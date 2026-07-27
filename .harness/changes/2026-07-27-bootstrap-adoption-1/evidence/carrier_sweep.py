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
    + [0x2028, 0x2029]               # line / paragraph separators
    + [0x200E, 0x200F]               # LRM / RLM
    + list(range(0x202A, 0x202F))    # LRE RLE PDF LRO RLO
    + list(range(0x2066, 0x206A))    # LRI RLI FSI PDI
    + [0xFEFF]                       # BOM / ZWNBSP
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
    ("B LRM U+200E", "A\u200eB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B RLM U+200F", "A\u200fB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LRE U+202A", "A\u202aB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B RLO U+202E", "A\u202eB\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B LRI U+2066", "A\u2066B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B FSI U+2068", "A\u2068B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B PDI U+2069", "A\u2069B\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    ("B BOM U+FEFF", "\ufeffOK\n".encode("utf-8"), BRANCH_UNRENDERABLE),
    # Boundary neighbours just outside the set: these MUST stay verbatim.
    ("B boundary U+00A0 renderable", "A\u00a0B\n".encode("utf-8"), BRANCH_LINE),
    ("B boundary U+2027 renderable", "A\u2027B\n".encode("utf-8"), BRANCH_LINE),
    ("B boundary U+202F renderable", "A\u202fB\n".encode("utf-8"), BRANCH_LINE),
    ("B boundary U+2065 renderable", "A\u2065B\n".encode("utf-8"), BRANCH_LINE),
    ("B boundary U+206A renderable", "A\u206aB\n".encode("utf-8"), BRANCH_LINE),
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


def run_directed():
    rows = []
    failures = 0
    for name, raw, expected in DIRECTED:
        branch, recorded = carrier(raw)
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


def main():
    rows, failures = run_directed()
    print("== DIRECTED CASES ==")
    print("%-36s %-40s %-40s %s" % ("case", "expected", "actual", "status"))
    for name, raw, expected, branch, recorded, ok in rows:
        print("%-36s %-40s %-40s %s" % (name, expected, branch, "PASS" if ok else "FAIL"))
    print("")
    print("directed cases: %d, failures: %d" % (len(rows), failures))

    counts, undefined = run_fuzz()
    print("")
    print("== RANDOM FUZZ ==")
    print("seed=%d iterations=%d max_len=%d domain=all 256 byte values"
          % (SEED, ITERATIONS, MAX_LEN))
    for branch in BRANCHES:
        print("  %-40s %d" % (branch, counts[branch]))
    print("undefined/exception cases: %d" % undefined)
    print("note: fuzzing shows only that no input escapes the partition; the")
    print("      directed cases above are what validate the predicate itself.")

    # Result digest: SHA-256 over the sorted, normalised result lines.
    lines = ["directed\t%s\t%s\t%s" % (name, expected, branch)
             for name, raw, expected, branch, recorded, ok in rows]
    lines += ["fuzz\t%s\t%d" % (branch, counts[branch]) for branch in BRANCHES]
    lines += ["fuzz\tundefined\t%d" % undefined,
              "directed\tfailures\t%d" % failures]
    payload = "\n".join(sorted(lines)) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print("")
    print("result digest (sha256 of sorted result lines): %s" % digest)
    return 0 if failures == 0 and undefined == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
