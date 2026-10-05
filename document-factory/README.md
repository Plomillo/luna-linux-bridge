# LOUKSNA Document Factory — candidate v0.1.0

STATUS: IMPLEMENTED_CANDIDATE_NOT_CERTIFIED

Authority: `Louksna.md`
Assurance reference: `PUAC2.md`
Doctrine: EXTEND_DO_NOT_REPLACE
Failure posture: FAIL_CLOSED
Canonical mutation: FORBIDDEN
Certification inheritance: FORBIDDEN

This module is a source-first, Git-native, profile-driven document factory. It is not hard-coded to one course, rubric, subject, or deliverable set. Each task is represented by preserved raw instructions plus a typed profile that maps requirements and rubric criteria to validation and evidence.

Flow:

RAW_INSTRUCTIONS -> PROFILE -> CHECKPOINT -> WRITE -> BUILD -> VERIFY
-> METACOGNITIVE_SELF_AUDIT -> FREEZE -> G23 -> G24
-> OPERATIONAL_AUTHORIZATION -> ACTIVE

Formats:
- DOCX/PPTX: pinned Pandoc provider.
- PDF: independent LibreOffice headless render of the DOCX.
- XLSX: deterministic stdlib OOXML writer.
- Audiovisual: external media is validated; the factory does not fabricate a student's recorded performance.

Writing is governed source work. Markdown/CSL/JSON are primary editable sources. Each writing provider is logged and has no certification authority.

Anti-paralysis:
- one-second heartbeat while stages run;
- explicit timeout per stage;
- bounded attempts;
- no blind retry;
- checkpoint before a build;
- HOLD with causal evidence on timeout/failure;
- resume from the last verified checkpoint.

The current UNIACC neuroplasticity task is encoded in a task profile. Future assignments use new profiles without changing engine logic.

No file in this candidate claims G23 or G24. Independent assurance must consume a frozen candidate as read-only data from a separately controlled trust root.
