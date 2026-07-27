# 边界用例扫描表 — 门禁证据载体规则

由 `carrier_sweep.py` 生成，与该脚本同源；脚本是本表的可复现载体。

用例总数 **52**，失败 **0**。输入字节以 Python `repr` 转义呈现，不含任何字面控制字符。


## A 组 — 流程 §2.3 声明的对抗字节域（逐项对应）

| 用例 | 输入字节（转义） | 期望分支 | 实际分支 | 状态 |
| --- | --- | --- | --- | --- |
| CRLF line ending | `b'OK\r\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| CRLF only | `b'\r\n'` | `(b) no non-empty line -> bytes+sha256` | `(b) no non-empty line -> bytes+sha256` | PASS |
| no trailing newline | `b'OK'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| empty stream | `b''` | `(a) empty` | `(a) empty` | PASS |
| non-ASCII CJK | `b'\xe5\xa5\x91\xe7\xba\xa6\xe6\x9c\x89\xe6\x95\x88\xe3\x8...'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| non-ASCII emoji | `b'done \xf0\x9f\x98\x80\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| C0 control NUL | `b'\x00\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| C0 control BEL | `b'\x07\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| DEL U+007F | `b'\x7f\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| NEL U+0085 | `b'A\xc2\x85B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| U+2028 line sep | `b'A\xe2\x80\xa8B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| U+2029 para sep | `b'A\xe2\x80\xa9B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| surrogate bytes D800 | `b'\xed\xa0\x80'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| surrogate bytes DFFF | `b'\xed\xbf\xbf'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| literal escape vs real char | `b'line\\nnot-a-newline\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| literal <empty> collision | `b'<empty>\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |

## B 组 — 规则自身的不可呈现码点集（含集合外的边界邻居）

| 用例 | 输入字节（转义） | 期望分支 | 实际分支 | 状态 |
| --- | --- | --- | --- | --- |
| C1 control U+0080 | `b'A\xc2\x80B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| C1 control U+009F | `b'A\xc2\x9fB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| LRM U+200E | `b'A\xe2\x80\x8eB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| RLM U+200F | `b'A\xe2\x80\x8fB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| LRE U+202A | `b'A\xe2\x80\xaaB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| RLO U+202E | `b'A\xe2\x80\xaeB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| LRI U+2066 | `b'A\xe2\x81\xa6B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| FSI U+2068 | `b'A\xe2\x81\xa8B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| PDI U+2069 | `b'A\xe2\x81\xa9B\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| BOM U+FEFF | `b'\xef\xbb\xbfOK\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| boundary U+00A0 renderable | `b'A\xc2\xa0B\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| boundary U+2027 renderable | `b'A\xe2\x80\xa7B\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| boundary U+202F renderable | `b'A\xe2\x80\xafB\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| boundary U+2065 renderable | `b'A\xe2\x81\xa5B\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| boundary U+206A renderable | `b'A\xe2\x81\xaaB\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |

## C 组 — 「行」的字节级定义

| 用例 | 输入字节（转义） | 期望分支 | 实际分支 | 状态 |
| --- | --- | --- | --- | --- |
| lone LF | `b'\n'` | `(b) no non-empty line -> bytes+sha256` | `(b) no non-empty line -> bytes+sha256` | PASS |
| lone CR | `b'\r'` | `(b) no non-empty line -> bytes+sha256` | `(b) no non-empty line -> bytes+sha256` | PASS |
| several blank lines | `b'\n\n\n'` | `(b) no non-empty line -> bytes+sha256` | `(b) no non-empty line -> bytes+sha256` | PASS |
| several CRLF blanks | `b'\r\n\r\n'` | `(b) no non-empty line -> bytes+sha256` | `(b) no non-empty line -> bytes+sha256` | PASS |
| single space line | `b' \n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| spaces no newline | `b'   '` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| trailing blanks after text | `b'OK\n\n\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| trailing CRLF blanks after text | `b'OK\r\n\r\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| CR inside line not trailing | `b'A\rB\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| only one trailing CR stripped | `b'OK\r\r\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |
| lone CR line | `b'\r\r\n'` | `(b) unrenderable code point -> bytes+sha256` | `(b) unrenderable code point -> bytes+sha256` | PASS |

## D 组 — UTF-8 可解码性边界

| 用例 | 输入字节（转义） | 期望分支 | 实际分支 | 状态 |
| --- | --- | --- | --- | --- |
| undecodable tail byte | `b'OK\n\xff'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| undecodable no non-empty line | `b'\n\xff'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| truncated multi-byte seq | `b'\xe5\xa5'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| overlong encoding of slash | `b'\xc0\xaf'` | `(c) not UTF-8 decodable -> bytes+sha256` | `(c) not UTF-8 decodable -> bytes+sha256` | PASS |
| two-byte boundary U+07FF | `b'\xdf\xbf\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| four-byte astral plane | `b'\xf0\x9f\x98\x80\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |

## E 组 — 本 Change Record 实际记录的门禁输出回放

| 用例 | 输入字节（转义） | 期望分支 | 实际分支 | 状态 |
| --- | --- | --- | --- | --- |
| gate 1/2/6 stdout | `b'Harness contract is valid.\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| gate 3 stdout two lines | `b'[ADAPT_SKIPPED_TEMPLATE] .: origin is null\nadapt: ok\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| gate 4 stderr tail | `b'Ran 175 tests in 12.316s\n\nOK (skipped=2)\n'` | `(b) last-non-empty-line verbatim` | `(b) last-non-empty-line verbatim` | PASS |
| gate 5 both streams | `b''` | `(a) empty` | `(a) empty` | PASS |

## 结论

52 个定向用例的实际分支与期望分支**逐条一致**，失败 0。
定向用例的作用是验证**判据本身**（输入是否被放进正确的分支）；随机模糊测试只能证明没有输入逃出划分，无法证明划分正确——两者不可互相替代。见 `run-manifest.md`。
