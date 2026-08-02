#!/usr/bin/env python3
"""Forbid current-state numeric assertions outside the generated table.

Mechanism authority: the "checker as it stands" (SSOT) section of
run-manifest.md. That section is the only place the domain, the marker
vocabulary, the exemption families, the self-test form and the freeze clause
are described; this docstring deliberately does not restate them, because a
second description is a second thing that can go stale.

Usage:  python3 check_current_numbers.py            # scan
        python3 check_current_numbers.py --self-test  # prove it can fail

Exit codes are listed in the SSOT section's mechanism table.

Note on source encoding: carrier_sweep.py holds a pure-ASCII discipline because
its source is hashed and attested. THIS file is not pure ASCII and cannot be:
the marker words it forbids are Chinese, so they appear here verbatim.
"""

import ast
import io
import os
import re
import sys
import shutil
import tempfile
import tokenize

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

# Exemption 2: the artifact invariants. What they are and why they are exempt
# is stated once, in the SSOT section of run-manifest.md; the whitelist table
# this comment used to name was withdrawn, and naming it kept a withdrawn
# framework alive in a second place. Note what this exemption costs: it lets
# ANY 64-hex run pass, so a stale hand-copied invariant is invisible here by
# construction -- it is guarded by checklist rows, not by this file.
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


class UnparsablePython(Exception):
    """Raised when a .py file in the domain cannot be tokenized or parsed."""


def _comment_carriers(source):
    """Yield (line_number, source_fragment) for COMMENT tokens."""
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        if token.type == tokenize.COMMENT:
            yield token.start[0], token.string


def _docstring_carriers(source):
    """Yield (line_number, source_fragment) for docstring nodes."""
    tree = ast.parse(source)
    lines = source.split("\n")
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        start, end = first.lineno, getattr(first, "end_lineno", first.lineno)
        col, end_col = first.col_offset, getattr(first, "end_col_offset", None)
        for number in range(start, end + 1):
            text = lines[number - 1]
            # Only the literal's own columns are prose (SSOT).
            left = col if number == start else 0
            right = end_col if (number == end and end_col is not None) else len(text)
            yield number, text[left:right]


def prose_carriers(path, source):
    """Yield (line_number, source_fragment) for fragments carrying prose.

    Domain: see the SSOT section of run-manifest.md.
    """
    if not path.endswith(".py"):
        for number, line in enumerate(source.split("\n"), start=1):
            yield number, line
        return
    try:
        carriers = sorted(set(_comment_carriers(source))
                          | set(_docstring_carriers(source)))
    except (SyntaxError, tokenize.TokenError, IndentationError, ValueError) as exc:
        raise UnparsablePython("%s: %s" % (path, exc))
    for number, fragment in carriers:
        yield number, fragment


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


def read_source(path):
    """Return a file's source text unchanged, honouring its coding cookie."""
    if path.endswith(".py"):
        with tokenize.open(path) as handle:
            return handle.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def scan(injections=None):
    """Scan the corpus. injections maps a path to source text to append."""
    violations = []
    for path in scanned_files():
        source = read_source(path)
        if injections and path in injections:
            suffix = injections[path]
            if not source.endswith("\n"):
                source += "\n"
            source += suffix if suffix.endswith("\n") else suffix + "\n"
        try:
            carriers = list(prose_carriers(path, source))
        except UnparsablePython as exc:
            # Fail closed: an unscannable file is an unknown, not a pass.
            violations.append((os.path.relpath(path, RECORD_DIR), 0,
                               "UNPARSABLE", "-", str(exc)))
            continue
        for number, fragment in carriers:
            for marker, token in line_violations(fragment):
                violations.append((os.path.relpath(path, RECORD_DIR),
                                   number, marker, token, fragment.strip()))
    return violations


# Independent syntactic-form matrix for the .py domain.
#
# Each row is (label, source, expected carriers, expected violations). Both
# expectations are WRITTEN DOWN -- a test whose oracle is the code under test
# proves only self-consistency. The carrier column is what makes the open axis
# checkable: it pins which SOURCE FRAGMENT is prose, not merely which line
# holds one, so code sharing a line with a comment stays out of the domain.
#
# Prefixes are enumerated even though ast resolves them, because an
# unenumerated prefix is exactly what an earlier round got wrong.
MARK = "当前定向用例为 9999"
HIT = [("当前", "9999")]

PROSE_FORM_MATRIX = (
    ("bare single-line docstring", '"""%s"""\n' % MARK,
     [(1, '"""%s"""' % MARK)], [HIT]),
    ("r single-line docstring", 'r"""%s"""\n' % MARK,
     [(1, 'r"""%s"""' % MARK)], [HIT]),
    ("u single-line docstring", 'u"""%s"""\n' % MARK,
     [(1, 'u"""%s"""' % MARK)], [HIT]),
    ("U single-line docstring", 'U"""%s"""\n' % MARK,
     [(1, 'U"""%s"""' % MARK)], [HIT]),
    ("R single-line docstring", 'R"""%s"""\n' % MARK,
     [(1, 'R"""%s"""' % MARK)], [HIT]),
    ("single-quote docstring", "%s%s%s\n" % ("'" * 3, MARK, "'" * 3),
     [(1, "%s%s%s" % ("'" * 3, MARK, "'" * 3))], [HIT]),
    ("multi-line docstring", '"""\n%s\n"""\n' % MARK,
     [(1, '"""'), (2, MARK), (3, '"""')], [[], HIT, []]),
    ("whole-line comment", "# %s\n" % MARK, [(1, "# %s" % MARK)], [HIT]),
    ("indented whole-line comment", "def f():\n    # %s\n    return 1\n" % MARK,
     [(2, "# %s" % MARK)], [HIT]),
    ("inline comment", "x = 1  # %s\n" % MARK, [(1, "# %s" % MARK)], [HIT]),
    ("function docstring", 'def f():\n    """%s"""\n    return 1\n' % MARK,
     [(2, '"""%s"""' % MARK)], [HIT]),
    ("class docstring", 'class C:\n    """%s"""\n' % MARK,
     [(2, '"""%s"""' % MARK)], [HIT]),
    ("async function docstring",
     'async def f():\n    """%s"""\n    return 1\n' % MARK,
     [(2, '"""%s"""' % MARK)], [HIT]),
    # --- the open axis: code strings never become prose ---
    ("assigned multi-line string", 'PAYLOAD = """\n%s\n"""\n' % MARK, [], []),
    ("assigned single-line string", 'PAYLOAD = "%s"\n' % MARK, [], []),
    ("string in a call", 'print("%s")\n' % MARK, [], []),
    ("second statement string", 'x = 1\n"""%s"""\n' % MARK, [], []),
    ("b prefix first statement", 'b"""currently 9999"""\n', [], []),
    ("f prefix first statement", 'f"""%s"""\n' % MARK, [], []),
    # --- the review's bidirectional cases: one line, two axes ---
    ("code string + harmless comment",
     'payload = "%s"  # harmless note\n' % MARK,
     [(1, "# harmless note")], [[]]),
    ("code number + marker-only comment",
     "payload = 9999  # 当前配置\n", [(1, "# 当前配置")], [[]]),
    ("code marker + number-only comment",
     'payload = "当前"  # 9999 items\n', [(1, "# 9999 items")], [[]]),
    ("same-line docstring + numeric name",
     'def f9999(): "当前配置"\n', [(1, '"当前配置"')], [[]]),
    ("docstring after semicolon code",
     'x = 9999; y = 2\n', [], []),
    # --- reading layer: the parser must see the file's real bytes ---
    ("U+2028 inside a legal comment",
     "# note\u2028%s\nx = 1\n" % MARK,
     [(1, "# note\u2028%s" % MARK)], [HIT]),
    ("CRLF line endings", "# %s\r\nx = 1\r\n" % MARK,
     [(1, "# %s" % MARK)], [HIT]),
    ("no trailing newline", "x = 1  # %s" % MARK,
     [(1, "# %s" % MARK)], [HIT]),
)

# Sources that must fail closed rather than be silently normalised into
# something parsable.
UNPARSABLE_SAMPLES = (
    ("broken def", "def f(:\n    pass\n"),
    ("U+2028 between statements", "x = 1\u2028payload = 2"),
)

# The reading layer is exercised through a real file, because a coding cookie
# or a BOM only exists on disk.
READ_LAYER_SAMPLES = (
    # The expectation is the full per-carrier list: a coding cookie is itself
    # a comment, so that file has two carriers and only the second asserts.
    ("utf-8 BOM", "\ufeff# %s\nx = 1\n" % MARK, [HIT]),
    ("coding cookie", "# -*- coding: utf-8 -*-\n# %s\nx = 1\n" % MARK, [[], HIT]),
)


def form_matrix_check():
    """Check carriers and violations against written-down expectations."""
    failures = []
    for label, source, want_carriers, want_violations in PROSE_FORM_MATRIX:
        try:
            got_carriers = list(prose_carriers("probe.py", source))
        except UnparsablePython as exc:
            print("  %-34s UNEXPECTED UnparsablePython: %s" % (label, exc))
            failures.append((label, "carriers", want_carriers, "UnparsablePython"))
            continue
        got_violations = [line_violations(f) for _, f in got_carriers]
        ok = (got_carriers == list(want_carriers)
              and got_violations == list(want_violations))
        print("  %-34s carriers=%-2d violations=%-2d %s"
              % (label, len(got_carriers), sum(len(v) for v in got_violations),
                 "ok" if ok else "MISMATCH"))
        if not ok:
            failures.append((label, got_carriers, got_violations))
    for label, source in UNPARSABLE_SAMPLES:
        try:
            list(prose_carriers("broken.py", source))
        except UnparsablePython:
            print("  %-34s raises UnparsablePython (fail closed)" % label)
        else:
            print("  %-34s DID NOT FAIL CLOSED" % label)
            failures.append((label, "UnparsablePython", "no exception"))
    for label, source, want in READ_LAYER_SAMPLES:
        directory = tempfile.mkdtemp()
        try:
            probe = os.path.join(directory, "probe.py")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write(source)
            carriers = list(prose_carriers(probe, read_source(probe)))
            got = [line_violations(f) for _, f in carriers]
            ok = got == list(want)
            print("  %-34s read-layer violations=%-2d %s"
                  % (label, sum(len(v) for v in got), "ok" if ok else "MISMATCH"))
            if not ok:
                failures.append((label, list(want), got))
        finally:
            shutil.rmtree(directory)
    return failures


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
    # R28: a trailing comment. The hand-written scanner only saw whole-line
    # comments, so this shape rode through the real scan path unseen while the
    # SSOT claimed '.py comments' were covered.
    "x = 1  # 当前定向用例为 9999",
)


def self_test():
    """Inject every variant into every scanned file -- a true cross product.

    The previous version rotated one variant per file and exercised the full
    set on the first file only, while printing "every file and every notation".
    A check shown to fail on one file in one notation has only been shown to
    fail there. Everything goes through the real scan path; nothing is written.
    """
    print("form matrix (.py syntactic positions, expectations written down):")
    form_failures = form_matrix_check()
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
            # A line appended at EOF is a trailing expression, not a
            # docstring -- the old scanner counted one as prose, which was a
            # false positive in the other direction. Only comments are prose
            # wherever they land; real docstrings are covered by the form
            # matrix above, which places them where the grammar puts them.
            already_python = variant.lstrip().startswith("#") or "  # " in variant
            injected = variant if (not path.endswith(".py") or already_python) \
                else "# " + variant
            dirty = scan(injections={path: injected})
            caught = len(dirty) > len(baseline)
            print("  %-26s variant=%-30s caught=%s" % (rel, variant[:30], caught))
            if not caught:
                misses.append((rel, variant))
    if form_failures:
        print("SELF-TEST FAILED: form matrix mismatches: %r" % (form_failures,))
        return 1
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
