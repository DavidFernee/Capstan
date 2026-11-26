# CWE atlas: red-teaming Capstan

For each code-level weakness in the CWE list, the atlas holds the most natural attempt to write it
in Capstan, plus deliberate workarounds (laundering untrusted input, hiding credentials under
innocuous names, using the wrong escaper). Every verdict is an executable test in
`tests/cwe/atlas.py`, re-checked by the test suite against the current compiler.

The rest of the CWE list (hardware design, organisational and process weaknesses, and
categories and views) is outside scope: it describes things program code cannot express.
Attempts are written from the CWE descriptions; this atlas is not an official MITRE mapping.

**255 weaknesses, 301 attempts.** Counting each weakness once, by its weakest attempt:

| Outcome | Weaknesses |
|---|---|
| Prevented: rejected at compile time | 81 |
| Prevented: stopped safely at run time | 25 |
| Prevented: attempt compiles but has no effect | 16 |
| Inexpressible: the construct does not exist | 71 |
| Possible only through an audited escape hatch | 2 |
| Logic or design decision: beyond any language | 22 |
| **Gap: can be written** | 5 |
| Not applicable (yet) | 33 |

## Gaps: weaknesses that can still be written

These are honest limits of the current version. Each is a test, so when a future version
closes a gap the test fails and the entry is reclassified.

| CWE | Weakness | What was written | Why it compiles, and the plan |
|---|---|---|---|
| [116](https://cwe.mitre.org/data/definitions/116.html) | Improper encoding: JSON-escaped fragment written into a CSV file | `'int main() { string cell = escape_json(taint("=cmd\|\' /C calc\'!A0")); bool ok = writ...` | escape_json() returns an untyped string fragment for JSON serializers; typed JSON fragments and sinks are tracked in #250. |
| [798](https://cwe.mitre.org/data/definitions/798.html) | Hard-coded password-like literal under an innocuous name | `int main() { string cfg = "Winter2026!"; sql_query("UPDATE settings SET v = ?", cfg); r...` | A short password-like literal under an ordinary name is indistinguishable from other text. |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password in an innocuously named variable) | `int main() { if (let x = read_line(65536)) { string stored = hash(x); } return 0; }` | Detection is name-based. Typing passwords as Secret at input would make this a type error (roadmap). |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password passed through a method call) | `int main() { if (let password = read_line(65536)) { string stored = hash(password.slice...` | The password-name heuristic stops at N_METHOD nodes, so wrapping a password in a string method may evade the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted. |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password passed through a helper call) | `Tainted identity(Tainted value) { return value; }` | The password-name heuristic stops at N_CALL nodes, so a helper that preserves Tainted can hide a password-like variable from the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted. |
| [862](https://cwe.mitre.org/data/definitions/862.html) | Missing authorization (data type not declared sensitive) | `string read_any(Record r) { return r.body; }` | Protection starts when the type is declared sensitive. It is declared once per type, not per function, but it can still be forgotten. |
| [306](https://cwe.mitre.org/data/definitions/306.html) | Missing authentication for critical function | `void delete_all_records() { }` | An operation that touches no sensitive data value cannot be recognised as critical; it must be declared protected. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (Html assembled across separate statements) | `int main() { if (let t = read_line(65536)) { Html v = escape_html(t); Html page = "<img...` | The context of escaped text is checked only where escape_html() is called in the same expression as the literal HTML around it. Contextual HTML templates, which track context across statements, are on the roadmap. |

## Beyond any language: logic and design decisions

These weaknesses can be written in Capstan because they are not mistakes in *how* code is written but
in *what* it was meant to do: a wrong formula, a missing business rule, a policy that is consistent but
wrong. No compiler can tell them from intended behaviour. Each attempt still compiles here, as a test.

| CWE | Weakness | Why | 
|---|---|---|
| [682](https://cwe.mitre.org/data/definitions/682.html) | Incorrect calculation | A wrong formula is a specification error. Overflow from it is still caught. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Laundering untrusted bytes through control flow | Building output by branching on each input byte is exactly how a validator is written (the compiler's own lexer works this way). Which branches are safe is the programmer's decision. |
| [203](https://cwe.mitre.org/data/definitions/203.html) | Observable discrepancy (e.g. username enumeration) | What a response reveals is a design decision. |
| [863](https://cwe.mitre.org/data/definitions/863.html) | Incorrect authorization | A consistent but wrong policy is a requirements error. Denial tests, policy assertions (roadmap) and review are the defences. |
| [287](https://cwe.mitre.org/data/definitions/287.html) | Improper authentication | Authentication logic is a design decision; a session and authentication framework is on the roadmap. |
| [307](https://cwe.mitre.org/data/definitions/307.html) | Improper restriction of excessive authentication attempts | Rate limiting is a design decision (the slow password hash already limits guessing speed). |
| [521](https://cwe.mitre.org/data/definitions/521.html) | Weak password requirements | Password rules are policy. |
| [620](https://cwe.mitre.org/data/definitions/620.html) | Unverified password change | Workflow design. |
| [266](https://cwe.mitre.org/data/definitions/266.html) | Incorrect privilege assignment | Default roles are policy. |
| [834](https://cwe.mitre.org/data/definitions/834.html) | Excessive iteration | Loop bounds are a design decision. |
| [835](https://cwe.mitre.org/data/definitions/835.html) | Loop with unreachable exit condition (infinite loop) | Whether a loop terminates is undecidable in general (the halting problem). |
| [407](https://cwe.mitre.org/data/definitions/407.html) | Inefficient algorithmic complexity | Algorithm choice is a design decision. |
| [480](https://cwe.mitre.org/data/definitions/480.html) | Use of incorrect operator | Which operator was meant is the programmer's intent. |
| [697](https://cwe.mitre.org/data/definitions/697.html) | Incorrect comparison | Comparison logic is intent. |
| [1023](https://cwe.mitre.org/data/definitions/1023.html) | Incomplete comparison with missing factors | As CWE-697. |
| [670](https://cwe.mitre.org/data/definitions/670.html) | Always-incorrect control flow implementation | Control-flow intent. |
| [912](https://cwe.mitre.org/data/definitions/912.html) | Hidden functionality | A deliberate backdoor written as ordinary logic is indistinguishable from intended logic. Code review and Capstan Review (AI) are the defences. |
| [1284](https://cwe.mitre.org/data/definitions/1284.html) | Improper validation of specified quantity in input | Which range is valid is business knowledge; validate_range(t, min, max) makes enforcing it one call. Overflow is still caught. |
| [178](https://cwe.mitre.org/data/definitions/178.html) | Improper handling of case sensitivity | Whether 'Admin' and 'admin' are the same name is a design decision. |
| [841](https://cwe.mitre.org/data/definitions/841.html) | Improper enforcement of behavioral workflow | Workflow order is a design decision; typestate checking is a possible future feature. |
| [837](https://cwe.mitre.org/data/definitions/837.html) | Improper enforcement of a single, unique action | Business rule. |
| [799](https://cwe.mitre.org/data/definitions/799.html) | Improper control of interaction frequency | Rate limiting is a design decision. |

## Full atlas

| CWE | Weakness | Outcome | Detail |
|---|---|---|---|
| [15](https://cwe.mitre.org/data/definitions/15.html) | External control of system or configuration setting | Inexpressible: the construct does not exist |  |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Laundering untrusted bytes through control flow | Logic or design decision: beyond any language | Building output by branching on each input byte is exactly how a validator is written (the compiler's own lexer works this way). Which branches are safe is the programmer's decision. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Laundering untrusted bytes through a bit mask | Prevented: rejected at compile time | `CWE-20`. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Improper input validation | Prevented: rejected at compile time | `CWE-20`. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Laundering untrusted bytes through a list | Prevented: rejected at compile time | `CWE-20`. Collections and structs that hold bytes of untrusted input are tracked too. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Laundering untrusted bytes through a struct field | Prevented: rejected at compile time | `CWE-20`. |
| [20](https://cwe.mitre.org/data/definitions/20.html) | Improper input validation (laundering through a lookup table) | Prevented: rejected at compile time | `CWE-20`. Bytes of untrusted input are tainted integers: selecting trusted text with them (list index, slice, map key) is rejected. |
| [22](https://cwe.mitre.org/data/definitions/22.html) | Path traversal (via an audited trust()) | Possible only through an audited escape hatch | Possible only through trust(), which needs a written justification and is reported in every build. validate_path() is the safe route. |
| [22](https://cwe.mitre.org/data/definitions/22.html) | Path traversal (attempt through validate_path) | Prevented: attempt compiles but has no effect |  |
| [22](https://cwe.mitre.org/data/definitions/22.html) | Path traversal | Prevented: rejected at compile time | `CWE-20`. |
| [23](https://cwe.mitre.org/data/definitions/23.html) | Relative path traversal | Prevented: rejected at compile time | `CWE-20`. |
| [36](https://cwe.mitre.org/data/definitions/36.html) | Absolute path traversal | Prevented: rejected at compile time | `CWE-20`. |
| [59](https://cwe.mitre.org/data/definitions/59.html) | Improper link resolution before file access (link following) | Not applicable (yet) | File access follows symbolic links; capability-based file access (v0.6) will address it. |
| [73](https://cwe.mitre.org/data/definitions/73.html) | External control of file name or path | Prevented: rejected at compile time | `CWE-20`. |
| [74](https://cwe.mitre.org/data/definitions/74.html) | Injection (generic) | Prevented: rejected at compile time | `CWE-20`. |
| [77](https://cwe.mitre.org/data/definitions/77.html) | Command injection | Prevented: rejected at compile time | `CWE-78`. |
| [78](https://cwe.mitre.org/data/definitions/78.html) | OS command injection (via run with untrusted argument) | Prevented: attempt compiles but has no effect | No shell exists: the whole value stays one argument. |
| [78](https://cwe.mitre.org/data/definitions/78.html) | OS command injection | Prevented: rejected at compile time | `CWE-78`. |
| [78](https://cwe.mitre.org/data/definitions/78.html) | OS command injection (through a shell named as the program) | Prevented: rejected at compile time | `CWE-78`. Shells, interpreters and launchers (sh, env, python, xargs and others) take only literal arguments. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (Html assembled across separate statements) | **Gap: can be written** | The context of escaped text is checked only where escape_html() is called in the same expression as the literal HTML around it. Contextual HTML templates, which track context across statements, are on the roadmap. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting | Prevented: rejected at compile time | `CWE-20`. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (via the wrong escaper) | Prevented: rejected at compile time | `CWE-116`. escape_log() returns LogText and escape_html() returns Html; neither can pass as a plain string. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (via byte-by-byte laundering) | Prevented: rejected at compile time | `CWE-20`. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (laundering through a helper function) | Prevented: rejected at compile time | `CWE-20`. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (escaped text in an unquoted attribute) | Prevented: rejected at compile time | `CWE-79`. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (escaped text in a URL attribute) | Prevented: rejected at compile time | `CWE-79`. |
| [79](https://cwe.mitre.org/data/definitions/79.html) | Cross-site scripting (escaped text in a script block) | Prevented: rejected at compile time | `CWE-79`. |
| [80](https://cwe.mitre.org/data/definitions/80.html) | Basic XSS (improper neutralization of script tags) | Prevented: attempt compiles but has no effect |  |
| [88](https://cwe.mitre.org/data/definitions/88.html) | Argument injection | Prevented: rejected at compile time | `CWE-88`. |
| [88](https://cwe.mitre.org/data/definitions/88.html) | Argument injection (computed argument read as an option) | Prevented: rejected at compile time | `CWE-88`. Every computed argument must follow a literal "--"; validate_path() also refuses a leading '-'. |
| [89](https://cwe.mitre.org/data/definitions/89.html) | SQL injection (attempt through a bound parameter) | Prevented: attempt compiles but has no effect |  |
| [89](https://cwe.mitre.org/data/definitions/89.html) | SQL injection | Prevented: rejected at compile time | `CWE-89`. |
| [89](https://cwe.mitre.org/data/definitions/89.html) | SQL injection (query held in a variable) | Prevented: rejected at compile time | `CWE-89`. |
| [90](https://cwe.mitre.org/data/definitions/90.html) | LDAP injection | Not applicable (yet) | No LDAP facility. |
| [91](https://cwe.mitre.org/data/definitions/91.html) | XML injection | Inexpressible: the construct does not exist |  |
| [93](https://cwe.mitre.org/data/definitions/93.html) | CRLF injection | Prevented: rejected at compile time | `CWE-117`. |
| [94](https://cwe.mitre.org/data/definitions/94.html) | Code injection | Inexpressible: the construct does not exist |  |
| [95](https://cwe.mitre.org/data/definitions/95.html) | Eval injection | Prevented: rejected at compile time | `CWE-95`. |
| [96](https://cwe.mitre.org/data/definitions/96.html) | Static code injection | Inexpressible: the construct does not exist |  |
| [97](https://cwe.mitre.org/data/definitions/97.html) | Server-side includes injection | Not applicable (yet) | No web server facility. |
| [98](https://cwe.mitre.org/data/definitions/98.html) | PHP remote file inclusion | Inexpressible: the construct does not exist |  |
| [99](https://cwe.mitre.org/data/definitions/99.html) | Resource injection | Prevented: rejected at compile time | `CWE-20`. |
| [113](https://cwe.mitre.org/data/definitions/113.html) | HTTP response splitting | Not applicable (yet) | No HTTP facility yet; header output would follow the CWE-93 rule. |
| [114](https://cwe.mitre.org/data/definitions/114.html) | Process control | Inexpressible: the construct does not exist |  |

| [116](https://cwe.mitre.org/data/definitions/116.html) | Improper encoding: JSON-escaped fragment written into a CSV file | **Gap: can be written** | escape_json() returns an untyped string fragment for JSON serializers; typed JSON fragments and sinks are tracked in #250. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | Improper encoding or escaping of output | Prevented: rejected at compile time | `CWE-116`. Escaped text is typed by its context (Html, LogText) and cannot pass as a plain string. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | HTML context passed to CSV sink | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | CSV context passed to HTML sink | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | CSV context passed to terminal output | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | Plain string passed to CSV sink | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | HTML context passed to format-agnostic file sink | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | Mixed CSV and HTML contexts concatenated | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | CSV context erased by assignment to string | Prevented: rejected at compile time | `CWE-116`. |
| [116](https://cwe.mitre.org/data/definitions/116.html) | Tainted value concatenated into CSV context | Prevented: rejected at compile time | `CWE-116`. |
| [117](https://cwe.mitre.org/data/definitions/117.html) | Log injection (attempt after escape_log) | Prevented: attempt compiles but has no effect |  |
| [117](https://cwe.mitre.org/data/definitions/117.html) | Improper output neutralization for logs | Prevented: rejected at compile time | `CWE-117`. |
| [119](https://cwe.mitre.org/data/definitions/119.html) | Improper restriction of operations within memory buffer bounds | Prevented: stopped safely at run time | `CWE-787`. |
| [120](https://cwe.mitre.org/data/definitions/120.html) | Buffer copy without checking size of input (classic overflow) | Prevented: rejected at compile time | `CWE-120`. |
| [121](https://cwe.mitre.org/data/definitions/121.html) | Stack-based buffer overflow | Inexpressible: the construct does not exist |  |
| [122](https://cwe.mitre.org/data/definitions/122.html) | Heap-based buffer overflow | Prevented: stopped safely at run time | `CWE-787`. |
| [123](https://cwe.mitre.org/data/definitions/123.html) | Write-what-where condition | Inexpressible: the construct does not exist |  |
| [124](https://cwe.mitre.org/data/definitions/124.html) | Buffer underwrite | Prevented: stopped safely at run time | `CWE-787`. |
| [125](https://cwe.mitre.org/data/definitions/125.html) | Out-of-bounds read | Prevented: stopped safely at run time | `CWE-125`. |
| [126](https://cwe.mitre.org/data/definitions/126.html) | Buffer over-read | Prevented: stopped safely at run time | `CWE-125`. |
| [127](https://cwe.mitre.org/data/definitions/127.html) | Buffer under-read | Prevented: stopped safely at run time | `CWE-125`. |
| [128](https://cwe.mitre.org/data/definitions/128.html) | Wrap-around error | Prevented: stopped safely at run time | `CWE-190`. |
| [129](https://cwe.mitre.org/data/definitions/129.html) | Improper validation of array index | Prevented: stopped safely at run time | `CWE-125`. |
| [131](https://cwe.mitre.org/data/definitions/131.html) | Incorrect calculation of buffer size | Inexpressible: the construct does not exist |  |
| [134](https://cwe.mitre.org/data/definitions/134.html) | Use of externally-controlled format string | Prevented: rejected at compile time | `CWE-134`. |
| [170](https://cwe.mitre.org/data/definitions/170.html) | Improper null termination | Prevented: attempt compiles but has no effect | Strings carry their length; an embedded zero byte does not truncate them. |
| [172](https://cwe.mitre.org/data/definitions/172.html) | Encoding error | Not applicable (yet) | Strings are bytes; encodings are not interpreted. |
| [176](https://cwe.mitre.org/data/definitions/176.html) | Improper handling of Unicode encoding | Prevented: attempt compiles but has no effect |  |
| [178](https://cwe.mitre.org/data/definitions/178.html) | Improper handling of case sensitivity | Logic or design decision: beyond any language | Whether 'Admin' and 'admin' are the same name is a design decision. |
| [180](https://cwe.mitre.org/data/definitions/180.html) | Incorrect behaviour order: validate before canonicalize | Not applicable (yet) | No canonicalisation API. |
| [185](https://cwe.mitre.org/data/definitions/185.html) | Incorrect regular expression | Inexpressible: the construct does not exist |  |
| [188](https://cwe.mitre.org/data/definitions/188.html) | Reliance on data/memory layout | Inexpressible: the construct does not exist |  |
| [190](https://cwe.mitre.org/data/definitions/190.html) | Integer overflow or wraparound | Prevented: stopped safely at run time | `CWE-190`. |
| [190](https://cwe.mitre.org/data/definitions/190.html) | Integer overflow (bits shifted out by <<) | Prevented: stopped safely at run time | `CWE-190`. << is checked like multiplication; wrapping_shl() is the explicit modular form. |
| [191](https://cwe.mitre.org/data/definitions/191.html) | Integer underflow | Prevented: stopped safely at run time | `CWE-191`. |
| [192](https://cwe.mitre.org/data/definitions/192.html) | Integer coercion error | Inexpressible: the construct does not exist |  |
| [194](https://cwe.mitre.org/data/definitions/194.html) | Unexpected sign extension | Inexpressible: the construct does not exist |  |
| [195](https://cwe.mitre.org/data/definitions/195.html) | Signed to unsigned conversion error | Inexpressible: the construct does not exist |  |
| [196](https://cwe.mitre.org/data/definitions/196.html) | Unsigned to signed conversion error | Inexpressible: the construct does not exist |  |
| [197](https://cwe.mitre.org/data/definitions/197.html) | Numeric truncation error | Inexpressible: the construct does not exist |  |
| [200](https://cwe.mitre.org/data/definitions/200.html) | Exposure of sensitive information | Prevented: rejected at compile time | `CWE-200`. |
| [203](https://cwe.mitre.org/data/definitions/203.html) | Observable discrepancy (e.g. username enumeration) | Logic or design decision: beyond any language | What a response reveals is a design decision. |
| [208](https://cwe.mitre.org/data/definitions/208.html) | Observable timing discrepancy | Prevented: rejected at compile time | `CWE-208`. |
| [208](https://cwe.mitre.org/data/definitions/208.html) | Timing discrepancy (token compared as a plain string) | Prevented: rejected at compile time | `CWE-208`. |
| [209](https://cwe.mitre.org/data/definitions/209.html) | Error message containing sensitive information | Prevented: rejected at compile time | `CWE-200`. |
| [210](https://cwe.mitre.org/data/definitions/210.html) | Self-generated error message with sensitive information | Prevented: attempt compiles but has no effect | Runtime stops report the file, line and check, never data values. The test expects the stop's stderr to be data-free. |
| [214](https://cwe.mitre.org/data/definitions/214.html) | Invocation of process using visible sensitive information | Prevented: attempt compiles but has no effect | Secrets cannot be passed to run(); a separate test proves that (CWE-532). |
| [214](https://cwe.mitre.org/data/definitions/214.html) | Sensitive information on a command line | Prevented: rejected at compile time | `CWE-532`. |
| [215](https://cwe.mitre.org/data/definitions/215.html) | Insertion of sensitive information into debugging code | Prevented: rejected at compile time | `CWE-532`. |
| [226](https://cwe.mitre.org/data/definitions/226.html) | Sensitive information in resource not removed before reuse | Prevented: attempt compiles but has no effect | Memory is zeroed when the collector reuses it and when it is allocated. Freed but not yet reused memory is not wiped; see CWE-244. |
| [242](https://cwe.mitre.org/data/definitions/242.html) | Use of inherently dangerous function | Prevented: rejected at compile time | `CWE-120`. |
| [244](https://cwe.mitre.org/data/definitions/244.html) | Improper clearing of heap memory before release (heap inspection) | Prevented: attempt compiles but has no effect | Secrets live in their own memory class and are zeroed when collected; tests/unit proves it. Password-hashing scratch buffers are wiped too. |
| [248](https://cwe.mitre.org/data/definitions/248.html) | Uncaught exception | Inexpressible: the construct does not exist |  |
| [250](https://cwe.mitre.org/data/definitions/250.html) | Execution with unnecessary privileges | Not applicable (yet) | Deployment concern; capability-based I/O (v0.6) limits what code can touch. |
| [252](https://cwe.mitre.org/data/definitions/252.html) | Unchecked return value | Prevented: rejected at compile time | `CWE-252`. Warning; an error with --strict (tested that way). |
| [253](https://cwe.mitre.org/data/definitions/253.html) | Incorrect check of function return value | Prevented: rejected at compile time | `type mismatch`. |
| [256](https://cwe.mitre.org/data/definitions/256.html) | Plaintext storage of a password | Prevented: rejected at compile time | `CWE-20`. |
| [257](https://cwe.mitre.org/data/definitions/257.html) | Storing passwords in a recoverable format | Prevented: rejected at compile time | `CWE-256`. |
| [259](https://cwe.mitre.org/data/definitions/259.html) | Use of hard-coded password | Prevented: rejected at compile time | `CWE-798`. |
| [266](https://cwe.mitre.org/data/definitions/266.html) | Incorrect privilege assignment | Logic or design decision: beyond any language | Default roles are policy. |
| [269](https://cwe.mitre.org/data/definitions/269.html) | Improper privilege management | Prevented: rejected at compile time | `CWE-862`. Changing a sensitive record also needs a grant. |
| [276](https://cwe.mitre.org/data/definitions/276.html) | Incorrect default permissions | Not applicable (yet) | Files are created with the process umask; a file API with explicit permissions is planned with capabilities. |
| [284](https://cwe.mitre.org/data/definitions/284.html) | Improper access control | Prevented: rejected at compile time | `CWE-862`. |
| [285](https://cwe.mitre.org/data/definitions/285.html) | Improper authorization | Prevented: rejected at compile time | `CWE-862`. |
| [287](https://cwe.mitre.org/data/definitions/287.html) | Improper authentication | Logic or design decision: beyond any language | Authentication logic is a design decision; a session and authentication framework is on the roadmap. |
| [288](https://cwe.mitre.org/data/definitions/288.html) | Authentication bypass using an alternate path | Prevented: rejected at compile time | `CWE-862`. Every path to sensitive data needs a grant, so a second unprotected path does not compile. |
| [290](https://cwe.mitre.org/data/definitions/290.html) | Authentication bypass by spoofing | Not applicable (yet) | Network concern. |
| [294](https://cwe.mitre.org/data/definitions/294.html) | Authentication bypass by capture-replay | Not applicable (yet) | Network concern. |
| [295](https://cwe.mitre.org/data/definitions/295.html) | Improper certificate validation | Inexpressible: the construct does not exist |  |
| [297](https://cwe.mitre.org/data/definitions/297.html) | Improper validation of certificate with host mismatch | Inexpressible: the construct does not exist |  |
| [302](https://cwe.mitre.org/data/definitions/302.html) | Authentication bypass by assumed-immutable data | Prevented: rejected at compile time | `CWE-807`. |
| [306](https://cwe.mitre.org/data/definitions/306.html) | Missing authentication for critical function | **Gap: can be written** | An operation that touches no sensitive data value cannot be recognised as critical; it must be declared protected. |
| [307](https://cwe.mitre.org/data/definitions/307.html) | Improper restriction of excessive authentication attempts | Logic or design decision: beyond any language | Rate limiting is a design decision (the slow password hash already limits guessing speed). |
| [308](https://cwe.mitre.org/data/definitions/308.html) | Use of single-factor authentication | Not applicable (yet) | Design concern. |
| [311](https://cwe.mitre.org/data/definitions/311.html) | Missing encryption of sensitive data | Not applicable (yet) | No encryption API yet (seal()/open() planned for v0.6). |
| [312](https://cwe.mitre.org/data/definitions/312.html) | Cleartext storage of sensitive information | Prevented: rejected at compile time | `CWE-532`. |
| [316](https://cwe.mitre.org/data/definitions/316.html) | Cleartext storage of sensitive information in memory | Not applicable (yet) | As CWE-244. |
| [319](https://cwe.mitre.org/data/definitions/319.html) | Cleartext transmission of sensitive information | Inexpressible: the construct does not exist |  |
| [321](https://cwe.mitre.org/data/definitions/321.html) | Use of hard-coded cryptographic key | Prevented: rejected at compile time | `CWE-798`. |
| [323](https://cwe.mitre.org/data/definitions/323.html) | Reusing a nonce, key pair in encryption | Inexpressible: the construct does not exist |  |
| [324](https://cwe.mitre.org/data/definitions/324.html) | Use of a key past its expiration date | Inexpressible: the construct does not exist |  |
| [325](https://cwe.mitre.org/data/definitions/325.html) | Missing cryptographic step | Inexpressible: the construct does not exist |  |
| [326](https://cwe.mitre.org/data/definitions/326.html) | Inadequate encryption strength | Inexpressible: the construct does not exist |  |
| [327](https://cwe.mitre.org/data/definitions/327.html) | Use of a broken or risky cryptographic algorithm | Prevented: rejected at compile time | `CWE-327`. |
| [328](https://cwe.mitre.org/data/definitions/328.html) | Use of weak hash | Prevented: rejected at compile time | `CWE-327`. |
| [329](https://cwe.mitre.org/data/definitions/329.html) | Generation of predictable IV with CBC mode | Inexpressible: the construct does not exist |  |
| [330](https://cwe.mitre.org/data/definitions/330.html) | Use of insufficiently random values | Prevented: rejected at compile time | `CWE-338`. |
| [331](https://cwe.mitre.org/data/definitions/331.html) | Insufficient entropy | Prevented: rejected at compile time | `CWE-338`. |
| [335](https://cwe.mitre.org/data/definitions/335.html) | Incorrect usage of seeds in PRNG | Inexpressible: the construct does not exist |  |
| [338](https://cwe.mitre.org/data/definitions/338.html) | Use of cryptographically weak PRNG | Prevented: rejected at compile time | `CWE-338`. |
| [345](https://cwe.mitre.org/data/definitions/345.html) | Insufficient verification of data authenticity | Not applicable (yet) | No signature API yet. |
| [347](https://cwe.mitre.org/data/definitions/347.html) | Improper verification of cryptographic signature | Inexpressible: the construct does not exist |  |
| [352](https://cwe.mitre.org/data/definitions/352.html) | Cross-site request forgery | Not applicable (yet) | No web facility yet (CSRF tokens planned in the web framework). |
| [353](https://cwe.mitre.org/data/definitions/353.html) | Missing support for integrity check | Prevented: attempt compiles but has no effect | hash() and hash_verify() are available. Integrity is opt-in. |
| [359](https://cwe.mitre.org/data/definitions/359.html) | Exposure of private personal information | Prevented: rejected at compile time | `CWE-862`. Personal data declared sensitive can only be read under a grant. |
| [362](https://cwe.mitre.org/data/definitions/362.html) | Concurrent execution using shared resource with improper synchronization (race) | Inexpressible: the construct does not exist |  |
| [364](https://cwe.mitre.org/data/definitions/364.html) | Signal handler race condition | Inexpressible: the construct does not exist |  |
| [366](https://cwe.mitre.org/data/definitions/366.html) | Race condition within a thread | Inexpressible: the construct does not exist |  |
| [367](https://cwe.mitre.org/data/definitions/367.html) | Time-of-check time-of-use race | Inexpressible: the construct does not exist | There is no separate existence check; read_file(path, 4096) returns the contents or none in one step. |
| [367](https://cwe.mitre.org/data/definitions/367.html) | Time-of-check time-of-use (grant used after the checked data changed) | Prevented: stopped safely at run time | `CWE-367`. Each protected call evaluates the policy again on the grant's arguments. |
| [369](https://cwe.mitre.org/data/definitions/369.html) | Divide by zero | Prevented: stopped safely at run time | `CWE-369`. |
| [377](https://cwe.mitre.org/data/definitions/377.html) | Insecure temporary file | Not applicable (yet) | No temporary-file API. |
| [384](https://cwe.mitre.org/data/definitions/384.html) | Session fixation | Not applicable (yet) | No session facility. |
| [385](https://cwe.mitre.org/data/definitions/385.html) | Covert timing channel | Not applicable (yet) | Below the language. |
| [390](https://cwe.mitre.org/data/definitions/390.html) | Detection of error condition without action | Prevented: rejected at compile time | `CWE-390`. An empty else is a warning; an error with --strict (tested that way). |
| [391](https://cwe.mitre.org/data/definitions/391.html) | Unchecked error condition | Prevented: rejected at compile time | `CWE-476`. |
| [396](https://cwe.mitre.org/data/definitions/396.html) | Declaration of catch for generic exception | Inexpressible: the construct does not exist |  |
| [397](https://cwe.mitre.org/data/definitions/397.html) | Declaration of throws for generic exception | Inexpressible: the construct does not exist |  |
| [400](https://cwe.mitre.org/data/definitions/400.html) | Uncontrolled resource consumption | Prevented: stopped safely at run time | `CWE-400`. The heap limit (CAPSTAN_MAX_HEAP; 64 MB in this test) stops runaway allocation safely. validate_range() bounds input values. |
| [401](https://cwe.mitre.org/data/definitions/401.html) | Missing release of memory after effective lifetime (leak) | Prevented: attempt compiles but has no effect | Unreachable memory is collected. Memory still reachable from live data (a growing global list) is retained by design. |
| [404](https://cwe.mitre.org/data/definitions/404.html) | Improper resource shutdown or release | Inexpressible: the construct does not exist | Files are read and written whole; there are no handles to leak. |
| [405](https://cwe.mitre.org/data/definitions/405.html) | Asymmetric resource consumption (amplification) | Not applicable (yet) | Network concern. |
| [407](https://cwe.mitre.org/data/definitions/407.html) | Inefficient algorithmic complexity | Logic or design decision: beyond any language | Algorithm choice is a design decision. |
| [415](https://cwe.mitre.org/data/definitions/415.html) | Double free | Prevented: rejected at compile time | `CWE-415`. |
| [416](https://cwe.mitre.org/data/definitions/416.html) | Use after free | Prevented: rejected at compile time | `CWE-415`. There is no free(); memory is reclaimed only when unreachable. |
| [425](https://cwe.mitre.org/data/definitions/425.html) | Direct request (forced browsing) | Not applicable (yet) | No web facility. |
| [426](https://cwe.mitre.org/data/definitions/426.html) | Untrusted search path | Inexpressible: the construct does not exist |  |
| [427](https://cwe.mitre.org/data/definitions/427.html) | Uncontrolled search path element | Inexpressible: the construct does not exist |  |
| [434](https://cwe.mitre.org/data/definitions/434.html) | Unrestricted upload of file with dangerous type | Not applicable (yet) | No upload facility. |
| [457](https://cwe.mitre.org/data/definitions/457.html) | Use of uninitialized variable | Prevented: rejected at compile time | `CWE-457`. |
| [459](https://cwe.mitre.org/data/definitions/459.html) | Incomplete cleanup | Inexpressible: the construct does not exist |  |
| [466](https://cwe.mitre.org/data/definitions/466.html) | Return of pointer value outside of expected range | Inexpressible: the construct does not exist |  |
| [467](https://cwe.mitre.org/data/definitions/467.html) | Use of sizeof() on a pointer type | Inexpressible: the construct does not exist |  |
| [468](https://cwe.mitre.org/data/definitions/468.html) | Incorrect pointer scaling | Inexpressible: the construct does not exist |  |
| [469](https://cwe.mitre.org/data/definitions/469.html) | Use of pointer subtraction to determine size | Inexpressible: the construct does not exist |  |
| [470](https://cwe.mitre.org/data/definitions/470.html) | Use of externally-controlled input to select classes or code (unsafe reflection) | Inexpressible: the construct does not exist |  |
| [476](https://cwe.mitre.org/data/definitions/476.html) | NULL pointer dereference | Prevented: rejected at compile time | `CWE-476`. |
| [477](https://cwe.mitre.org/data/definitions/477.html) | Use of obsolete function | Prevented: rejected at compile time | `CWE-327`. |
| [478](https://cwe.mitre.org/data/definitions/478.html) | Missing default case in multiple condition expression | Prevented: rejected at compile time | `CWE-478`. match must handle every variant or have an else branch. |
| [480](https://cwe.mitre.org/data/definitions/480.html) | Use of incorrect operator | Logic or design decision: beyond any language | Which operator was meant is the programmer's intent. |
| [480](https://cwe.mitre.org/data/definitions/480.html) | Use of incorrect operator (bitwise on booleans) | Prevented: rejected at compile time | `CWE-480`. |
| [481](https://cwe.mitre.org/data/definitions/481.html) | Assigning instead of comparing | Inexpressible: the construct does not exist |  |
| [482](https://cwe.mitre.org/data/definitions/482.html) | Comparing instead of assigning | Prevented: rejected at compile time | `expression result is unused`. |
| [483](https://cwe.mitre.org/data/definitions/483.html) | Incorrect block delimitation | Inexpressible: the construct does not exist | Braces are mandatory. |
| [484](https://cwe.mitre.org/data/definitions/484.html) | Omitted break statement in switch | Inexpressible: the construct does not exist | match has no fall-through between cases. |
| [489](https://cwe.mitre.org/data/definitions/489.html) | Active debug code | Prevented: rejected at compile time | `CWE-489`. A debug switch left on is an error in --release builds (tested that way). |
| [494](https://cwe.mitre.org/data/definitions/494.html) | Download of code without integrity check | Inexpressible: the construct does not exist |  |
| [497](https://cwe.mitre.org/data/definitions/497.html) | Exposure of sensitive system information | Not applicable (yet) | No system-information API. |
| [502](https://cwe.mitre.org/data/definitions/502.html) | Deserialization of untrusted data | Inexpressible: the construct does not exist |  |
| [506](https://cwe.mitre.org/data/definitions/506.html) | Embedded malicious code | Not applicable (yet) | Supply-chain concern; signed packages are planned. |
| [521](https://cwe.mitre.org/data/definitions/521.html) | Weak password requirements | Logic or design decision: beyond any language | Password rules are policy. |
| [522](https://cwe.mitre.org/data/definitions/522.html) | Insufficiently protected credentials | Prevented: rejected at compile time | `CWE-200`. |
| [532](https://cwe.mitre.org/data/definitions/532.html) | Insertion of sensitive information into log file | Prevented: rejected at compile time | `CWE-532`. |
| [532](https://cwe.mitre.org/data/definitions/532.html) | Insertion of sensitive information into output (hash of a secret) | Prevented: rejected at compile time | `CWE-532`. A fast hash of a short secret is reversed by trying every value. |
| [538](https://cwe.mitre.org/data/definitions/538.html) | Insertion of sensitive information into externally-accessible file | Prevented: rejected at compile time | `CWE-532`. |
| [543](https://cwe.mitre.org/data/definitions/543.html) | Use of singleton pattern without synchronization | Inexpressible: the construct does not exist |  |
| [546](https://cwe.mitre.org/data/definitions/546.html) | Suspicious comment | Prevented: rejected at compile time | `CWE-546`. A warning; an error with --strict (tested that way). |
| [547](https://cwe.mitre.org/data/definitions/547.html) | Use of hard-coded, security-relevant constants | Prevented: rejected at compile time | `CWE-547`. A warning; an error with --strict (tested that way). |
| [552](https://cwe.mitre.org/data/definitions/552.html) | Files or directories accessible to external parties | Not applicable (yet) | Deployment concern. |
| [561](https://cwe.mitre.org/data/definitions/561.html) | Dead code | Prevented: rejected at compile time | `CWE-561`. Warning; an error with --strict (tested that way). |
| [563](https://cwe.mitre.org/data/definitions/563.html) | Assignment to variable without use | Prevented: rejected at compile time | `CWE-563`. Warning; an error with --strict (tested that way). |
| [565](https://cwe.mitre.org/data/definitions/565.html) | Reliance on cookies without validation | Prevented: rejected at compile time | `CWE-807`. |
| [567](https://cwe.mitre.org/data/definitions/567.html) | Unsynchronized access to shared data | Inexpressible: the construct does not exist |  |
| [570](https://cwe.mitre.org/data/definitions/570.html) | Expression is always false | Prevented: rejected at compile time | `CWE-570`. Warning; an error with --strict (tested that way). |
| [571](https://cwe.mitre.org/data/definitions/571.html) | Expression is always true | Prevented: rejected at compile time | `CWE-571`. Warning; an error with --strict (tested that way). |
| [587](https://cwe.mitre.org/data/definitions/587.html) | Assignment of a fixed address to a pointer | Inexpressible: the construct does not exist |  |
| [590](https://cwe.mitre.org/data/definitions/590.html) | Free of memory not on the heap | Prevented: rejected at compile time | `CWE-415`. |
| [595](https://cwe.mitre.org/data/definitions/595.html) | Comparison of object references instead of object contents | Prevented: rejected at compile time | `cannot compare`. |
| [597](https://cwe.mitre.org/data/definitions/597.html) | Use of wrong operator in string comparison | Prevented: attempt compiles but has no effect | == on strings compares contents, not references. |
| [601](https://cwe.mitre.org/data/definitions/601.html) | URL redirection to untrusted site (open redirect) | Not applicable (yet) | No web facility. |
| [602](https://cwe.mitre.org/data/definitions/602.html) | Client-side enforcement of server-side security | Not applicable (yet) | Architecture concern. |
| [606](https://cwe.mitre.org/data/definitions/606.html) | Unchecked input for loop condition | Prevented: stopped safely at run time | `CWE-400`. |
| [611](https://cwe.mitre.org/data/definitions/611.html) | XML external entity reference (XXE) | Inexpressible: the construct does not exist |  |
| [613](https://cwe.mitre.org/data/definitions/613.html) | Insufficient session expiration (grant kept beyond its request) | Prevented: rejected at compile time | `CWE-613`. |
| [617](https://cwe.mitre.org/data/definitions/617.html) | Reachable assertion | Prevented: rejected at compile time | `CWE-617`. assert() outside tests is a warning; an error with --strict (tested that way). |
| [620](https://cwe.mitre.org/data/definitions/620.html) | Unverified password change | Logic or design decision: beyond any language | Workflow design. |
| [636](https://cwe.mitre.org/data/definitions/636.html) | Not failing securely (failing open) | Prevented: rejected at compile time | `default deny`. |
| [639](https://cwe.mitre.org/data/definitions/639.html) | IDOR (policy that ignores the object) | Prevented: rejected at compile time | `CWE-639`. Reported as a warning; an error with --strict (tested that way). |
| [639](https://cwe.mitre.org/data/definitions/639.html) | Authorization bypass through user-controlled key (IDOR) | Prevented: stopped safely at run time | `CWE-639`. |
| [640](https://cwe.mitre.org/data/definitions/640.html) | Weak password recovery mechanism | Not applicable (yet) | Design concern. |
| [643](https://cwe.mitre.org/data/definitions/643.html) | XPath injection | Not applicable (yet) | No XPath facility. |
| [652](https://cwe.mitre.org/data/definitions/652.html) | XQuery injection | Not applicable (yet) | No XQuery facility. |
| [667](https://cwe.mitre.org/data/definitions/667.html) | Improper locking | Inexpressible: the construct does not exist |  |
| [670](https://cwe.mitre.org/data/definitions/670.html) | Always-incorrect control flow implementation | Logic or design decision: beyond any language | Control-flow intent. |
| [674](https://cwe.mitre.org/data/definitions/674.html) | Uncontrolled recursion | Prevented: stopped safely at run time | `CWE-674`. |
| [676](https://cwe.mitre.org/data/definitions/676.html) | Use of potentially dangerous function | Prevented: rejected at compile time | `CWE-120`. |
| [681](https://cwe.mitre.org/data/definitions/681.html) | Incorrect conversion between numeric types | Inexpressible: the construct does not exist |  |
| [682](https://cwe.mitre.org/data/definitions/682.html) | Incorrect calculation | Logic or design decision: beyond any language | A wrong formula is a specification error. Overflow from it is still caught. |
| [693](https://cwe.mitre.org/data/definitions/693.html) | Protection mechanism failure | Possible only through an audited escape hatch | trust() is audited: it needs a justification and is reported in every build. |
| [697](https://cwe.mitre.org/data/definitions/697.html) | Incorrect comparison | Logic or design decision: beyond any language | Comparison logic is intent. |
| [704](https://cwe.mitre.org/data/definitions/704.html) | Incorrect type conversion or cast | Prevented: stopped safely at run time | `CWE-704`. |
| [732](https://cwe.mitre.org/data/definitions/732.html) | Incorrect permission assignment for critical resource | Inexpressible: the construct does not exist |  |
| [754](https://cwe.mitre.org/data/definitions/754.html) | Improper check for unusual or exceptional conditions | Prevented: rejected at compile time | `CWE-476`. |
| [755](https://cwe.mitre.org/data/definitions/755.html) | Improper handling of exceptional conditions | Prevented: rejected at compile time | `CWE-476`. |
| [759](https://cwe.mitre.org/data/definitions/759.html) | Use of a one-way hash without a salt | Prevented: rejected at compile time | `CWE-916`. |
| [760](https://cwe.mitre.org/data/definitions/760.html) | Use of a one-way hash with a predictable salt | Prevented: rejected at compile time | `CWE-916`. |
| [761](https://cwe.mitre.org/data/definitions/761.html) | Free of pointer not at start of buffer | Prevented: rejected at compile time | `CWE-415`. |
| [762](https://cwe.mitre.org/data/definitions/762.html) | Mismatched memory management routines | Prevented: rejected at compile time | `CWE-415`. |
| [763](https://cwe.mitre.org/data/definitions/763.html) | Release of invalid pointer or reference | Prevented: rejected at compile time | `CWE-415`. |
| [770](https://cwe.mitre.org/data/definitions/770.html) | Allocation of resources without limits or throttling | Prevented: stopped safely at run time | `CWE-400`. |
| [772](https://cwe.mitre.org/data/definitions/772.html) | Missing release of resource after effective lifetime | Inexpressible: the construct does not exist |  |
| [775](https://cwe.mitre.org/data/definitions/775.html) | Missing release of file descriptor or handle | Inexpressible: the construct does not exist |  |
| [776](https://cwe.mitre.org/data/definitions/776.html) | XML entity expansion (billion laughs) | Inexpressible: the construct does not exist |  |
| [780](https://cwe.mitre.org/data/definitions/780.html) | Use of RSA algorithm without OAEP | Inexpressible: the construct does not exist |  |
| [783](https://cwe.mitre.org/data/definitions/783.html) | Operator precedence logic error (bitwise) | Prevented: rejected at compile time | `CWE-783`. A bitwise operator may not be mixed with another operator without parentheses. |
| [783](https://cwe.mitre.org/data/definitions/783.html) | Operator precedence logic error | Prevented: rejected at compile time | `CWE-783`. Mixing && inside || without parentheses is a warning; an error with --strict (tested that way). |
| [786](https://cwe.mitre.org/data/definitions/786.html) | Access of memory location before start of buffer | Prevented: stopped safely at run time | `CWE-125`. |
| [787](https://cwe.mitre.org/data/definitions/787.html) | Out-of-bounds write | Prevented: stopped safely at run time | `CWE-787`. |
| [788](https://cwe.mitre.org/data/definitions/788.html) | Access of memory location after end of buffer | Prevented: stopped safely at run time | `CWE-125`. |
| [789](https://cwe.mitre.org/data/definitions/789.html) | Memory allocation with excessive size value | Prevented: stopped safely at run time | `CWE-400`. |
| [798](https://cwe.mitre.org/data/definitions/798.html) | Hard-coded password-like literal under an innocuous name | **Gap: can be written** | A short password-like literal under an ordinary name is indistinguishable from other text. |
| [798](https://cwe.mitre.org/data/definitions/798.html) | Use of hard-coded credentials | Prevented: rejected at compile time | `CWE-798`. |
| [798](https://cwe.mitre.org/data/definitions/798.html) | Hard-coded credential in a recognised format, under an innocuous name | Prevented: rejected at compile time | `CWE-798`. Literals in known credential formats (payment, cloud, source-hosting and chat tokens; private keys) are rejected wherever they appear. |
| [799](https://cwe.mitre.org/data/definitions/799.html) | Improper control of interaction frequency | Logic or design decision: beyond any language | Rate limiting is a design decision. |
| [805](https://cwe.mitre.org/data/definitions/805.html) | Buffer access with incorrect length value | Prevented: stopped safely at run time | `CWE-125`. |
| [806](https://cwe.mitre.org/data/definitions/806.html) | Buffer access using size of source buffer | Prevented: stopped safely at run time | `CWE-125`. |
| [807](https://cwe.mitre.org/data/definitions/807.html) | Reliance on untrusted inputs in a security decision | Prevented: rejected at compile time | `CWE-807`. |
| [820](https://cwe.mitre.org/data/definitions/820.html) | Missing synchronization | Inexpressible: the construct does not exist |  |
| [821](https://cwe.mitre.org/data/definitions/821.html) | Incorrect synchronization | Inexpressible: the construct does not exist |  |
| [824](https://cwe.mitre.org/data/definitions/824.html) | Access of uninitialized pointer | Prevented: rejected at compile time | `CWE-457`. |
| [825](https://cwe.mitre.org/data/definitions/825.html) | Expired pointer dereference | Inexpressible: the construct does not exist |  |
| [829](https://cwe.mitre.org/data/definitions/829.html) | Inclusion of functionality from untrusted control sphere | Inexpressible: the construct does not exist |  |
| [833](https://cwe.mitre.org/data/definitions/833.html) | Deadlock | Inexpressible: the construct does not exist |  |
| [834](https://cwe.mitre.org/data/definitions/834.html) | Excessive iteration | Logic or design decision: beyond any language | Loop bounds are a design decision. |
| [835](https://cwe.mitre.org/data/definitions/835.html) | Loop with unreachable exit condition (infinite loop) | Logic or design decision: beyond any language | Whether a loop terminates is undecidable in general (the halting problem). |
| [837](https://cwe.mitre.org/data/definitions/837.html) | Improper enforcement of a single, unique action | Logic or design decision: beyond any language | Business rule. |
| [841](https://cwe.mitre.org/data/definitions/841.html) | Improper enforcement of behavioral workflow | Logic or design decision: beyond any language | Workflow order is a design decision; typestate checking is a possible future feature. |
| [843](https://cwe.mitre.org/data/definitions/843.html) | Access of resource using incompatible type (type confusion) | Inexpressible: the construct does not exist |  |
| [862](https://cwe.mitre.org/data/definitions/862.html) | Missing authorization (data type not declared sensitive) | **Gap: can be written** | Protection starts when the type is declared sensitive. It is declared once per type, not per function, but it can still be forgotten. |
| [862](https://cwe.mitre.org/data/definitions/862.html) | Missing authorization | Prevented: rejected at compile time | `CWE-862`. |
| [862](https://cwe.mitre.org/data/definitions/862.html) | Missing authorization (record read with no grant) | Prevented: rejected at compile time | `CWE-862`. Fields of a sensitive struct can only be read in protected functions, policies and tests. |
| [863](https://cwe.mitre.org/data/definitions/863.html) | Incorrect authorization | Logic or design decision: beyond any language | A consistent but wrong policy is a requirements error. Denial tests, policy assertions (roadmap) and review are the defences. |
| [908](https://cwe.mitre.org/data/definitions/908.html) | Use of uninitialized resource | Prevented: rejected at compile time | `CWE-908`. |
| [909](https://cwe.mitre.org/data/definitions/909.html) | Missing initialization of resource | Prevented: rejected at compile time | `CWE-908`. |
| [912](https://cwe.mitre.org/data/definitions/912.html) | Hidden functionality | Logic or design decision: beyond any language | A deliberate backdoor written as ordinary logic is indistinguishable from intended logic. Code review and Capstan Review (AI) are the defences. |
| [915](https://cwe.mitre.org/data/definitions/915.html) | Improperly controlled modification of dynamically-determined object attributes | Inexpressible: the construct does not exist |  |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password in an innocuously named variable) | **Gap: can be written** | Detection is name-based. Typing passwords as Secret at input would make this a type error (roadmap). |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password passed through a method call) | **Gap: can be written** | The password-name heuristic stops at N_METHOD nodes, so wrapping a password in a string method may evade the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted. |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Weak password hash (password passed through a helper call) | **Gap: can be written** | The password-name heuristic stops at N_CALL nodes, so a helper that preserves Tainted can hide a password-like variable from the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted. |
| [916](https://cwe.mitre.org/data/definitions/916.html) | Use of password hash with insufficient computational effort | Prevented: rejected at compile time | `CWE-916`. |
| [917](https://cwe.mitre.org/data/definitions/917.html) | Expression language injection | Inexpressible: the construct does not exist |  |
| [918](https://cwe.mitre.org/data/definitions/918.html) | Server-side request forgery | Inexpressible: the construct does not exist |  |
| [1007](https://cwe.mitre.org/data/definitions/1007.html) | Insufficient visual distinction of homoglyphs and invisible characters (Trojan Source) | Prevented: rejected at compile time | `CWE-1007`. Bidirectional controls and zero-width characters are rejected anywhere in source (CVE-2021-42574). |
| [1021](https://cwe.mitre.org/data/definitions/1021.html) | Improper restriction of rendered UI layers (clickjacking) | Not applicable (yet) | No web facility. |
| [1023](https://cwe.mitre.org/data/definitions/1023.html) | Incomplete comparison with missing factors | Logic or design decision: beyond any language | As CWE-697. |
| [1077](https://cwe.mitre.org/data/definitions/1077.html) | Floating point comparison with incorrect operator | Inexpressible: the construct does not exist |  |
| [1104](https://cwe.mitre.org/data/definitions/1104.html) | Use of unmaintained third-party components | Not applicable (yet) | No package system yet. |
| [1164](https://cwe.mitre.org/data/definitions/1164.html) | Irrelevant code | Prevented: rejected at compile time | `CWE-1164`. Warning; an error with --strict (tested that way). |
| [1188](https://cwe.mitre.org/data/definitions/1188.html) | Insecure default initialization of resource | Prevented: rejected at compile time | `CWE-908`. There are no implicit defaults; every field must be given. |
| [1236](https://cwe.mitre.org/data/definitions/1236.html) | CSV formula injection (attempt after escape_csv) | Prevented: attempt compiles but has no effect |  |
| [1236](https://cwe.mitre.org/data/definitions/1236.html) | CSV formula injection | Prevented: rejected at compile time | `escape_csv`. Untrusted text cannot be written to a file unchanged. |
| [1265](https://cwe.mitre.org/data/definitions/1265.html) | Unintended reentrant invocation of non-reentrant code | Inexpressible: the construct does not exist |  |
| [1284](https://cwe.mitre.org/data/definitions/1284.html) | Improper validation of specified quantity in input | Logic or design decision: beyond any language | Which range is valid is business knowledge; validate_range(t, min, max) makes enforcing it one call. Overflow is still caught. |
| [1287](https://cwe.mitre.org/data/definitions/1287.html) | Improper validation of specified type in input | Prevented: attempt compiles but has no effect |  |
| [1321](https://cwe.mitre.org/data/definitions/1321.html) | Prototype pollution | Inexpressible: the construct does not exist |  |
| [1325](https://cwe.mitre.org/data/definitions/1325.html) | Improperly controlled sequential memory allocation | Prevented: attempt compiles but has no effect | Collections grow geometrically with checked sizes. |
| [1333](https://cwe.mitre.org/data/definitions/1333.html) | Inefficient regular expression complexity (ReDoS) | Inexpressible: the construct does not exist |  |
| [1335](https://cwe.mitre.org/data/definitions/1335.html) | Incorrect bitwise shift of integer | Prevented: rejected at compile time | `CWE-1335`. A literal shift count outside 0..63 does not compile. |
| [1335](https://cwe.mitre.org/data/definitions/1335.html) | Incorrect bitwise shift of integer (computed count) | Prevented: stopped safely at run time | `CWE-1335`. |
| [1339](https://cwe.mitre.org/data/definitions/1339.html) | Insufficient precision or accuracy of a real number | Inexpressible: the construct does not exist |  |
| [1341](https://cwe.mitre.org/data/definitions/1341.html) | Multiple releases of same resource | Prevented: rejected at compile time | `CWE-415`. |
| [1386](https://cwe.mitre.org/data/definitions/1386.html) | Insecure operation on Windows junction / mount point | Not applicable (yet) | Platform file-system concern. |
| [1390](https://cwe.mitre.org/data/definitions/1390.html) | Weak authentication | Not applicable (yet) | Design concern. |
| [1391](https://cwe.mitre.org/data/definitions/1391.html) | Use of weak credentials | Prevented: rejected at compile time | `CWE-798`. |
| [1392](https://cwe.mitre.org/data/definitions/1392.html) | Use of default credentials | Prevented: rejected at compile time | `CWE-798`. |
| [1393](https://cwe.mitre.org/data/definitions/1393.html) | Use of default password | Prevented: rejected at compile time | `CWE-798`. |
| [1394](https://cwe.mitre.org/data/definitions/1394.html) | Use of default cryptographic key | Prevented: rejected at compile time | `CWE-798`. |
