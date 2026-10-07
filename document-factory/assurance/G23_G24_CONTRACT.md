# Independent assurance contract

Candidate code may build, verify and self-audit. Candidate code MUST NOT issue G23 or G24.

G23 requires:
- a validator source controlled by a separate trust-root/base branch;
- candidate consumed as immutable data;
- recomputation of the candidate digest;
- framework selftests and demonstration artifacts checked independently;
- exact rubric arithmetic and explicit task constraints checked for the active profile;
- unresolved or unpinned providers reported, never silently converted to PASS;
- no repair of candidate during independent validation.

G24 requires:
- favorable G23 bound to the exact candidate digest;
- authenticated authority evidence;
- a scope-limited certificate;
- no certification propagation to future assignment profiles or generated submissions;
- operational authorization remains separate.

FAIL, UNKNOWN or CONFLICT in a mandatory precondition denies certificate issuance.
