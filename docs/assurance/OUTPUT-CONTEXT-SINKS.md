# Output-context types and sink contracts

> Status: implementation landed on the rebased draft PR #491 branch; exact-head test/CI validation pending.
> Scope: HTML, log and CSV output contexts. JSON migration is deliberately separate.

## Contract

Capstan distinguishes context-encoded values from ordinary trusted strings:

| Type | Producer | Permitted output sink |
|---|---|---|
| `Html` | `escape_html()` and safe HTML composition | `write_html_file()` |
| `LogText` | `escape_log()` and safe log composition | `write_log_file()`, `print()` and `println()` |
| `CsvText` | `escape_csv()` and safe CSV composition | `write_csv_file()` |

Terminal output is a log context: `print()` and `println()` accept `LogText` or trusted `string`, but reject `Html` and `CsvText`. The format-agnostic `write_file(path, data)` accepts trusted `string` only. It rejects `Tainted` data and all three context-encoded types. A context-encoded value cannot be assigned to `string`, passed to another context's sink, or mixed with a different context type.

Concatenation of a context-encoded value with trusted `string` or a value of the same context preserves that context. Concatenation with `Tainted` data or another context type is rejected. This permits assembling a CSV row from independently escaped fields and literal delimiters without erasing the CSV context.

The three typed file sinks currently lower to the same bounded-path-checked runtime file-writing primitive. Their security distinction is enforced by the compiler's type checker, not by filename extensions or runtime inspection of file contents. Calling `write_csv_file("page.html", csv)` does not make the contents HTML; it writes the caller-supplied CSV representation to that path. The sink name is an explicit declaration of intended output context, not a file-format detector.

## Deliberate scope limits

- `Html` still does not encode HTML subcontexts as distinct types. The existing expression-local HTML context checker remains responsible for rejecting known unsafe script, style, URL, event-handler and unquoted-attribute cases. Cross-statement HTML context tracking remains an atlas gap.
- `escape_json()` still returns a plain `string` fragment (contents of a JSON string literal, without surrounding quotes). The language server and Shroud accessibility serializer currently compose JSON from these fragments in string/list-based pipelines. Consequently, an escaped JSON fragment can still be passed to generic `write_file()` and then used in a different format (for example, CSV); this remains a CWE-116 atlas gap. The JSON escaper also escapes the terminal-hostile Unicode set used by `escape_log()` (C1 and bidi controls), so the known JSON-fragment-to-terminal control-byte attempt is neutralised, although the result remains a plain string rather than a distinct `LogText` type. A typed `JsonText` and JSON sink must be introduced together with a migration of those serializers and their tests; this increment does not claim JSON sink safety.
- `escape_csv()` neutralises the tested ASCII, leading-space, LF and full-width formula prefixes, but this is not a universal spreadsheet guarantee. Spreadsheet clients differ, and Microsoft Excel may strip some quoting/escape characters when a CSV is saved and reopened. Do not claim all spreadsheet workflows are safe without client-specific validation; see [OWASP CSV Injection guidance](https://github.com/OWASP/www-community/blob/master/pages/attacks/CSV_Injection.md).
- `escape_c()` remains a string fragment used by compiler code generation; it is not an application file-format encoder.
- Plain trusted strings remain available to the generic `write_file()`. The type system does not infer a file's intended format from its path or contents. Applications should use the typed sink for context-sensitive output and must not declassify attacker-controlled data with `trust()` without an audited justification.

## Evidence

The implementation on PR #491 adds positive conformance coverage for all three matching sinks and negative tests for:
- HTML-encoded data passed to the generic file sink (CWE-116 atlas regression);
- untrusted input passed directly to a typed HTML sink (CWE-20);
- HTML data passed to the CSV sink;
- HTML or CSV data passed to terminal/log output;
- `LogText` passed to terminal output (positive control);
- CSV formula leaders (`=`, `+`, `-`, `@`, tab, CR and LF), full-width variants and leading ASCII spaces before a leader are prefixed before the field content (CWE-1236 regressions);
- CSV context preservation through `+=`, with mixed-context concatenation, unescaped tainted concatenation and assignment to plain `string` rejected (CWE-116);
- JSON fragments containing C1/bidi terminal controls are neutralised by `escape_json()` (CWE-117 atlas regression);
- CSV data passed to the HTML sink;
- plain trusted strings passed to a typed CSV sink;
- Secret values passed to a file sink.

The fixtures and implementation described here remain on the unmerged PR #238 branch. The standard suite must compile the compiler and programs through the stage-0 bootstrap and check generated C warning-free; results must be recorded against the exact implementation PR head after CI completes. The current compiler still uses one runtime file-writing primitive behind the three statically typed sinks. No universal proof is claimed by this document.
