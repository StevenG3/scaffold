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
  4. An EXHAUSTIVE sweep of every input of length 0-2 (65793 inputs) against
     the oracle. This is the one place a universal claim is affordable, and it
     is claimed only over that subdomain.
  5. A SAMPLED sweep over lengths 0-6. Each DRAWN input gets an independent
     oracle check of BOTH branch and carrier value; what sampling cannot
     establish is anything about inputs never drawn. The full 0-6 domain is
     2.8e14 inputs.

Expected carriers are constructed INDEPENDENTLY of the code under test:
verbatim expectations are literal strings written out by hand, and hash
expectations pair a literal byte count with a direct hashlib.sha256() call.
Neither `_digest()` nor `carrier()` is ever used to build an expectation.

Deterministic, with a stated scope: standard library only, fixed seed, no
clock or environment input. Re-running under the SAME interpreter version
reproduces the same sample set and the same result digest bit for bit. NO
cross-version promise is made: the sample is drawn with random.randint() and
getrandbits(), and CPython documents that most random-module algorithms may
change between releases -- the cross-version guarantee covers random() under a
compatible seeder, not this combination of calls.
See https://docs.python.org/3/library/random.html#notes-on-reproducibility
The measured interpreter version is recorded in run-manifest.md.

Usage:  python3 carrier_sweep.py [--baseline | --emit-markdown]

The two flags are mutually exclusive; passing both is rejected.

Exit codes are per mode:
  default          0 only if the single certification state holds: directed
                   cases pass on branch AND carrier, all four self-test classes
                   pass (comparator, common-cause, argv, certification), the
                   exhaustive length 0-2 sweep has no mismatch, and the sampled
                   sweep has no mismatch and no undefined input. 1 otherwise.
                   This is the only mode whose exit code is a verdict.
  --baseline       always 0 unless the run itself errors. It is a reporting
                   mode, is EXPECTED to show failures, and never writes a file.
  --emit-markdown  0 only when certification holds. On failure it refuses to
                   write PATH and exits 1; without PATH it prints the
                   uncertified table on stdout, with a banner, and exits 1.
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

# ---------------------------------------------------------------------------
# VERIFICATION-SIDE CONSTANTS.
#
# These belong to the checking side and must never be read from the code under
# test. An external review showed why: when the directed expectation and the
# oracle both read the SUT's CARRIER_EMPTY, editing that one constant to
# "<wrong>" left every check green. A literal written out separately here fails
# that mutation immediately.
# ---------------------------------------------------------------------------

EXPECTED_EMPTY_LITERAL = "<empty>"   # independent copy; do NOT use CARRIER_EMPTY

# The oracle's OWN transcription of the unrenderable code-point set. This is a
# second literal list, not an alias: sharing one set made SUT and oracle fail
# in the same direction, so deleting a member that no directed case covered
# left both agreeing and the run green. assert_set_agreement() cross-checks the
# two transcriptions at import, so deleting from either one fires immediately.
# A deletion applied to BOTH lists is still a genuine common cause -- see the
# trusted-computing-base disclosure in run-manifest.md.
ORACLE_UNRENDERABLE_SET = frozenset(
    list(range(0x0000, 0x0020))
    + [0x007F]
    + list(range(0x0080, 0x00A0))
    + [0x00AD]
    + [0x061C]
    + [0x200B, 0x200C, 0x200D]
    + [0x200E, 0x200F]
    + [0x2028, 0x2029]
    + [0x202A, 0x202B, 0x202C, 0x202D, 0x202E]
    + [0x2060, 0x2061, 0x2062, 0x2063, 0x2064]
    + [0x2066, 0x2067, 0x2068, 0x2069]
    + [0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F]
    + [0xFFF9, 0xFFFA, 0xFFFB]
    + list(range(0xFE00, 0xFE10))
    + [0xFEFF]
    + list(range(0xE0000, 0xE0080))
)


# The checking side's OWN branch labels. Same treatment as the empty carrier:
# an internal review showed that carrier(), oracle_carrier() and every directed
# expectation all read one set of BRANCH_* constants, so making two of them
# identical silently collapsed the five-way partition to four and every check
# stayed green. These literals are written out separately and cross-asserted
# against the SUT's at import.
ORACLE_BRANCH_EMPTY = "(a) empty"
ORACLE_BRANCH_LINE = "(b) last-non-empty-line verbatim"
ORACLE_BRANCH_NO_LINE = "(b) no non-empty line -> bytes+sha256"
ORACLE_BRANCH_UNRENDERABLE = "(b) unrenderable code point -> bytes+sha256"
ORACLE_BRANCH_UNDECODABLE = "(c) not UTF-8 decodable -> bytes+sha256"
ORACLE_BRANCHES = (
    ORACLE_BRANCH_EMPTY,
    ORACLE_BRANCH_LINE,
    ORACLE_BRANCH_NO_LINE,
    ORACLE_BRANCH_UNRENDERABLE,
    ORACLE_BRANCH_UNDECODABLE,
)


def branch_label_problems(sut_branches, oracle_branches):
    """Return a list of problems with the two branch-label transcriptions.

    Two distinct failures are checked, because they fail differently:
      - collision: two labels in one transcription are the same string, which
        collapses the partition without any pair disagreeing;
      - divergence: the transcriptions disagree pairwise.
    """
    problems = []
    if len(set(sut_branches)) != len(sut_branches):
        problems.append("SUT branch labels are not distinct: %r" % (sut_branches,))
    if len(set(oracle_branches)) != len(oracle_branches):
        problems.append("oracle branch labels are not distinct: %r" % (oracle_branches,))
    if len(sut_branches) != len(oracle_branches):
        problems.append("branch label count differs: %d vs %d"
                        % (len(sut_branches), len(oracle_branches)))
    else:
        for index, (left, right) in enumerate(zip(sut_branches, oracle_branches)):
            if left != right:
                problems.append("branch label %d differs: %r vs %r"
                                % (index, left, right))
    return problems


def assert_branch_labels():
    """Fail loudly at import on label collision or SUT/oracle divergence."""
    problems = branch_label_problems(BRANCHES, ORACLE_BRANCHES)
    if problems:
        raise AssertionError("; ".join(problems))


def set_divergence(set_a, set_b):
    """Return (only_in_a, only_in_b) as sorted lists. Empty pair means agreement."""
    return (sorted(set_a - set_b), sorted(set_b - set_a))


def assert_set_agreement():
    """Fail loudly at import if the two transcriptions disagree."""
    only_sut, only_oracle = set_divergence(UNRENDERABLE_SET, ORACLE_UNRENDERABLE_SET)
    if only_sut or only_oracle:
        raise AssertionError(
            "unrenderable set transcriptions disagree; only in SUT: %s; "
            "only in oracle: %s"
            % ([hex(cp) for cp in only_sut], [hex(cp) for cp in only_oracle]))


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

# Fire at import if a common-cause edit hits only one transcription, or if
# two branch labels collide (which would collapse the partition silently).
assert_set_agreement()
assert_branch_labels()


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
        return EXPECTED_EMPTY_LITERAL
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
    ("A CRLF line ending", b"OK\r\n", ORACLE_BRANCH_LINE, ("verbatim", "OK")),
    ("A CRLF only", b"\r\n", ORACLE_BRANCH_NO_LINE, ("hash", 2)),
    ("A no trailing newline", b"OK", ORACLE_BRANCH_LINE, ("verbatim", "OK")),
    ("A empty stream", b"", ORACLE_BRANCH_EMPTY, ("empty",)),
    ("A non-ASCII CJK", "\u5951\u7ea6\u6709\u6548\u3002\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "\u5951\u7ea6\u6709\u6548\u3002")),
    ("A non-ASCII emoji", "done \U0001f600\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "done \U0001f600")),
    ("A C0 control NUL", b"\x00\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A C0 control BEL", b"\x07\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A DEL U+007F", b"\x7f\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 2)),
    ("A NEL U+0085", "A\u0085B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("A U+2028 line sep", "A\u2028B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("A U+2029 para sep", "A\u2029B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("A surrogate bytes D800", b"\xed\xa0\x80", ORACLE_BRANCH_UNDECODABLE, ("hash", 3)),
    ("A surrogate bytes DFFF", b"\xed\xbf\xbf", ORACLE_BRANCH_UNDECODABLE, ("hash", 3)),
    ("A literal escape vs real char", b"line\\nnot-a-newline\n",
     ORACLE_BRANCH_LINE, ("verbatim", "line\\nnot-a-newline")),
    ("A literal <empty> collision", b"<empty>\n", ORACLE_BRANCH_LINE, ("verbatim", "<empty>")),
    # -- Group B: the rule's unrenderable code-point set --
    ("B C1 control U+0080", "A\u0080B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B C1 control U+009F", "A\u009fB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B SOFT HYPHEN U+00AD", "A\u00adB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B ARABIC LETTER MARK U+061C", "A\u061cB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("B ZWSP U+200B", "A\u200bB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ZWNJ U+200C", "A\u200cB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ZWJ U+200D", "A\u200dB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRM U+200E", "A\u200eB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B RLM U+200F", "A\u200fB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRE U+202A", "A\u202aB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B RLO U+202E", "A\u202eB\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B WORD JOINER U+2060", "A\u2060B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INVISIBLE TIMES U+2062", "A\u2062B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INVISIBLE PLUS U+2064", "A\u2064B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LRI U+2066", "A\u2066B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B FSI U+2068", "A\u2068B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B PDI U+2069", "A\u2069B\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B INHIBIT SYMMETRIC SWAP U+206A", "A\u206aB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B NOMINAL DIGIT SHAPES U+206F", "A\u206fB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B VARIATION SELECTOR-1 U+FE00", "A\ufe00B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B VARIATION SELECTOR-16 U+FE0F", "A\ufe0fB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ANNOTATION ANCHOR U+FFF9", "A\ufff9B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B ANNOTATION TERMINATOR U+FFFB", "A\ufffbB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B BOM U+FEFF", "\ufeffOK\n".encode("utf-8"), ORACLE_BRANCH_UNRENDERABLE, ("hash", 6)),
    ("B LANGUAGE TAG U+E0001", "A\U000e0001B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 7)),
    ("B TAG LATIN SMALL A U+E0061", "A\U000e0061B\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 7)),
    ("B CANCEL TAG U+E007F", "A\U000e007fB\n".encode("utf-8"),
     ORACLE_BRANCH_UNRENDERABLE, ("hash", 7)),
    # Visible neighbours just outside the set. These MUST stay verbatim.
    # Every one is an assigned, visible (or visibly spacing) character; the set
    # makes no claim about unassigned code points, so none are used here.
    ("B neighbour U+00A0 NBSP visible-spacing", "A\u00a0B\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "A\u00a0B")),
    ("B neighbour U+2010 HYPHEN visible", "A\u2010B\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "A\u2010B")),
    ("B neighbour U+2027 HYPHENATION POINT visible", "A\u2027B\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "A\u2027B")),
    ("B neighbour U+202F NNBSP visible-spacing", "A\u202fB\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "A\u202fB")),
    ("B neighbour U+3000 IDEOGRAPHIC SPACE visible-spacing", "A\u3000B\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "A\u3000B")),
    # -- Group C: byte-level definition of "line" --
    ("C lone LF", b"\n", ORACLE_BRANCH_NO_LINE, ("hash", 1)),
    ("C lone CR", b"\r", ORACLE_BRANCH_NO_LINE, ("hash", 1)),
    ("C several blank lines", b"\n\n\n", ORACLE_BRANCH_NO_LINE, ("hash", 3)),
    ("C several CRLF blanks", b"\r\n\r\n", ORACLE_BRANCH_NO_LINE, ("hash", 4)),
    ("C single space line", b" \n", ORACLE_BRANCH_LINE, ("verbatim", " ")),
    ("C spaces no newline", b"   ", ORACLE_BRANCH_LINE, ("verbatim", "   ")),
    ("C trailing blanks after text", b"OK\n\n\n", ORACLE_BRANCH_LINE, ("verbatim", "OK")),
    ("C trailing CRLF blanks after text", b"OK\r\n\r\n", ORACLE_BRANCH_LINE, ("verbatim", "OK")),
    ("C CR inside line not trailing", b"A\rB\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 4)),
    ("C only one trailing CR stripped", b"OK\r\r\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 5)),
    ("C lone CR line", b"\r\r\n", ORACLE_BRANCH_UNRENDERABLE, ("hash", 3)),
    # -- Group D: UTF-8 decodability boundaries --
    ("D undecodable tail byte", b"OK\n\xff", ORACLE_BRANCH_UNDECODABLE, ("hash", 4)),
    ("D undecodable no non-empty line", b"\n\xff", ORACLE_BRANCH_UNDECODABLE, ("hash", 2)),
    ("D truncated multi-byte seq", "\u5951".encode("utf-8")[:2],
     ORACLE_BRANCH_UNDECODABLE, ("hash", 2)),
    ("D overlong encoding of slash", b"\xc0\xaf", ORACLE_BRANCH_UNDECODABLE, ("hash", 2)),
    ("D two-byte boundary U+07FF", "\u07ff\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "\u07ff")),
    ("D four-byte astral plane", "\U0001f600\n".encode("utf-8"),
     ORACLE_BRANCH_LINE, ("verbatim", "\U0001f600")),
    # -- Group E: real gate outputs recorded by this Change Record --
    ("E gate 1/2/6 stdout", b"Harness contract is valid.\n",
     ORACLE_BRANCH_LINE, ("verbatim", "Harness contract is valid.")),
    ("E gate 3 stdout two lines",
     b"[ADAPT_SKIPPED_TEMPLATE] .: origin is null\nadapt: ok\n",
     ORACLE_BRANCH_LINE, ("verbatim", "adapt: ok")),
    ("E gate 4 stderr tail",
     b"Ran 175 tests in 12.316s\n\nOK (skipped=2)\n",
     ORACLE_BRANCH_LINE, ("verbatim", "OK (skipped=2)")),
    ("E gate 5 both streams", b"", ORACLE_BRANCH_EMPTY, ("empty",)),
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
        return ORACLE_BRANCH_EMPTY, EXPECTED_EMPTY_LITERAL

    hashed = "bytes=%d sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest())

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return ORACLE_BRANCH_UNDECODABLE, hashed

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
        return ORACLE_BRANCH_NO_LINE, hashed

    decoded = last_non_empty.decode("utf-8")
    for code_point in map(ord, decoded):
        if code_point in ORACLE_UNRENDERABLE_SET:
            return ORACLE_BRANCH_UNRENDERABLE, hashed
    return ORACLE_BRANCH_LINE, decoded


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


EXHAUSTIVE_MAX_LEN = 2


def run_exhaustive():
    """Compare SUT against the oracle on EVERY input of length 0..2.

    1 + 256 + 65536 = 65793 inputs. This is the only part of the byte domain
    where a universal claim is affordable, and it is made only here: lengths
    3..6 are sampled, never exhausted (the full 0..6 domain is 2.8e14 inputs).
    """
    total = 0
    mismatches = 0
    for length in range(EXHAUSTIVE_MAX_LEN + 1):
        for index in range(256 ** length):
            raw = index.to_bytes(length, "big") if length else b""
            total += 1
            try:
                branch, recorded = carrier(raw)
            except Exception:  # noqa: BLE001
                mismatches += 1
                continue
            expected_branch, expected_carrier = oracle_carrier(raw)
            if branch != expected_branch or recorded != expected_carrier:
                mismatches += 1
    return total, mismatches


def run_fuzz():
    """Fuzz the full byte domain, checking BRANCH and CARRIER VALUE.

    This is SAMPLING, not exhaustion: 200000 draws over lengths 0..6, whose
    full domain is 2.8e14 inputs. Every DRAWN input is scored against
    oracle_carrier(); inputs never drawn are not checked here and nothing about
    them is claimed. Returns (counts, undefined, mismatches, unique_inputs).
    """
    rng = random.Random(SEED)
    counts = {branch: 0 for branch in BRANCHES}
    undefined = 0
    mismatches = 0
    unique = set()
    for _ in range(ITERATIONS):
        raw = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, MAX_LEN)))
        unique.add(raw)
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
    return counts, undefined, mismatches, len(unique)


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


def selftest_common_cause():
    """Attack the shared trusted computing base itself.

    Two mutations that an external review showed were survivable when the
    checking side read the SUT's own constants: corrupting the empty-stream
    carrier, and deleting a set member no directed case covers.
    """
    results = []

    # Common cause 1: the SUT's empty carrier is wrong. The independent literal
    # must disagree with it. (Before the split, both sides read one constant.)
    sut_branch, sut_empty = carrier(b"")
    results.append((
        "empty carrier checked against independent literal",
        sut_empty == EXPECTED_EMPTY_LITERAL and sut_branch == BRANCH_EMPTY))
    results.append((
        "a wrong empty carrier would be rejected",
        not compare(BRANCH_EMPTY, EXPECTED_EMPTY_LITERAL, sut_branch, "<wrong>")))

    # Common cause 2: a set member deleted on one side only. The cross-check
    # must report the divergence. U+0001 is deliberately chosen: no directed
    # case covers it, which is exactly why the shared-set version stayed green.
    mutated = frozenset(ORACLE_UNRENDERABLE_SET - {0x0001})
    only_sut, only_oracle = set_divergence(UNRENDERABLE_SET, mutated)
    results.append((
        "one-sided set deletion is detected",
        only_sut == [0x0001] and not only_oracle))

    # Control: the real transcriptions must agree, or every check above is moot.
    only_sut, only_oracle = set_divergence(UNRENDERABLE_SET, ORACLE_UNRENDERABLE_SET)
    results.append((
        "control: the two set transcriptions agree",
        not only_sut and not only_oracle))

    # Common cause 3: branch labels. Making two of them the same string collapses
    # the five-way partition to four without any pair disagreeing, so a
    # uniqueness check is needed in addition to the pairwise cross-check.
    collided = ("(a) empty", "(a) empty", BRANCH_NO_LINE,
                BRANCH_UNRENDERABLE, BRANCH_UNDECODABLE)
    results.append((
        "colliding branch labels are detected",
        bool(branch_label_problems(collided, ORACLE_BRANCHES))))
    renamed = (BRANCH_EMPTY, "(b) RENAMED", BRANCH_NO_LINE,
               BRANCH_UNRENDERABLE, BRANCH_UNDECODABLE)
    results.append((
        "a one-sided branch label rename is detected",
        bool(branch_label_problems(renamed, ORACLE_BRANCHES))))
    results.append((
        "control: the two branch label transcriptions agree",
        not branch_label_problems(BRANCHES, ORACLE_BRANCHES)))

    # The uncovered member must actually be classified by the rule, so that a
    # deletion would change behaviour rather than being inert.
    branch, _ = carrier(b"\x01\n")
    results.append((
        "uncovered set member still classified unrenderable",
        branch == BRANCH_UNRENDERABLE))

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
        ("help with unknown flag rejected",
         parse_args(["--help", "--bogus"])[0] == 2),
        ("help with baseline rejected",
         parse_args(["--help", "--baseline"])[0] == 2),
        ("help with emit rejected",
         parse_args(["--help", "--emit-markdown"])[0] == 2),
        ("help with path rejected", parse_args(["-h", "stray.md"])[0] == 2),
        ("help with both modes rejected",
         parse_args(["--help", "--baseline", "--emit-markdown"])[0] == 2),
        ("help after other tokens rejected",
         parse_args(["--baseline", "--help"])[0] == 2),
        ("both help forms together rejected",
         parse_args(["-h", "--help"])[0] == 2),
        ("empty path rejected", parse_args(["--emit-markdown", ""])[0] == 2),
        ("whitespace-only path rejected",
         parse_args(["--emit-markdown", "   "])[0] == 2),
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
HELP_FLAGS = ("-h", "--help")


def parse_args(argv):
    """Return (exit_code, error_message, mode, path). exit_code 0 when accepted.

    The COMPLETE argv is validated before any mode is selected. An external
    review showed why: returning early on -h let `--help --bogus`,
    `--help --baseline --emit-markdown` and `-h stray.md` all exit 0, quietly
    reopening the argument domain that the manifest claimed was closed. `-h`
    and `--help` are therefore valid only on their own.
    """
    flags = [arg for arg in argv if arg.startswith("-")]
    positionals = [arg for arg in argv if not arg.startswith("-")]

    unknown = [arg for arg in flags if arg not in KNOWN_FLAGS and arg not in HELP_FLAGS]
    if unknown:
        return 2, "unknown argument(s): %s" % " ".join(unknown), None, None

    help_tokens = [arg for arg in flags if arg in HELP_FLAGS]
    if help_tokens:
        # "on its own" means exactly one token in the whole argv -- not merely
        # "no non-help tokens", which would still admit `-h --help`.
        if len(argv) != 1:
            return (2,
                    "-h/--help must be the only argument; got: %s" % " ".join(argv),
                    None, None)
        return 0, None, "help", None

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
    if any(not arg.strip() for arg in positionals):
        # An empty path used to be accepted and then died deep inside the write
        # with a FileNotFoundError traceback and exit 1 -- indistinguishable at
        # a glance from a rule failure, which is what exit 1 is reserved for.
        return (2, "--emit-markdown path must not be empty", None, None)

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


def result_digest(rows, counts, undefined, mismatches, unique, exhaustive, failures):
    """SHA-256 over sorted result lines.

    DETECTION RANGE, stated exactly. The payload binds:
      - every DIRECTED row: input bytes, expected and ACTUAL carrier;
      - AGGREGATE counts for the exhaustive and sampled layers.
    It therefore moves when a directed row's recorded carrier changes, or when
    any layer's counts change. It does NOT bind the carrier of an input that
    was never executed: an external review poisoned b"\x00" * 6 -- absent from
    the directed cases, from the length 0-2 exhaustive sweep, and from this
    seed's sample -- and the digest was unchanged. Errors on inputs never
    executed are OUTSIDE this digest's detection range.
    """
    lines = ["directed\t%s\t%s\t%s\t%s\t%s\t%s"
             % (name, repr(raw), expected_branch, repr(expected_carrier),
                actual_branch, repr(actual_carrier))
             for (name, raw, expected_branch, expected_carrier,
                  actual_branch, actual_carrier, ok) in rows]
    lines += ["fuzz\t%s\t%d" % (branch, counts[branch]) for branch in BRANCHES]
    lines += ["fuzz\tundefined\t%d" % undefined,
              "fuzz\tvalue_mismatches\t%d" % mismatches,
              "fuzz\tunique_inputs\t%d" % unique,
              "exhaustive\ttotal\t%d" % exhaustive[0],
              "exhaustive\tmismatches\t%d" % exhaustive[1],
              "directed\tfailures\t%d" % failures]
    payload = "\n".join(sorted(lines)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


CERT_LAYERS = (
    "directed",
    "comparator self-test",
    "common-cause self-test",
    "argv self-test",
    "exhaustive length 0-2",
    "sampled length 0-6",
)


def certification_state(directed_failures, selftest_failures, exhaustive_mismatches,
                        sampled_mismatches, undefined):
    """The ONE certification state, a conjunction over every verdict layer.

    An external review showed the cost of having more than one: emit_markdown()
    consumed only the directed layer, so poisoning carrier(b"\x00\x00") -- an
    input no directed case covers but the exhaustive sweep necessarily visits --
    produced an official table that recorded "1 mismatches" and "EVERY input
    agrees" at the same time, exit 0, and could atomically overwrite the
    committed evidence.

    Returns (certified, layers) where layers is a list of (name, ok, detail).
    """
    comparator_failed = [n for n in selftest_failures if n.startswith("comparator:")]
    common_failed = [n for n in selftest_failures if n.startswith("common-cause:")]
    argv_failed = [n for n in selftest_failures if n.startswith("argv:")]
    layers = [
        ("directed", directed_failures == 0,
         "%d failures" % directed_failures),
        ("comparator self-test", not comparator_failed,
         "%d failures" % len(comparator_failed)),
        ("common-cause self-test", not common_failed,
         "%d failures" % len(common_failed)),
        ("argv self-test", not argv_failed,
         "%d failures" % len(argv_failed)),
        ("exhaustive length 0-2", exhaustive_mismatches == 0,
         "%d mismatches" % exhaustive_mismatches),
        ("sampled length 0-6", sampled_mismatches == 0 and undefined == 0,
         "%d value mismatches, %d undefined" % (sampled_mismatches, undefined)),
    ]
    return all(ok for _, ok, _ in layers), layers


UNCERTIFIED_BANNER = (
    "# THIS TABLE DOES NOT CERTIFY THE RULE\n"
    "\n"
    "One or more verdict layers FAILED, so this output is diagnostic only. It was\n"
    "NOT written to the official table and must not be committed as evidence.\n"
)


GROUP_TITLES = {
    "A": "A group -- declared adversarial byte domain (process section 2.3)",
    "B": "B group -- the rule's unrenderable code-point set, plus visible neighbours",
    "C": 'C group -- the byte-level definition of "line"',
    "D": "D group -- UTF-8 decodability boundaries",
    "E": "E group -- replay of the gate outputs this Change Record records",
}


def emit_markdown(rows, failures, digest, summary, mismatches, unique, exhaustive,
                  certified, layers):
    """Emit the boundary-case table. Values are shown in full, untruncated.

    Every verdict layer feeds the conclusion. No sentence asserting agreement
    survives a failure in the layer it describes.
    """
    exhaustive_total, exhaustive_mismatches = exhaustive
    out = []
    if not certified:
        out.append(UNCERTIFIED_BANNER)
    out.append("# Boundary case table -- gate evidence carrier rule")
    out.append("")
    out.append("DO NOT EDIT BY HAND. Generated by `carrier_sweep.py --emit-markdown`;")
    out.append("regenerate rather than editing, or the result digest stops matching.")
    out.append("")
    out.append("Certification state: **%s**." % ("CERTIFIED" if certified else "NOT CERTIFIED"))
    out.append("")
    out.append("| verdict layer | result | status |")
    out.append("| --- | --- | --- |")
    for name, ok, detail in layers:
        out.append("| %s | %s | %s |" % (name, detail, "PASS" if ok else "**FAIL**"))
    out.append("")
    out.append("Directed cases: **%d**, failures: **%d**." % (len(rows), failures))
    out.append("A case passes only if BOTH its branch and its carrier value match the")
    out.append("independently constructed expectation, byte for byte. Inputs and")
    out.append("carriers are shown in full and are never truncated.")
    out.append("")
    out.append("Self-test attestation for the run that produced this table:")
    out.append("comparator %d/%d, common-cause %d/%d, argv %d/%d passed." % summary)
    out.append("Exhaustive sweep of all %d inputs of length 0-2: %d mismatches."
               % exhaustive)
    out.append("Sampled sweep: %d draws over lengths 0-6, %d unique inputs, %d "
               "value mismatches." % (ITERATIONS, unique, mismatches))
    out.append("These counts change under the mutation classes the self-tests")
    out.append("enumerate (wrong SHA, wrong byte count, wrong verbatim line, wrong")
    out.append("branch, wrong empty carrier, one-sided set or label edits); no claim")
    out.append("is made about mutation classes outside that enumeration.")
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
    if not certified:
        out.append("**This table does NOT certify the rule.** Failing layers:")
        out.append("")
        for name, ok, detail in layers:
            if not ok:
                out.append("- %s: %s" % (name, detail))
        out.append("")
    if failures == 0:
        out.append("- Directed: all %d cases match BOTH their expected branch and"
                   % len(rows))
        out.append("  their expected carrier value.")
    else:
        out.append("- Directed: **%d of %d cases FAILED** -- branch or carrier value"
                   % (failures, len(rows)))
        out.append("  differs from the independently constructed expectation:")
        for (name, raw, expected_branch, expected_carrier,
             actual_branch, actual_carrier, ok) in rows:
            if not ok:
                out.append("  - `%s`: expected `%s` / `%s`, got `%s` / `%s`"
                           % (name, expected_branch, repr(expected_carrier),
                              actual_branch, repr(actual_carrier)))
    if exhaustive_mismatches == 0:
        out.append("- Exhaustive: every input of length 0-2 (%d of them) agrees with"
                   % exhaustive_total)
        out.append("  the oracle. This universal claim is made over that subdomain only.")
    else:
        out.append("- Exhaustive: **%d of %d inputs of length 0-2 DISAGREE** with the"
                   % (exhaustive_mismatches, exhaustive_total))
        out.append("  oracle. No universal claim holds over this subdomain.")
    if mismatches == 0:
        out.append("- Sampled: each of the %d drawn inputs was oracle-compared for"
                   % ITERATIONS)
        out.append("  branch AND carrier value; %d unique inputs. What sampling cannot"
                   % unique)
        out.append("  establish is anything about inputs never drawn.")
    else:
        out.append("- Sampled: **%d drawn inputs DISAGREE** with the oracle." % mismatches)
    out.append("")
    out.append("See `run-manifest.md`, including its trusted-computing-base disclosure")
    out.append("and its forall-sentence audit.")
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
    common_cause_checks = selftest_common_cause()
    argv_checks = selftest_argv()
    failures = (["comparator: " + name for name, ok in comparator_checks if not ok]
                + ["common-cause: " + name for name, ok in common_cause_checks if not ok]
                + ["argv: " + name for name, ok in argv_checks if not ok])
    summary = (sum(1 for _, ok in comparator_checks if ok), len(comparator_checks),
               sum(1 for _, ok in common_cause_checks if ok), len(common_cause_checks),
               sum(1 for _, ok in argv_checks if ok), len(argv_checks))
    return comparator_checks, common_cause_checks, argv_checks, summary, failures


def _selftest_certification():
    """Prove the certification state actually flips when a layer fails.

    Three regressions the external review demanded, plus the all-green control.
    Each asserts BOTH that certification goes false and that the emitted
    conclusion text stops asserting agreement for the failing layer.
    """
    checks = []
    green = certification_state(0, [], 0, 0, 0)
    checks.append(("control: all layers green certifies", green[0]))

    exhaustive_bad = certification_state(0, [], 1, 0, 0)
    checks.append(("exhaustive failure blocks certification", not exhaustive_bad[0]))

    sampled_bad = certification_state(0, [], 0, 3, 0)
    checks.append(("sampled failure blocks certification", not sampled_bad[0]))

    selftest_bad = certification_state(0, ["comparator: x"], 0, 0, 0)
    checks.append(("self-test failure blocks certification", not selftest_bad[0]))

    undefined_bad = certification_state(0, [], 0, 0, 2)
    checks.append(("undefined input blocks certification", not undefined_bad[0]))

    directed_bad = certification_state(1, [], 0, 0, 0)
    checks.append(("directed failure blocks certification", not directed_bad[0]))

    # Conclusion text must follow the state, not just the exit code.
    rows, _ = run_directed()
    summary = (5, 5, 8, 8, 24, 24)
    text_bad = emit_markdown(rows, 0, "d", summary, 0, 1, (65793, 1),
                             exhaustive_bad[0], exhaustive_bad[1])
    checks.append(("failing exhaustive removes the universal agreement line",
                   "EVERY input" not in text_bad
                   and "every input of length 0-2 agrees" not in text_bad
                   and "does NOT certify" in text_bad))
    text_sampled = emit_markdown(rows, 0, "d", summary, 3, 1, (65793, 0),
                                 sampled_bad[0], sampled_bad[1])
    checks.append(("failing sampled layer is reported as failing",
                   "does NOT certify" in text_sampled
                   and "drawn inputs DISAGREE" in text_sampled))
    text_ok = emit_markdown(rows, 0, "d", summary, 0, 1, (65793, 0),
                            green[0], green[1])
    checks.append(("all-green table carries no uncertified banner",
                   "does NOT certify" not in text_ok
                   and "NOT CERTIFIED" not in text_ok))
    return checks


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

    if mode == "baseline":
        # Reporting mode: exit code carries no verdict. The baseline is EXPECTED
        # to be red, so tying its exit code to the failure count would invert
        # what a reader assumes.
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

    (comparator_checks, common_cause_checks, argv_checks,
     summary, selftest_failures) = selftest_summary()
    cert_checks = _selftest_certification()
    selftest_failures = selftest_failures + [
        "certification: " + name for name, ok in cert_checks if not ok]
    exhaustive = run_exhaustive()
    counts, undefined, mismatches, unique = run_fuzz()
    certified, layers = certification_state(
        failures, selftest_failures, exhaustive[1], mismatches, undefined)
    digest = result_digest(rows, counts, undefined, mismatches, unique,
                           exhaustive, failures)

    if mode == "emit":
        text = emit_markdown(rows, failures, digest, summary, mismatches, unique,
                             exhaustive, certified, layers)
        if not certified:
            # Never write an uncertified table to the official path, and never
            # exit 0 from a run whose verdict is negative. Diagnostic output
            # goes to stdout only, carrying its own banner.
            if path is not None:
                sys.stderr.write(
                    "carrier_sweep.py: refusing to write %s -- certification "
                    "FAILED\n" % path)
                for name, ok, detail in layers:
                    if not ok:
                        sys.stderr.write("  failing layer: %s (%s)\n" % (name, detail))
                sys.stderr.write(
                    "  diagnostic output: rerun without a PATH to print the "
                    "uncertified table on stdout\n")
                return 1
            sys.stdout.write(text)
            return 1
        if path is None:
            sys.stdout.write(text)
        else:
            write_atomically(path, text)
            sys.stderr.write("wrote %s\n" % path)
        return 0

    # Default mode. Its exit code is the certification verdict.
    _print_directed(rows, "CURRENT RULE")

    print("")
    print("== COMPARATOR SELF-TEST ==")
    print("mutated expectations must be REJECTED; the control must be ACCEPTED")
    for name, ok in comparator_checks:
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))

    print("")
    print("== COMMON-CAUSE SELF-TEST ==")
    print("attacks on data shared between the code under test and the checker")
    for name, ok in common_cause_checks:
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))

    print("")
    print("== ARGV SELF-TEST ==")
    for name, ok in argv_checks:
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))

    print("")
    print("== CERTIFICATION SELF-TEST ==")
    print("each verdict layer must be able to block certification")
    for name, ok in cert_checks:
        print("  %-52s %s" % (name, "PASS" if ok else "FAIL"))

    print("")
    print("== EXHAUSTIVE SWEEP, LENGTHS 0-%d ==" % EXHAUSTIVE_MAX_LEN)
    print("inputs checked: %d (every input of those lengths)" % exhaustive[0])
    print("value/branch mismatches vs independent oracle: %d" % exhaustive[1])

    print("")
    print("== SAMPLED SWEEP, LENGTHS 0-%d ==" % MAX_LEN)
    print("seed=%d draws=%d unique inputs=%d domain=all 256 byte values"
          % (SEED, ITERATIONS, unique))
    print("(the full length 0-%d domain is 282578800148737 inputs; this is a "
          "sample, not an exhaustion)" % MAX_LEN)
    for branch in BRANCHES:
        print("  %-44s %d" % (branch, counts[branch]))
    print("undefined/exception cases: %d" % undefined)
    print("value mismatches vs independent oracle: %d" % mismatches)
    print("note: each DRAWN input is oracle-compared for branch AND carrier value;")
    print("      what sampling cannot establish is anything about inputs never drawn.")

    print("")
    print("== CERTIFICATION ==")
    for name, ok, detail in layers:
        print("  %-28s %-32s %s" % (name, detail, "PASS" if ok else "FAIL"))
    print("  certified: %s" % ("YES" if certified else "NO"))
    print("self-test failures: %d" % len(selftest_failures))
    print("result digest (binds directed rows' actual carriers plus aggregate "
          "counts): %s" % digest)
    return 0 if certified else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
