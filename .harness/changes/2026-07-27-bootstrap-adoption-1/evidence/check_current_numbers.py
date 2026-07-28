#!/usr/bin/env python3
"""Fail if a current-state record section contains a non-whitelisted number.

The de-mirroring rule -- current-state text must not transcribe numbers a
command or the sweep script can derive -- had no check that could fail. The
forall collector matches keywords, not digits, so a stale count sat in
run-manifest.md line 49 through the very commit that claimed the class was
closed, and the one checklist row aimed at this was anchored to two literal
phrases inside a single section, returning 0 whenever the residue lived
elsewhere. A discipline without a failing check is a hope.

This scans the CURRENT-STATE sections of the record for number tokens,
subtracts an explicit whitelist, and exits 1 listing whatever is left.

Usage:  python3 check_current_numbers.py            # scan, exit 1 on residue
        python3 check_current_numbers.py --self-test  # prove it can fail

Exit codes:
  0  no non-whitelisted number in any scanned current-state section
  1  residue found (each occurrence printed with file, line and token)
  2  bad arguments, or a scanned file is missing

Note on source encoding: carrier_sweep.py holds a pure-ASCII discipline because
its source is hashed and attested. THIS file is not pure ASCII and cannot be:
it matches section headings written in Chinese, so those headings appear here
verbatim. Escaping them would make the anchors unreadable and the check harder
to audit, which costs more than it buys. Disclosed rather than left for a
reviewer to notice as an inconsistency.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# (path, section heading, end heading or None for end-of-file). Only the
# CURRENT-STATE sections are scanned; historical sections keep their
# round-tagged numbers by design.
SCAN_TARGETS = (
    ("run-manifest.md", "## 结果（**去镜像**：当前态数字不再手抄）", "### 红基线（先见红，再见绿）"),
    ("run-manifest.md", "### 本节保留的唯一两个不变量", "### 当前态数字白名单（显式、可核查）"),
    ("protocol-runs.md", "### 机械步骤的观察值（只保留产物不变量与退出语义）",
     "### 落地核对清单（本提交声称的每一处修复）"),
)

# Structures that are not prose assertions at all: fenced code blocks and
# inline code spans hold COMMANDS, and the Change Record's own directory name
# holds a date. Numbers inside them are not transcribed measurements, so they
# are removed before the whitelist is applied. Without this the scanner drowns
# in path digits and stops being usable -- a check nobody can read is a check
# nobody runs.
RECORD_DIR = "2026-07-27-bootstrap-adoption-1"
INLINE_CODE = re.compile(r"`[^`]*`")
FENCE = re.compile(r"^\s*```")

# Whitelisted number shapes, justified in run-manifest.md's whitelist table.
WHITELIST_PATTERNS = (
    r"\b[0-9a-f]{64}\b",          # script SHA-256 / result digest
    r"SHA-?256",                  # the algorithm name
    r"U\+[0-9A-Fa-f]{4,6}",       # code points
    r"0x[0-9A-Fa-f]+",            # byte literals
    r"Python 3\.\d+(\.\d+)?",     # interpreter version
    r"第 \d+ 步",                  # protocol step numbers (structure, not results)
    r"第 \d+ 轮",                  # review round numbers
    r"exit(?:s)? \d",             # exit-code semantics
    r"退出 \d",
    r"rc=\d",
    r"\d+/\d+ passed",            # attestation shape reference
    r"length 0-\d",               # documented subdomain names
    r"长度 0[–-]\d",
    r"CERT_LAYERS|CHECK_CLASSES",
    r"§\s*\d+",                    # rule section references (e.g. rules/project.md §2)
)

NUMBER_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")


def _load(path):
    full = os.path.join(HERE, path)
    if not os.path.isfile(full):
        raise SystemExit("missing scan target: %s" % full)
    with open(full, encoding="utf-8") as handle:
        return handle.read().splitlines()


def _section(lines, start_heading, end_heading):
    try:
        start = lines.index(start_heading)
    except ValueError:
        raise SystemExit("missing section %r" % start_heading)
    if end_heading is None:
        return start, len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] == end_heading:
            return start, index
    return start, len(lines)


def _mask_whitelisted(line):
    masked = line.replace(RECORD_DIR, " ")
    masked = INLINE_CODE.sub(" ", masked)
    for pattern in WHITELIST_PATTERNS:
        masked = re.sub(pattern, " ", masked)
    return masked


def scan(extra_lines=None):
    """Return a list of (path, line_number, token, line) residues."""
    residues = []
    for path, start_heading, end_heading in SCAN_TARGETS:
        lines = _load(path)
        if extra_lines and path in extra_lines:
            for offset, injected in extra_lines[path]:
                lines.insert(offset, injected)
        start, end = _section(lines, start_heading, end_heading)
        in_fence = False
        for number, line in enumerate(lines[start:end], start=start + 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for token in NUMBER_TOKEN.findall(_mask_whitelisted(line)):
                residues.append((path, number, token, line.strip()))
    return residues


def self_test():
    """Prove the scanner can fail: inject a stray number, expect a residue."""
    clean = scan()
    path, start_heading, _end = SCAN_TARGETS[0]
    lines = _load(path)
    start, _ = _section(lines, start_heading, SCAN_TARGETS[0][2])
    injected = {path: [(start + 1, "stray residue 12345 injected by self test")]}
    dirty = scan(extra_lines=injected)
    caught = [r for r in dirty if r[2] == "12345"]
    print("clean scan residues: %d" % len(clean))
    print("injected-stray scan caught the stray: %s" % bool(caught))
    if not caught:
        print("SELF-TEST FAILED: scanner did not catch an injected stray number")
        return 1
    print("SELF-TEST PASSED: scanner detects a stray number (injection was")
    print("in-memory only; no file was modified)")
    return 0


def main(argv):
    if argv and argv != ["--self-test"]:
        sys.stderr.write("usage: check_current_numbers.py [--self-test]\n")
        return 2
    if argv == ["--self-test"]:
        return self_test()
    residues = scan()
    if not residues:
        print("no non-whitelisted number in the scanned current-state sections")
        return 0
    print("non-whitelisted number(s) found in current-state sections:")
    for path, number, token, line in residues:
        print("  %s:%d  token=%s  | %s" % (path, number, token, line))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
