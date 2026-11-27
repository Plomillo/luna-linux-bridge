# C05 source-grounded executable-plan expansion — 2026-11-27

## Status and boundary

This report records implementation readiness only. It does not certify C05 and does not claim that the newly added plans have already completed restricted-container execution.

- Complete source-bound executable plans: **54 / 1,000**
- Cases outside the executable plan set: **946 / 1,000**
- Remaining underlying executions for those 946 cases: **4,730** (three NORMAL, one NEGATIVE, one BOUNDARY per case)
- Typed normal specifications: **101**
- Typed specifications still missing at least one required control: **47**
- Interpreter candidates: **7**; ready and registered: **2**; blocked: **5**
- Cases with neither a typed normal specification nor an interpreter candidate: **894**
- C05: **NOT_PASSED**

## Implementation added in this increment

### D01 serialization, representation and encoding
Added complementary source-derived controls for BOM handling, grapheme/code-point distinctions, CRLF/LF normalization, multiline CSV, nested JSON types, Unicode JSON, duplicate JSON keys, valid JSON acceptance, canonical empty objects, framed binary records, float32 exactness, decimal preservation, Base64 byte preservation and strict padding rejection, the empty SHA-256 vector, and empty-manifest hash mutation.

Added further Unicode normalization controls for:
- NFC mismatch (decomposed acute accent compared with an unaccented character);
- NFD decomposition of ñ;
- NFKC conversion of fullwidth A.

The D01 independent oracle now uses explicit published/fixed vectors for the new cases. Decimal and SHA-256 oracles were generalized to verify the alternate decimal and empty-input vectors independently.

### D03 and numerical controls
Added source-derived controls for:
- linear and binary search (previous increment);
- duplicate detection, bracket validation, stable age sorting and stack underflow (previous increments);
- L2 norm: malformed component rejection and the zero-vector boundary;
- Pearson correlation: zero-variance rejection and perfect positive/negative two-point boundaries.

The L2 executor now rejects non-integer components explicitly. The independent norm oracle recomputes the integer square root; the Pearson oracle independently handles zero variance and recomputes the raw-score coefficient.

## Validation requirements

The compiler and regression assertions now expect 54 complete plans and 946 cases outside the plan set. The population inventory validator requires the NOT_RUN identifiers to be exactly the complement of valid executable-plan identifiers; it does not accept a matching count with substituted IDs.

The hosted restricted-container workflow must still execute the 54 plans (270 runs) and persist authentic evidence. The independent workflow must validate those artifacts. No results from either workflow are asserted in this report.

## Remaining work

All 946 cases outside the plan set still require source-grounded normal plans, registered capabilities, fixtures, negative and boundary controls, and actual restricted-container execution. Cases with missing essential parameters remain blocked rather than receiving invented inputs. C05 cannot pass until all 1,000 cases have five valid runs, individual evidence validation, contractual PASS, and global validation.
