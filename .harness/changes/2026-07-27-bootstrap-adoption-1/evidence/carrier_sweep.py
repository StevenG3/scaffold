#!/usr/bin/env python3
"""Adversarial sweep over the gate-evidence carrier rule.

This script is EVIDENCE MATERIAL of the bootstrap Change Record, not a reusable
Harness component: it is deliberately not registered in manifest.json.

It contains a mechanical implementation of the carrier rule as written in
`.harness/rules/project.md` section 2, then attacks that implementation with:

  1. DIRECTED cases drawn verbatim from the project's declared adversarial
     input domain (`docs/process/invariant-closure-design.md` section 2.3),
     plus every family of the fixed unrenderable code-point set the rule
     enumerates, plus visible neighbours just outside that set. Each directed
     case carries an EXPECTED BRANCH and an EXPECTED CARRIER VALUE, and a case
     passes only if BOTH match byte-exactly. Branch-only checking would accept
     an implementation that classifies correctly and then records the wrong
     bytes -- an external review proved exactly that hole by stubbing the
     digest helper to a constant and still seeing zero failures.
  2. A COMPARATOR SELF-TEST that mutates known-good expectations (wrong SHA,
     wrong byte count, wrong verbatim line, wrong branch) and asserts the
     comparator rejects each one, plus a control that must still be accepted.
     Without this, a comparator that always passed would look identical to a
     correct one.
  3. An ARGV SELF-TEST asserting that unknown flags and mutually exclusive
     mode combinations are rejected rather than silently reinterpreted.
  4. RANDOM fuzzing over the full byte domain. Fuzzing can only show that no
     input escapes the partition; it cannot show that the partition places
     inputs in the RIGHT branch, still less that it records the right bytes.
     That is why the directed cases and the self-tests exist.

Expected carriers are constructed INDEPENDENTLY of the code under test:
verbatim expectations are literal strings written out by hand, and hash
expectations pair a literal byte count with a direct hashlib.sha256() call.
Neither `_digest()` nor `carrier()` is ever used to build an expectation.

Deterministic: standard library only, fixed seed, no clock or environment
input. Re-running on any Python 3.9+ reproduces the same result digest.

Usage:  python3 carrier_sweep.py [--baseline | --emit-markdown]

The two flags are mutually exclusive; passing both is rejected.

Exit codes are per mode:
  default          0 if every directed case matches its expected branch AND
                   carrier, both self-tests pass, and no input escapes the
                   partition; 1 otherwise. This is the only mode whose exit
                   code is a verdict.
  --baseline       always 0 unless the run itself errors. It is a reporting
                   mode and is EXPECTED to show failures.
  --emit-markdown  always 0 unless the run itself errors. Reporting mode.
  bad arguments    2, with a message and usage on stderr. This covers unknown
                   flags and mutually exclusive combinations alike.

Note on source encoding: this file is pure ASCII. Every non-ASCII code point
appears as an escape sequence (for example "\\u0085"), never as a literal
character, so the script stays reviewable in a plain text diff.
"""

import hashlib
import os
import random
import sys
import tempfile

# Fixed seed. Changing this invalidates the recorded result digest.
SEED = 20260727
ITERATIONS = 200000
MAX_LEN = 6

# The rule's fixed unrenderable code-point set, spelled out exactly as the rule
# enumerates it. Membership is tested by code point, never by Unicode category,
# so the outcome does not move with a Unicode version upgrade.
UNRENDERABLE_SET = frozenset(
    list(range(0x00, 0x20))          # C0 controls
    + [0x7F]                         # DEL
    + list(range(0x80, 0xA0))        # C1 controls, includes NEL U+0085
    + [0xAD]                         # SOFT HYPHEN
    + [0x61C]                        # ARABIC LETTER MARK
    + list(range(0x200B, 0x200E))    # ZWSP ZWNJ ZWJ
    + [0x200E, 0x200F]               # LRM / RLM
    + [0x2028, 0x2029]               # line / paragraph separators
    + list(range(0x202A, 0x202F))    # LRE RLE PDF LRO RLO
    + list(range(0x2060, 0x2065))    # word joiner, invisible operators
    + list(range(0x2066, 0x2070))    # bidi isolates + deprecated format chars
    + list(range(0xFFF9, 0xFFFC))    # interlinear annotation marks
    + list(range(0xFE00, 0xFE10))    # variation selectors, basic block
    + [0xFEFF]                       # BOM / ZWNBSP
    + list(range(0xE0000, 0xE0080))  # tag characters
)

BRANCH_EMPTY = "(a) empty"
BRANCH_LINE = "(b) last-non-empty-line verbatim"
BRANCH_NO_LINE = "(b) no non-empty line -> bytes+sha256"
BRANCH_UNRENDERABLE = "(b) unrenderable code point -> bytes+sha256"
BRANCH_UNDECODABLE = "(c) not UTF-8 decodable -> bytes+sha256"
BRANCHES = (
    BRANCH_EMPTY,
    BRANCH_LINE,
    BRANCH_NO_LINE,
    BRANCH_UNRENDERABLE,
    BRANCH_UNDECODABLE,
)

CARRIER_EMPTY = "<empty>"


# ---------------------------------------------------------------------------
# Code under test.
# ---------------------------------------------------------------------------

def _digest(raw):
    return "bytes=%d sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest())


def carrier(raw):
    """Mechanical implementation of the carrier rule. Total over all bytes."""
    if len(raw) == 0:
        return BRANCH_EMPTY, CARRIER_EMPTY

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return BRANCH_UNDECODABLE, _digest(raw)

    # Lines: split on 0x0A only; strip at most one trailing 0x0D.
    lines = raw.split(b"\x0a")
    stripped = [ln[:-1] if ln.endswith(b"\x0d") else ln for ln in lines]
    non_empty = [ln for ln in stripped if len(ln) >= 1]
    if not non_empty:
        return BRANCH_NO_LINE, _digest(raw)

    last = non_empty[-1].decode("utf-8")
    if any(ord(ch) in UNRENDERABLE_SET for ch in last):
        return BRANCH_UNRENDERABLE, _digest(raw)
    return BRANCH_LINE, last


BASELINE_UNRENDERABLE_BYTES = frozenset(list(range(0x00, 0x20)) + [0x7F])


def carrier_baseline(raw):
    """The PRE-FIX predicate, kept so the fix can be shown to go red on it.

    This is the rule as it stood before the unrenderable code-point set was
    introduced: the unrenderable test looked at raw BYTES for C0/DEL only, so
    every strictly-decodable invisible character (NEL, U+2028, bidi controls,
    zero-width characters, ...) was classified as renderable verbatim.
    """
    if len(raw) == 0:
        return BRANCH_EMPTY, CARRIER_EMPTY
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return BRANCH_UNDECODABLE, _digest(raw)
    lines = raw.split(b"\x0a")
    stripped = [ln[:-1] if ln.endswith(b"\x0d") else ln for ln in lines]
    non_empty = [ln for ln in stripped if len(ln) >= 1]
    if not non_empty:
        return BRANCH_NO_LINE, _digest(raw)
    last = non_empty[-1]
    if any(byte in BASELINE_UNRENDERABLE_BYTES for byte in last):
        return BRANCH_UNRENDERABLE, _digest(raw)
    return BRANCH_LINE, last.decode("utf-8")


# ---------------------------------------------------------------------------
# Independent expectation construction.
#
# expect_hash() takes the LITERAL expected byte count from the case table and
# asserts it against the input, so a wrong literal fails loudly at import
# rather than silently agreeing with whatever the implementation produced. The
# SHA comes straight from hashlib, which is not the thing under test.
# ---------------------------------------------------------------------------

def expect_hash(raw, expected_len):
    if len(raw) != expected_len:
        raise AssertionError(
            "case table declares %d bytes but the input is %d bytes: %r"
            % (expected_len, len(raw), raw))
    return "bytes=%d sha256=%s" % (expected_len, hashlib.sha256(raw).hexdigest())


def resolve_expectation(raw, spec):
    """Carrier specs: ("empty",), ("verbatim", literal), ("hash", literal_len)."""
    kind = spec[0]
    if kind == "empty":
        return CARRIER_EMPTY
    if kind == "verbatim":
        return spec[1]
    if kind == "hash":
        return expect_hash(raw, spec[1])
    raise AssertionError("unknown carrier spec: %r" % (spec,))


# ---------------------------------------------------------------------------
# Directed cases: (name, input bytes, expected branch, expected carrier spec).
#
# Group A mirrors the declared adversarial byte domain (process section 2.3).
# Group B covers every family of the unrenderable set, plus visible neighbours.
# Group C attacks the byte-level definition of "line".
# Group D attacks UTF-8 decodability boundaries.
# Group E replays the real gate outputs recorded by this Change Record.
# ---------------------------------------------------------------------------
DIRECTED_SPECS = [
    # -- Group A: declared adversarial byte domain (section 2.3) --
    ("A CRLF line ending", b"OK\r\n", BRANCH_LINE, ("verbatim", "OK")),
    ("A CRLF only", b"\r\n", BRANCH_NO_LINE, ("hash", 2)),
    ("A no trailing newline", b"OK", BRANCH_LINE, ("verbatim", "OK")),
    ("A empty stream", b"", BRANCH_EMPTY, ("empty",)),
    ("A non-ASCII CJK", "\u5951\u7ea6\u6709\u6548\u3002\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "\u5951\u7ea6\u6709\u6548\u3002")),
    ("A non-ASCII emoji", "done \U0001f600\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "done \U0001f600")),
    ("A C0 control NUL", b"\x00\n", BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A C0 control BEL", b"\x07\n", BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A DEL U+007F", b"\x7f\n", BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A NEL U+0085", "A\u0085B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 5)),
    ("A U+2028 line sep", "A\u2028B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("A U+2029 para sep", "A\u2029B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("A surrogate bytes D800", b"\xed\xa0\x80", BRANCH_UNDECODABLE, ("hash", 3)),
    ("A surrogate bytes DFFF", b"\xed\xbf\xbf", BRANCH_UNDECODABLE, ("hash", 3)),
    ("A literal escape vs real char", b"line\\nnot-a-newline\n",
     BRANCH_LINE, ("verbatim", "line\\nnot-a-newline")),
    ("A literal <empty> collision", b"<empty>\n", BRANCH_LINE, ("verbatim", "<empty>")),
    # -- Group B: the rule's unrenderable code-point set --
    ("B C1 control U+0080", "A\u0080B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B C1 control U+009F", "A\u009fB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B SOFT HYPHEN U+00AD", "A\u00adB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B ARABIC LETTER MARK U+061C", "A\u061cB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B ZWSP U+200B", "A\u200bB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ZWNJ U+200C", "A\u200cB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ZWJ U+200D", "A\u200dB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRM U+200E", "A\u200eB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B RLM U+200F", "A\u200fB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRE U+202A", "A\u202aB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B RLO U+202E", "A\u202eB\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B WORD JOINER U+2060", "A\u2060B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INVISIBLE TIMES U+2062", "A\u2062B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INVISIBLE PLUS U+2064", "A\u2064B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRI U+2066", "A\u2066B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B FSI U+2068", "A\u2068B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B PDI U+2069", "A\u2069B\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INHIBIT SYMMETRIC SWAP U+206A", "A\u206aB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B NOMINAL DIGIT SHAPES U+206F", "A\u206fB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B VARIATION SELECTOR-1 U+FE00", "A\ufe00B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B VARIATION SELECTOR-16 U+FE0F", "A\ufe0fB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ANNOTATION ANCHOR U+FFF9", "A\ufff9B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ANNOTATION TERMINATOR U+FFFB", "A\ufffbB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B BOM U+FEFF", "\ufeffOK\n".encode("utf-8"), BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LANGUAGE TAG U+E0001", "A\U000e0001B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 7)),
    ("B TAG LATIN SMALL A U+E0061", "A\U000e0061B\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 7)),
    ("B CANCEL TAG U+E007F", "A\U000e007fB\n".encode("utf-8"),
     BRANCH_UNRENDERABLE, ("hash", 7)),
    # Visible neighbours just outside the set. These MUST stay verbatim.
    # Every one is an assigned, visible (or visibly spacing) character; the set
    # makes no claim about unassigned code points, so none are used here.
    ("B neighbour U+00A0 NBSP visible-spacing", "A\u00a0B\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "A\u00a0B")),
    ("B neighbour U+2010 HYPHEN visible", "A\u2010B\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "A\u2010B")),
    ("B neighbour U+2027 HYPHENATION POINT visible", "A\u2027B\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "A\u2027B")),
    ("B neighbour U+202F NNBSP visible-spacing", "A\u202fB\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "A\u202fB")),
    ("B neighbour U+3000 IDEOGRAPHIC SPACE visible-spacing", "A\u3000B\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "A\u3000B")),
    # -- Group C: byte-level definition of "line" --
    ("C lone LF", b"\n", BRANCH_NO_LINE, ("hash", 1)),
    ("C lone CR", b"\r", BRANCH_NO_LINE, ("hash", 1)),
    ("C several blank lines", b"\n\n\n", BRANCH_NO_LINE, ("hash", 3)),
    ("C several CRLF blanks", b"\r\n\r\n", BRANCH_NO_LINE, ("hash", 4)),
    ("C single space line", b" \n", BRANCH_LINE, ("verbatim", " ")),
    ("C spaces no newline", b"   ", BRANCH_LINE, ("verbatim", "   ")),
    ("C trailing blanks after text", b"OK\n\n\n", BRANCH_LINE, ("verbatim", "OK")),
    ("C trailing CRLF blanks after text", b"OK\r\n\r\n", BRANCH_LINE, ("verbatim", "OK")),
    ("C CR inside line not trailing", b"A\rB\n", BRANCH_UNRENDERABLE, ("hash", 4)),
    ("C only one trailing CR stripped", b"OK\r\r\n", BRANCH_UNRENDERABLE, ("hash", 5)),
    ("C lone CR line", b"\r\r\n", BRANCH_UNRENDERABLE, ("hash", 3)),
    # -- Group D: UTF-8 decodability boundaries --
    ("D undecodable tail byte", b"OK\n\xff", BRANCH_UNDECODABLE, ("hash", 4)),
    ("D undecodable no non-empty line", b"\n\xff", BRANCH_UNDECODABLE, ("hash", 2)),
    ("D truncated multi-byte seq", "\u5951".encode("utf-8")[:2],
     BRANCH_UNDECODABLE, ("hash", 2)),
    ("D overlong encoding of slash", b"\xc0\xaf", BRANCH_UNDECODABLE, ("hash", 2)),
    ("D two-byte boundary U+07FF", "\u07ff\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "\u07ff")),
    ("D four-byte astral plane", "\U0001f600\n".encode("utf-8"),
     BRANCH_LINE, ("verbatim", "\U0001f600")),
    # -- Group E: real gate outputs recorded by this Change Record --
    ("E gate 1/2/6 stdout", b"Harness contract is valid.\n",
     BRANCH_LINE, ("verbatim", "Harness contract is valid.")),
    ("E gate 3 stdout two lines",
     b"[ADAPT_SKIPPED_TEMPLATE] .: origin is null\nadapt: ok\n",
     BRANCH_LINE, ("verbatim", "adapt: ok")),
    ("E gate 4 stderr tail",
     b"Ran 175 tests in 12.316s\n\nOK (skipped=2)\n",
     BRANCH_LINE, ("verbatim", "OK (skipped=2)")),
    ("E gate 5 both streams", b"", BRANCH_EMPTY, ("empty",)),
]

# Resolved at import: (name, raw, expected_branch, expected_carrier).
DIRECTED = [(name, raw, branch, resolve_expectation(raw, spec))
            for name, raw, branch, spec in DIRECTED_SPECS]


# ---------------------------------------------------------------------------
# Independent value oracle for the fuzz domain.
#
# This is a SECOND, deliberately different transcription of the same rule. It
# never calls carrier() or _digest(): it walks bytes by hand instead of using
# split(), and rebuilds the hash string from a direct hashlib call. Two
# independent transcriptions that disagree on ANY fuzz input turn the run red,
# so the fuzz domain now checks recorded VALUES, not just branch labels --
# without it, an implementation that recorded garbage for inputs outside the
# 69 directed cases reproduced the recorded digest exactly and stayed green.
# ---------------------------------------------------------------------------

def oracle_carrier(raw):
    """Independent transcription of the carrier rule. Never calls carrier()."""
    if not raw:
        return BRANCH_EMPTY, CARRIER_EMPTY

    hashed = "bytes=%d sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest())

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return BRANCH_UNDECODABLE, hashed

    # Split on 0x0A by hand rather than with bytes.split(), so a defect in one
    # transcription's use of the library shows up as a disagreement.
    segments = []
    current = bytearray()
    for byte in raw:
        if byte == 0x0A:
            segments.append(bytes(current))
            current = bytearray()
        else:
            current.append(byte)
    segments.append(bytes(current))

    last_non_empty = None
    for segment in segments:
        trimmed = segment[:-1] if (segment and segment[-1] == 0x0D) else segment
        if len(trimmed) > 0:
            last_non_empty = trimmed
    if last_non_empty is None:
        return BRANCH_NO_LINE, hashed

    decoded = last_non_empty.decode("utf-8")
    for code_point in map(ord, decoded):
        if code_point in UNRENDERABLE_SET:
            return BRANCH_UNRENDERABLE, hashed
    return BRANCH_LINE, decoded


# ---------------------------------------------------------------------------
# Comparator.
# ---------------------------------------------------------------------------

def compare(expected_branch, expected_carrier, actual_branch, actual_carrier):
    """A case passes only if BOTH the branch and the carrier match exactly."""
    return (expected_branch == actual_branch
            and expected_carrier == actual_carrier)


def run_directed(predicate=carrier):
    rows = []
    failures = 0
    for name, raw, expected_branch, expected_carrier in DIRECTED:
        actual_branch, actual_carrier = predicate(raw)
        ok = compare(expected_branch, expected_carrier,
                     actual_branch, actual_carrier)
        if not ok:
            failures += 1
        rows.append((name, raw, expected_branch, expected_carrier,
                     actual_branch, actual_carrier, ok))
    return rows, failures


def run_fuzz():
    """Fuzz the full byte domain, checking BRANCH and CARRIER VALUE.

    Every input is scored against oracle_carrier(), an independent
    transcription. Returns (counts, undefined, mismatches) where mismatches
    counts inputs on which the implementation and the oracle disagree about
    the branch or about the recorded value.
    """
    rng = random.Random(SEED)
    counts = {branch: 0 for branch in BRANCHES}
    undefined = 0
    mismatches = 0
    for _ in range(ITERATIONS):
        raw = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, MAX_LEN)))
        try:
            branch, recorded = carrier(raw)
        except Exception:  # noqa: BLE001 - any escape at all is a rule defect
            undefined += 1
            continue
        if branch not in counts or not recorded:
            undefined += 1
            continue
        counts[branch] += 1
        expected_branch, expected_carrier = oracle_carrier(raw)
        if branch != expected_branch or recorded != expected_carrier:
            mismatches += 1
    return counts, undefined, mismatches


# ---------------------------------------------------------------------------
# Self-tests. A comparator that always returned True would make every directed
# case pass and look exactly like a correct one, so the comparator itself must
# be shown to discriminate -- in both directions.
# ---------------------------------------------------------------------------

def selftest_comparator():
    """Mutate known-good expectations and assert the comparator rejects them."""
    results = []

    hash_case = next(c for c in DIRECTED if c[0] == "A NEL U+0085")
    line_case = next(c for c in DIRECTED if c[0] == "E gate 1/2/6 stdout")

    _, hash_raw, hash_branch, hash_carrier = hash_case
    _, line_raw, line_branch, line_carrier = line_case
    actual_hash_branch, actual_hash_carrier = carrier(hash_raw)
    actual_line_branch, actual_line_carrier = carrier(line_raw)

    # Mutation 1: wrong SHA (flip one hex digit of the expected digest).
    head, sha = hash_carrier.split("sha256=")
    flipped = ("1" if sha[0] != "1" else "2") + sha[1:]
    results.append((
        "wrong sha256 rejected",
        not compare(hash_branch, head + "sha256=" + flipped,
                    actual_hash_branch, actual_hash_carrier)))

    # Mutation 2: wrong byte count (same SHA, count off by one).
    wrong_count = hash_carrier.replace("bytes=%d " % len(hash_raw),
                                       "bytes=%d " % (len(hash_raw) + 1), 1)
    results.append((
        "wrong byte count rejected",
        wrong_count != hash_carrier
        and not compare(hash_branch, wrong_count,
                        actual_hash_branch, actual_hash_carrier)))

    # Mutation 3: wrong verbatim line (trailing period dropped).
    results.append((
        "wrong verbatim line rejected",
        not compare(line_branch, line_carrier.rstrip("."),
                    actual_line_branch, actual_line_carrier)))

    # Mutation 4: right carrier, wrong branch -- the branch half must still bite.
    results.append((
        "wrong branch rejected",
        not compare(BRANCH_LINE, hash_carrier,
                    actual_hash_branch, actual_hash_carrier)))

    # Control: unmutated expectations must still be ACCEPTED. Without this, a
    # comparator hardwired to False would pass every mutation check above.
    results.append((
        "control: unmutated expectation accepted",
        compare(hash_branch, hash_carrier,
                actual_hash_branch, actual_hash_carrier)
        and compare(line_branch, line_carrier,
                    actual_line_branch, actual_line_carrier)))

    return results


def selftest_argv():
    """Assert bad argv is rejected rather than silently reinterpreted."""
    return [
        ("unknown flag rejected", parse_args(["--bogus"])[1] is not None),
        ("unknown flag exits 2", parse_args(["--bogus"])[0] == 2),
        ("mutually exclusive combination rejected",
         parse_args(["--baseline", "--emit-markdown"])[1] is not None),
        ("mutually exclusive combination exits 2",
         parse_args(["--baseline", "--emit-markdown"])[0] == 2),
        ("reversed order also rejected",
         parse_args(["--emit-markdown", "--baseline"])[1] is not None),
        ("repeated flag is still one mode",
         parse_args(["--baseline", "--baseline"])[2] == "baseline"),
        ("default mode accepted", parse_args([])[2] == "default"),
        ("baseline mode accepted", parse_args(["--baseline"])[2] == "baseline"),
        ("emit mode accepted", parse_args(["--emit-markdown"])[2] == "emit"),
        ("emit with path accepted",
         parse_args(["--emit-markdown", "out.md"])[2:] == ("emit", "out.md")),
        ("path without emit rejected",
         parse_args(["out.md"])[0] == 2),
        ("two paths rejected",
         parse_args(["--emit-markdown", "a.md", "b.md"])[0] == 2),
        ("baseline with path rejected",
         parse_args(["--baseline", "out.md"])[0] == 2),
        ("help accepted and exits 0",
         parse_args(["--help"])[2] == "help" and parse_args(["--help"])[0] == 0),
        ("short help accepted", parse_args(["-h"])[2] == "help"),
    ]


# ---------------------------------------------------------------------------
# Argument parsing, reporting, digest.
# ---------------------------------------------------------------------------

USAGE = (
    "usage: carrier_sweep.py [--baseline | --emit-markdown]\n"
    "  (no flag)        run directed + self-tests + fuzz; exit 1 on any failure\n"
    "  --baseline       report the pre-fix predicate's results (reporting mode)\n"
    "  --emit-markdown [PATH]\n"
    "                   emit the boundary-case table (reporting mode). With no\n"
    "                   PATH it streams to stdout; with PATH it is written\n"
    "                   atomically, so a failed run cannot truncate the table.\n"
    "  -h, --help       print this usage on stdout and exit 0\n"
    "The two mode flags are mutually exclusive.\n"
)
KNOWN_FLAGS = ("--baseline", "--emit-markdown")


def parse_args(argv):
    """Return (exit_code, error_message, mode, path). exit_code 0 when accepted.

    Modes: "default", "baseline", "emit", "help". `path` is set only for emit
    mode with an explicit destination, in which case the table is written
    atomically instead of streamed to stdout.
    """
    if "-h" in argv or "--help" in argv:
        return 0, None, "help", None

    flags = [arg for arg in argv if arg.startswith("-")]
    positionals = [arg for arg in argv if not arg.startswith("-")]

    unknown = [arg for arg in flags if arg not in KNOWN_FLAGS]
    if unknown:
        return 2, "unknown argument(s): %s" % " ".join(unknown), None, None

    baseline = "--baseline" in flags
    emit = "--emit-markdown" in flags
    if baseline and emit:
        return (2,
                "--baseline and --emit-markdown are mutually exclusive; "
                "combining them would mix baseline failures into the generated "
                "table and its digest",
                None, None)
    if positionals and not emit:
        return (2,
                "a path argument is only valid with --emit-markdown: %s"
                % " ".join(positionals),
                None, None)
    if len(positionals) > 1:
        return (2,
                "--emit-markdown takes at most one path: %s"
                % " ".join(positionals),
                None, None)

    if baseline:
        return 0, None, "baseline", None
    if emit:
        return 0, None, "emit", positionals[0] if positionals else None
    return 0, None, "default", None


def write_atomically(path, text):
    """Write text to path atomically: temp file in the same dir, then replace.

    The documented regeneration command used to be a shell redirect, which
    truncates the official table the instant the shell opens it -- so a crash
    or a rejected argv left a zero-length or half-written artifact in the
    Change Record. os.replace() is atomic on POSIX and Windows alike, so the
    old table survives untouched unless a complete new one is ready.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    handle, temp_path = tempfile.mkstemp(dir=directory, prefix=".carrier_sweep-",
                                         suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp_path, path)
    except BaseException:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def result_digest(rows, counts, undefined, mismatches, failures):
    """SHA-256 over sorted result lines.

    The payload binds the input bytes AND the actual recorded carrier, so a
    wrong carrier value moves the digest. Binding only branch labels would let
    an implementation that records garbage reproduce the recorded digest
    exactly -- which is precisely the hole an external review demonstrated.
    """
    lines = ["directed\t%s\t%s\t%s\t%s\t%s\t%s"
             % (name, repr(raw), expected_branch, repr(expected_carrier),
                actual_branch, repr(actual_carrier))
             for (name, raw, expected_branch, expected_carrier,
                  actual_branch, actual_carrier, ok) in rows]
    lines += ["fuzz\t%s\t%d" % (branch, counts[branch]) for branch in BRANCHES]
    lines += ["fuzz\tundefined\t%d" % undefined,
              "fuzz\tvalue_mismatches\t%d" % mismatches,
              "directed\tfailures\t%d" % failures]
    payload = "\n".join(sorted(lines)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


GROUP_TITLES = {
    "A": "A group -- declared adversarial byte domain (process section 2.3)",
    "B": "B group -- the rule's unrenderable code-point set, plus visible neighbours",
    "C": 'C group -- the byte-level definition of "line"',
    "D": "D group -- UTF-8 decodability boundaries",
    "E": "E group -- replay of the gate outputs this Change Record records",
}


def emit_markdown(rows, failures, digest, selftest_summary, mismatches):
    """Emit boundary-cases.md on stdout. Values are shown in full, untruncated."""
    out = []
    out.append("# Boundary case table -- gate evidence carrier rule")
    out.append("")
    out.append("DO NOT EDIT BY HAND. Generated by `carrier_sweep.py --emit-markdown`;")
    out.append("regenerate rather than editing, or the result digest stops matching.")
    out.append("")
    out.append("Directed cases: **%d**, failures: **%d**." % (len(rows), failures))
    out.append("A case passes only if BOTH its branch and its carrier value match the")
    out.append("independently constructed expectation, byte for byte. Inputs and")
    out.append("carriers are shown in full and are never truncated.")
    out.append("")
    out.append("Self-test attestation for the run that produced this table:")
    out.append("comparator self-test %d/%d passed, argv self-test %d/%d passed,"
               % selftest_summary)
    out.append("fuzz value mismatches: %d." % mismatches)
    out.append("A corrupted comparator changes these counts, so this artifact")
    out.append("carries the evidence of its own validity rather than asserting it.")
    out.append("")
    out.append("Result digest: `%s`" % digest)
    for key in "ABCDE":
        subset = [r for r in rows if r[0].startswith(key + " ")]
        if not subset:
            continue
        out.append("")
        out.append("## " + GROUP_TITLES[key])
        out.append("")
        out.append("| case | input bytes | expected branch | expected carrier "
                   "| actual branch | actual carrier | status |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for (name, raw, expected_branch, expected_carrier,
             actual_branch, actual_carrier, ok) in subset:
            out.append("| %s | `%s` | `%s` | `%s` | `%s` | `%s` | %s |"
                       % (name[2:],
                          repr(raw).replace("|", "\\|"),
                          expected_branch,
                          repr(expected_carrier).replace("|", "\\|"),
                          actual_branch,
                          repr(actual_carrier).replace("|", "\\|"),
                          "PASS" if ok else "**FAIL**"))
    out.append("")
    out.append("## Conclusion")
    out.append("")
    if failures == 0:
        out.append("All %d directed cases match BOTH their expected branch and their"
                   % len(rows))
        out.append("expected carrier value. Failures: 0.")
    else:
        out.append("**%d of %d directed cases FAILED.** Their branch or their carrier"
                   % (failures, len(rows)))
        out.append("value differs from the independently constructed expectation, so")
        out.append("this table does NOT certify the rule. Failing cases:")
        out.append("")
        for (name, raw, expected_branch, expected_carrier,
             actual_branch, actual_carrier, ok) in rows:
            if not ok:
                out.append("- `%s`: expected `%s` / `%s`, got `%s` / `%s`"
                           % (name, expected_branch, repr(expected_carrier),
                              actual_branch, repr(actual_carrier)))
    out.append("")
    out.append("Directed cases validate the PREDICATE: is each input placed in the right")
    out.append("branch, and is the right value recorded. Random fuzzing can only show")
    out.append("that no input escapes the partition. Neither substitutes for the other")
    out.append("-- see `run-manifest.md`.")
    return "\n".join(out) + "\n"


def _print_directed(rows, label):
    failures = sum(1 for row in rows if not row[6])
    print("== DIRECTED CASES -- %s ==" % label)
    print("%-52s %-44s %s" % ("case", "expected branch", "status"))
    for (name, raw, expected_branch, expected_carrier,
         actual_branch, actual_carrier, ok) in rows:
        print("%-52s %-44s %s"
              % (name, expected_branch, "PASS" if ok else "FAIL"))
    print("")
    print("directed cases: %d, failures: %d" % (len(rows), failures))
    print("(a case passes only if BOTH branch and carrier value match)")


def selftest_summary():
    comparator_checks = selftest_comparator()
    argv_checks = selftest_argv()
    failures = ([name for name, ok in comparator_checks if not ok]
                + [name for name, ok in argv_checks if not ok])
    summary = (sum(1 for _, ok in comparator_checks if ok), len(comparator_checks),
               sum(1 for _, ok in argv_checks if ok), len(argv_checks))
    return comparator_checks, argv_checks, summary, failures


def main(argv):
    code, error, mode, path = parse_args(argv)
    if error is not None:
        sys.stderr.write("carrier_sweep.py: %s\n" % error)
        sys.stderr.write(USAGE)
        return code

    if mode == "help":
        sys.stdout.write(USAGE)
        return 0

    predicate = carrier_baseline if mode == "baseline" else carrier
    rows, failures = run_directed(predicate)

    # Reporting modes. Their exit code carries no verdict: it reports only that
    # the run itself completed. --baseline is EXPECTED to show failures, so a
    # non-zero exit there would mean the opposite of what a reader assumes.
    if mode == "emit":
        counts, undefined, mismatches = run_fuzz()
        _, _, summary, _ = selftest_summary()
        digest = result_digest(rows, counts, undefined, mismatches, failures)
        text = emit_markdown(rows, failures, digest, summary, mismatches)
        if path is None:
            sys.stdout.write(text)
        else:
            write_atomically(path, text)
            sys.stderr.write("wrote %s\n" % path)
        return 0

    if mode == "baseline":
        _print_directed(rows, "BASELINE (pre-fix predicate)")
        print("")
        print("Reporting mode: this exit code carries no verdict. The baseline is")
        print("EXPECTED to be red. Cases the pre-fix predicate got wrong:")
        for (name, raw, expected_branch, expected_carrier,
             actual_branch, actual_carrier, ok) in rows:
            if not ok:
                print("  %-52s expected %-44s got %s"
                      % (name, expected_branch, actual_branch))
        return 0

    # Default mode. This is the only mode whose exit code is a verdict.
    _print_directed(rows, "CURRENT RULE")

    comparator_checks, argv_checks, summary, selftest_failures = selftest_summary()

    print("")
    print("== COMPARATOR SELF-TEST ==")
    print("mutated expectations must be REJECTED; the control must be ACCEPTED")
    for name, ok in comparator_checks:
        print("  %-44s %s" % (name, "PASS" if ok else "FAIL"))

    print("")
    print("== ARGV SELF-TEST ==")
    for name, ok in argv_checks:
        print("  %-44s %s" % (name, "PASS" if ok else "FAIL"))

    counts, undefined, mismatches = run_fuzz()
    print("")
    print("== RANDOM FUZZ ==")
    print("seed=%d iterations=%d max_len=%d domain=all 256 byte values"
          % (SEED, ITERATIONS, MAX_LEN))
    for branch in BRANCHES:
        print("  %-44s %d" % (branch, counts[branch]))
    print("undefined/exception cases: %d" % undefined)
    print("value mismatches vs independent oracle: %d" % mismatches)
    print("note: every fuzz input is scored against an independent transcription")
    print("      of the rule, so the fuzz domain checks recorded VALUES too, not")
    print("      only branch labels. Directed cases add byte-exact expectations.")

    print("")
    print("self-test failures: %d" % len(selftest_failures))
    print("result digest (sha256 of sorted result lines, inputs and actual "
          "carriers bound in): %s"
          % result_digest(rows, counts, undefined, mismatches, failures))
    if selftest_failures:
        return 1
    return 0 if failures == 0 and undefined == 0 and mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
