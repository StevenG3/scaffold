#!/usr/bin/env python3
"""Adversarial sweep over the gate-evidence carrier rule.

This script is EVIDENCE MATERIAL of the bootstrap Change Record, not a reusable
Harness component: it is deliberately not registered in manifest.json.

It contains a mechanical implementation of the carrier rule as written in
`.harness/rules/project.md` section 2, then attacks that implementation with:

  1. DIRECTED cases drawn verbatim from the project's declared adversarial
     input domain (`docs/process/invariant-closure-design.md` section 2.3),
     plus every category of the fixed unrenderable code-point set the rule
     itself enumerates. Each directed case carries an EXPECTED branch, so the
     sweep validates the predicate, not merely its totality.
  2. RANDOM fuzzing over the full byte domain. Fuzzing can only show that no
     input escapes the partition; it cannot show that the partition places
     inputs in the RIGHT branch. That is precisely why the directed cases
     exist, and why a sweep built only from random input would be worthless
     as validation of the rule.

Deterministic: standard library only, fixed seed, no clock or environment
input. Re-running on any Python 3.9+ reproduces the same result digest.

Usage:  python3 carrier_sweep.py
Exit:   0 if every directed case matches its expected branch and no input
        escapes the partition; 1 otherwise.

Note on source encoding: unrenderable code points appear in this file only as
escape sequences (for example "\\u0085"), never as literal characters, so the
script itself stays reviewable in a plain text diff.
"""

import hashlib
import random
import sys

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
    + list(range(0xFE00, 0xFE10))    # variation selectors
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


def _digest(raw):
    return "bytes=%d sha256=%s" % (len(raw), hashlib.sha256(raw).hexdigest())


def carrier(raw):
    """Mechanical implementation of the carrier rule. Total over all bytes."""
    if len(raw) == 0:
        return BRANCH_EMPTY, "<empty>"

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


# ---------------------------------------------------------------------------
# Directed cases.
#
# Group A mirrors, item by item, the declared adversarial byte domain in
# docs/process/invariant-closure-design.md section 2.3.
# Group B covers every category of the rule's unrenderable code-point set.
# Group C attacks the byte-level definition of "line".
# Group D attacks UTF-8 decodability boundaries.
# Group E replays the real gate outputs recorded by this Change Record.
# ---------------------------------------------------------------------------
DIRECTED = [
    # -- Group A: declared adversarial byte domain (section 2.3) --
    ("A CRLF line ending", b"OK\r\n", BRANCH_LINE),
    ("A CRLF only", b"\r\n", BRANCH_NO_LINE),
    ("A no trailing newline", b"OK", BRANCH_LINE),
    ("A empty stream", b"", BRANCH_EMPTY),
    ("A non-ASCII CJK", "\u5951\u7ea6\u6709\u6548\u3002\n".encode("utf-8"), BRANCH_LINE),
    ("A non-ASCII emoji", "done \U0001f600\n".encode("utf-8"), BRANCH_LINE),
    ("A C0 control NUL", b"\x00\n", BRANCH_UNRENDERABLE),
    ("A C0 control BEL", b"\x07\n", BRANCH_UNRENDERABLE),
    ("A DEL U+007F", b"\x7f\n", BRANCH_UNRENDERABLE),
    ("A NEL U+0085", "A\u0085B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("A U+2028 line sep", "A\u2028B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("A U+2029 para sep", "A\u2029B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("A surrogate bytes D800", b"\xed\xa0\x80", BRANCH_UNDECODABLE),
    ("A surrogate bytes DFFF", b"\xed\xbf\xbf", BRANCH_UNDECODABLE),
    ("A literal escape vs real char", b"line\\nnot-a-newline\n", BRANCH_LINE),
    ("A literal <empty> collision", b"<empty>\n", BRANCH_LINE),
    # -- Group B: the rule's unrenderable code-point set --
    ("B C1 control U+0080", "A\u0080B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B C1 control U+009F", "A\u009fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B SOFT HYPHEN U+00AD", "A\u00adB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ARABIC LETTER MARK U+061C", "A\u061cB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ZWSP U+200B", "A\u200bB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ZWNJ U+200C", "A\u200cB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ZWJ U+200D", "A\u200dB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LRM U+200E", "A\u200eB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B RLM U+200F", "A\u200fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LRE U+202A", "A\u202aB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B RLO U+202E", "A\u202eB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B WORD JOINER U+2060", "A\u2060B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B INVISIBLE TIMES U+2062", "A\u2062B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B INVISIBLE PLUS U+2064", "A\u2064B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LRI U+2066", "A\u2066B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B FSI U+2068", "A\u2068B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B PDI U+2069", "A\u2069B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B INHIBIT SYMMETRIC SWAP U+206A", "A\u206aB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B NOMINAL DIGIT SHAPES U+206F", "A\u206fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B VARIATION SELECTOR-1 U+FE00", "A\ufe00B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B VARIATION SELECTOR-16 U+FE0F", "A\ufe0fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ANNOTATION ANCHOR U+FFF9", "A\ufff9B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B ANNOTATION TERMINATOR U+FFFB", "A\ufffbB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B BOM U+FEFF", "\ufeffOK\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LANGUAGE TAG U+E0001", "A\U000e0001B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B TAG LATIN SMALL A U+E0061", "A\U000e0061B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B CANCEL TAG U+E007F", "A\U000e007fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    # Visible neighbours just outside the set. These MUST stay verbatim.
    # Every one is an assigned, visible (or visibly spacing) character; the set
    # makes no claim about unassigned code points, so none are used here.
    ("B neighbour U+00A0 NBSP visible-spacing", "A\u00a0B\n".encode("utf-8"), BRANCH_LINE),
    ("B neighbour U+2010 HYPHEN visible", "A\u2010B\n".encode("utf-8"), BRANCH_LINE),
    ("B neighbour U+2027 HYPHENATION POINT visible", "A\u2027B\n".encode("utf-8"), BRANCH_LINE),
    ("B neighbour U+202F NNBSP visible-spacing", "A\u202fB\n".encode("utf-8"), BRANCH_LINE),
    ("B neighbour U+3000 IDEOGRAPHIC SPACE visible-spacing", "A\u3000B\n".encode("utf-8"), BRANCH_LINE),
    # -- Group C: byte-level definition of "line" --
    ("C lone LF", b"\n", BRANCH_NO_LINE),
    ("C lone CR", b"\r", BRANCH_NO_LINE),
    ("C several blank lines", b"\n\n\n", BRANCH_NO_LINE),
    ("C several CRLF blanks", b"\r\n\r\n", BRANCH_NO_LINE),
    ("C single space line", b" \n", BRANCH_LINE),
    ("C spaces no newline", b"   ", BRANCH_LINE),
    ("C trailing blanks after text", b"OK\n\n\n", BRANCH_LINE),
    ("C trailing CRLF blanks after text", b"OK\r\n\r\n", BRANCH_LINE),
    ("C CR inside line not trailing", b"A\rB\n", BRANCH_UNRENDERABLE),
    ("C only one trailing CR stripped", b"OK\r\r\n", BRANCH_UNRENDERABLE),
    ("C lone CR line", b"\r\r\n", BRANCH_UNRENDERABLE),
    # -- Group D: UTF-8 decodability boundaries --
    ("D undecodable tail byte", b"OK\n\xff", BRANCH_UNDECODABLE),
    ("D undecodable no non-empty line", b"\n\xff", BRANCH_UNDECODABLE),
    ("D truncated multi-byte seq", "\u5951".encode("utf-8")[:2], BRANCH_UNDECODABLE),
    ("D overlong encoding of slash", b"\xc0\xaf", BRANCH_UNDECODABLE),
    ("D two-byte boundary U+07FF", "\u07ff\n".encode("utf-8"), BRANCH_LINE),
    ("D four-byte astral plane", "\U0001f600\n".encode("utf-8"), BRANCH_LINE),
    # -- Group E: real gate outputs recorded by this Change Record --
    ("E gate 1/2/6 stdout", b"Harness contract is valid.\n", BRANCH_LINE),
    ("E gate 3 stdout two lines",
     b"[ADAPT_SKIPPED_TEMPLATE] .: origin is null\nadapt: ok\n", BRANCH_LINE),
    ("E gate 4 stderr tail",
     b"Ran 175 tests in 12.316s\n\nOK (skipped=2)\n", BRANCH_LINE),
    ("E gate 5 both streams", b"", BRANCH_EMPTY),
]


BASELINE_UNRENDERABLE_BYTES = frozenset(list(range(0x00, 0x20)) + [0x7F])


def carrier_baseline(raw):
    """The PRE-FIX predicate, kept so the fix can be shown to go red on it.

    This is the rule as it stood before the unrenderable code-point set was
    introduced: the unrenderable test looked at raw BYTES for C0/DEL only, so
    every strictly-decodable invisible character (NEL, U+2028, bidi controls,
    zero-width characters, ...) was classified as renderable verbatim.
    """
    if len(raw) == 0:
        return BRANCH_EMPTY, "<empty>"
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


def run_directed(predicate=carrier):
    rows = []
    failures = 0
    for name, raw, expected in DIRECTED:
        branch, recorded = predicate(raw)
        ok = branch == expected
        if not ok:
            failures += 1
        rows.append((name, raw, expected, branch, recorded, ok))
    return rows, failures


def run_fuzz():
    rng = random.Random(SEED)
    counts = {branch: 0 for branch in BRANCHES}
    undefined = 0
    for _ in range(ITERATIONS):
        raw = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, MAX_LEN)))
        try:
            branch, recorded = carrier(raw)
        except Exception:  # noqa: BLE001 - any escape at all is a rule defect
            undefined += 1
            continue
        if branch not in counts or not recorded:
            undefined += 1
        else:
            counts[branch] += 1
    return counts, undefined


GROUP_TITLES = {
    "A": "A group -- declared adversarial byte domain (process section 2.3)",
    "B": "B group -- the rule's unrenderable code-point set, plus visible neighbours",
    "C": 'C group -- the byte-level definition of "line"',
    "D": "D group -- UTF-8 decodability boundaries",
    "E": "E group -- replay of the gate outputs this Change Record records",
}


def result_digest(rows, counts, undefined, failures):
    """SHA-256 over sorted result lines.

    The input bytes are bound into the payload, so editing a case's input
    without re-running changes the digest.
    """
    lines = ["directed\t%s\t%s\t%s\t%s" % (name, repr(raw), expected, branch)
             for name, raw, expected, branch, recorded, ok in rows]
    lines += ["fuzz\t%s\t%d" % (branch, counts[branch]) for branch in BRANCHES]
    lines += ["fuzz\tundefined\t%d" % undefined,
              "directed\tfailures\t%d" % failures]
    payload = "\n".join(sorted(lines)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def emit_markdown(rows, failures, digest):
    """Emit boundary-cases.md on stdout. Inputs are shown in full, untruncated."""
    out = []
    out.append("# Boundary case table -- gate evidence carrier rule")
    out.append("")
    out.append("DO NOT EDIT BY HAND. Generated by `carrier_sweep.py --emit-markdown`;")
    out.append("regenerate rather than editing, or the result digest stops matching.")
    out.append("")
    out.append("Directed cases: **%d**, failures: **%d**." % (len(rows), failures))
    out.append("Input bytes are shown as a full Python `repr`, never truncated and never")
    out.append("as literal control characters.")
    out.append("")
    out.append("Result digest: `%s`" % digest)
    for key in "ABCDE":
        subset = [r for r in rows if r[0].startswith(key + " ")]
        if not subset:
            continue
        out.append("")
        out.append("## " + GROUP_TITLES[key])
        out.append("")
        out.append("| case | input bytes | expected | actual | status |")
        out.append("| --- | --- | --- | --- | --- |")
        for name, raw, expected, branch, recorded, ok in subset:
            escaped = repr(raw).replace("|", "\\|")
            out.append("| %s | `%s` | `%s` | `%s` | %s |"
                       % (name[2:], escaped, expected, branch,
                          "PASS" if ok else "**FAIL**"))
    out.append("")
    out.append("## Conclusion")
    out.append("")
    out.append("All %d directed cases land in their expected branch; failures: %d."
               % (len(rows), failures))
    out.append("")
    out.append("Directed cases are what validate the PREDICATE (is each input placed in")
    out.append("the right branch). Random fuzzing can only show that no input escapes the")
    out.append("partition. Neither substitutes for the other -- see `run-manifest.md`.")
    return "\n".join(out) + "\n"


def main(argv):
    baseline = "--baseline" in argv
    predicate = carrier_baseline if baseline else carrier
    rows, failures = run_directed(predicate)

    if "--emit-markdown" in argv:
        counts, undefined = run_fuzz()
        digest = result_digest(rows, counts, undefined, failures)
        sys.stdout.write(emit_markdown(rows, failures, digest))
        return 0 if failures == 0 and undefined == 0 else 1

    label = "BASELINE (pre-fix predicate)" if baseline else "CURRENT RULE"
    print("== DIRECTED CASES -- %s ==" % label)
    print("%-52s %-44s %-44s %s" % ("case", "expected", "actual", "status"))
    for name, raw, expected, branch, recorded, ok in rows:
        print("%-52s %-44s %-44s %s"
              % (name, expected, branch, "PASS" if ok else "FAIL"))
    print("")
    print("directed cases: %d, failures: %d" % (len(rows), failures))
    if baseline:
        print("")
        print("Baseline is EXPECTED to be red. Cases that the pre-fix predicate got wrong:")
        for name, raw, expected, branch, recorded, ok in rows:
            if not ok:
                print("  %-52s expected %-44s got %s" % (name, expected, branch))
        return 0

    counts, undefined = run_fuzz()
    print("")
    print("== RANDOM FUZZ ==")
    print("seed=%d iterations=%d max_len=%d domain=all 256 byte values"
          % (SEED, ITERATIONS, MAX_LEN))
    for branch in BRANCHES:
        print("  %-44s %d" % (branch, counts[branch]))
    print("undefined/exception cases: %d" % undefined)
    print("note: fuzzing shows only that no input escapes the partition; the")
    print("      directed cases above are what validate the predicate itself.")
    print("")
    print("result digest (sha256 of sorted result lines, input bytes bound in): %s"
          % result_digest(rows, counts, undefined, failures))
    return 0 if failures == 0 and undefined == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
