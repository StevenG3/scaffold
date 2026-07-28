#!/usr/bin/env python3
"""Forbid current-state numeric assertions outside the generated table.

Mechanism authority: the "checker as it stands" (SSOT) section of
run-manifest.md. That section is the only place the domain, the marker
vocabulary, the exemption families, the self-test form and the freeze clause
are described; this docstring deliberately does not restate them, because a
second description is a second thing that can go stale.

In outline: markdown files are scanned in full and Python files in their prose
lines; a line pairing a current-state marker with a number is a violation;
exemptions fall into three families. Details live in the SSOT section.

Usage:  python3 check_current_numbers.py            # scan
        python3 check_current_numbers.py --self-test  # prove it can fail

Exit codes are listed in the SSOT section's mechanism table.

Note on source encoding: carrier_sweep.py holds a pure-ASCII discipline because
its source is hashed and attested. THIS file is not pure ASCII and cannot be:
the marker words it forbids are Chinese, so they appear here verbatim.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD_DIR = os.path.dirname(HERE)

# The generated table is the ONLY place a current-state number may live.
GENERATED_ARTIFACT = "boundary-cases.md"

# Current-state marker words. Explicit list; extend here when the record starts
# using a new way of saying "as of now" -- the same standing obligation the
# forall collector's keyword list carries.
CURRENT_STATE_MARKERS = (
    # Chinese. The first review of this list found it missing the corpus's
    # dominant vocabulary -- a marker list is only as good as its enumeration,
    # the same standing obligation the forall collector's keywords carry.
    "当前",
    "现为",
    "现有",
    "现在",
    "现行",
    "此时",
    "如今",
    "目前",
    "实测",
    "本轮",
    "最新",
    # English, for the .py prose that entered the domain this round.
    "now",
    "currently",
    "at present",
    "as of",
)

# Counting words that only assert current state when paired with a quantifier.
# Scanning them unconditionally floods the output; requiring the quantifier
# keeps them meaningful without creating a blind spot.
COUNTING_MARKERS = ("共", "合计", "总计")
QUANTIFIERS = ("项", "个", "条", "行", "处", "次")
# 共 is also the first character of 共因 / 共享 / 共同 / 共存, which assert
# nothing about counts. A counting use is followed by a digit or by 计.
COUNTING_COMPOUNDS = ("共因", "共享", "共同", "共存", "共用", "公共")

# Number tokens, plain and comma-grouped. Backticks are NOT stripped first:
# `137,527` must be caught exactly like 137,527.
NUMBER_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")

# Exemption 1: an EXPLICIT binding token, not a co-occurrence.
#
# The previous form exempted any line containing 历史 and a loose hex string.
# A review smuggled current-state figures past it twice by quoting a commit id
# in the same sentence: co-occurrence is not a statement of intent. The token
# below has to be written deliberately, and it binds the figure on that line to
# one round's HEAD.
HISTORY_BINDING = re.compile(r"历史@[0-9a-f]{7,40}")

# Exemption 2: the artifact invariants, enumerated here and mirrored verbatim
# in run-manifest.md's whitelist table.
INVARIANT_PATTERNS = (
    r"\b[0-9a-f]{64}\b",   # script SHA-256 and result digest are 64 hex chars
)

# Structural numerals that assert nothing about measured state.
#
# The Change Record's own directory name carries a date. It is a PATH COMPONENT,
# enumerated here as one literal -- not a class of syntax. This is deliberately
# narrower than the blinding that was breached before: that version exempted
# every backticked span, which let any figure hide behind a pair of backticks.
STRUCTURAL_PATTERNS = (
    r"2026-07-27-bootstrap-adoption-1",
    r"U\+[0-9A-Fa-f]{4,6}",      # code points
    r"0x[0-9A-Fa-f]+",           # byte literals
    r"Python 3\.\d+(?:\.\d+)?",  # interpreter version
    r"SHA-?256",                 # algorithm name
    r"第 \d+ 步",                 # protocol step numbers
    r"第 \d+ 轮",                 # review round numbers
    r"^\|\s*\d+\s*\|",           # leading table row number (audit rows)
    r"§\s*\d+",                  # rule section references
    r"R\d+[a-z]?",               # round labels such as R7, R10b
    r"\bv\d+\b",                 # product version labels such as v0, v3
    r"Errno \d+",                # errno names quoted in messages
    r"\b(?:[A-Z]-)*[A-Z]{1,2}\d+[a-z]?\b",  # finding labels: I1, C1, M2, A-C1, B-S-I2
    r"\bexit \d\b",              # exit-code semantics
    r"退出 \d",
)


def scanned_files():
    """Every .md and every .py in the Change Record, minus the generated table.

    The seventh recurrence of the stale-figure defect hid in a COMMENT of the
    attested script: the domain had been closed along the axis that was
    breached (line windows, quoting style) and left open along two others --
    file extension, and marker vocabulary. Closing a domain means enumerating
    every carrier axis, not the one that happened to fail.
    """
    found = []
    for root, _dirs, files in os.walk(RECORD_DIR):
        for name in sorted(files):
            if name == GENERATED_ARTIFACT:
                continue
            if name.endswith(".md") or name.endswith(".py"):
                found.append(os.path.join(root, name))
    return sorted(found)


TRIPLE_QUOTE = re.compile(r'\"\"\"|\'\'\'')


def prose_lines(path, lines):
    """Yield (line_number, line) for lines that carry PROSE.

    For markdown that is every line. For Python it is comment lines and
    docstring bodies only: a number inside code is the code's business, but a
    number inside a comment is an assertion aimed at a reader, and that is
    exactly where the seventh recurrence lived.
    """
    if not path.endswith(".py"):
        for number, line in enumerate(lines, start=1):
            yield number, line
        return
    in_doc = False
    for number, line in enumerate(lines, start=1):
        quotes = len(TRIPLE_QUOTE.findall(line))
        stripped = line.strip()
        if in_doc:
            yield number, line
            if quotes % 2 == 1:
                in_doc = False
            continue
        if stripped.startswith("#"):
            yield number, line
            continue
        if quotes % 2 == 1:
            yield number, line
            in_doc = True
            continue
        opens_docstring = (
            stripped.startswith('\"\"\"')
            or stripped.startswith("'''")
            or stripped.startswith('r\"\"\"')
            or stripped.startswith("r'''")
        )
        if quotes >= 2 and opens_docstring:
            # A single-line docstring: """text""" opens and closes on one line,
            # so the odd-count test never saw it and the line was skipped
            # entirely. The axis table claimed docstrings were covered, so this
            # is a gap inside a stated construction guarantee, not an
            # expansion of the detector. The line must OPEN with the
            # quotes: a code line that merely contains a triple-quoted
            # literal -- this file's own self-test variants, say --
            # stays code, which is the '.py code strings' axis the
            # carrier table marks open.
            yield number, line


def _strip_exempt(line):
    stripped = line
    for pattern in INVARIANT_PATTERNS + STRUCTURAL_PATTERNS:
        stripped = re.sub(pattern, " ", stripped)
    return stripped


def line_violations(line):
    """Return (marker, token) pairs that make this line a violation."""
    if HISTORY_BINDING.search(line):
        return []                      # exemption 1: explicitly bound to a HEAD
    markers = [marker for marker in CURRENT_STATE_MARKERS if marker in line]
    if not markers:
        for counter in COUNTING_MARKERS:
            probe = line
            for compound in COUNTING_COMPOUNDS:
                probe = probe.replace(compound, " ")
            if counter in probe and any(q in probe for q in QUANTIFIERS):
                markers = [counter]
                break
    if not markers:
        return []
    tokens = NUMBER_TOKEN.findall(_strip_exempt(line))
    if not tokens:
        return []
    return [(markers[0], token) for token in tokens]


def scan(injections=None):
    """Scan the corpus. injections maps a path to extra lines to splice in."""
    violations = []
    for path in scanned_files():
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        if injections and path in injections:
            lines = list(lines) + list(injections[path])
        for number, line in prose_lines(path, lines):
            for marker, token in line_violations(line):
                violations.append((os.path.relpath(path, RECORD_DIR),
                                   number, marker, token, line.strip()))
    return violations


SELF_TEST_VARIANTS = (
    "当前定向用例为 9999",
    "当前唯一输入数为 137,527",
    "当前认证自检为 `9999` 项",
    # The two escapes a review drove through the old co-occurrence exemption:
    # quoting a commit id beside the word 历史 used to launder any figure.
    "历史 c399394 参照：现在定向用例为 9999",
    "参见历史提交 fd8032ca，实测认证自检 9999 项",
    # English prose, for the .py comment domain.
    "# directed cases (69 of them at the time; 9999 now)",
    # Single-line docstring, the shape C2 showed was never scanned.
    '    """当前定向用例为 9999"""',
)


def self_test():
    """Inject every variant into every scanned file -- a true cross product.

    The previous version rotated one variant per file and exercised the full
    set on the first file only, while printing "every file and every notation".
    A check shown to fail on one file in one notation has only been shown to
    fail there. Everything goes through the real scan path; nothing is written.
    """
    baseline = scan()
    print("clean scan violations: %d" % len(baseline))
    files = scanned_files()
    if not files:
        print("SELF-TEST FAILED: no files to scan")
        return 1
    misses = []
    for path in files:
        rel = os.path.relpath(path, RECORD_DIR)
        for variant in SELF_TEST_VARIANTS:
            already_python = variant.lstrip().startswith(("#", '"""'))
            injected = variant if (not path.endswith(".py") or already_python) \
                else "# " + variant
            dirty = scan(injections={path: [injected]})
            caught = len(dirty) > len(baseline)
            print("  %-26s variant=%-30s caught=%s" % (rel, variant[:30], caught))
            if not caught:
                misses.append((rel, variant))
    if misses:
        print("SELF-TEST FAILED: injections not caught: %r" % (misses,))
        return 1
    print("SELF-TEST PASSED: %d file(s) x %d variant(s), every combination caught"
          % (len(files), len(SELF_TEST_VARIANTS)))
    print("(injections were in-memory only; no file was modified)")
    return 0


def main(argv):
    if argv and argv != ["--self-test"]:
        sys.stderr.write("usage: check_current_numbers.py [--self-test]\n")
        return 2
    if not os.path.isdir(RECORD_DIR):
        sys.stderr.write("missing Change Record directory: %s\n" % RECORD_DIR)
        return 2
    if argv == ["--self-test"]:
        return self_test()
    violations = scan()
    if not violations:
        print("no current-state numeric assertion outside %s" % GENERATED_ARTIFACT)
        print("scanned %d file(s) (.md in full, .py prose lines)"
              % len(scanned_files()))
        return 0
    print("current-state numeric assertion(s) outside %s:" % GENERATED_ARTIFACT)
    for rel, number, marker, token, line in violations:
        print("  %s:%d  marker=%s token=%s" % (rel, number, marker, token))
        print("      %s" % line[:160])
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
