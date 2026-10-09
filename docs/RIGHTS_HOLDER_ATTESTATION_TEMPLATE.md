# Rights-holder, licensing and maintainer attestation — 0.4.0-3

**Purpose:** collect the human authorization needed to complete Debian legal metadata. This is a blank template, not a license grant, legal opinion, or evidence that any field has been approved.

**Repository:** https://github.com/Plomillo/luna-linux-bridge  
**Candidate branch:** `work/louksna-zd-v04-03-mtls-provisioning-20261008`  
**Package:** `louksna-linux-bridge` 0.4.0-3  
**Current status:** HOLD — no verified rights-holder declaration or redistribution license located.

## A. Rights-holder declaration

- Legal name of the rights holder (person or entity): **[REQUIRED]**
- Jurisdiction / entity identifier, if applicable: **[REQUIRED IF APPLICABLE]**
- Capacity of signer (rights holder, authorized representative, employer, assignee): **[REQUIRED]**
- Signer's full name and role: **[REQUIRED]**
- Evidence of authority to license all covered material (link or document reference): **[REQUIRED]**
- Copyright year(s) supported by source records: **[REQUIRED; DO NOT GUESS]**
- Scope of owned material: list exact paths or attach a path manifest: **[REQUIRED]**
- Excluded files / third-party material: **[REQUIRED]**

Declaration:
> I confirm that I am the rights holder for the material listed above, or am authorized to act for the rights holder. I have authority to grant the license specified below for that material. Any exclusions and third-party components are explicitly listed.

## B. Explicit license decision

- SPDX license identifier: **[REQUIRED; choose only after authorization]**
- Full license text or authoritative license URL: **[REQUIRED]**
- Does this grant cover redistribution in source and binary Debian packages? **[YES / NO; REQUIRED]**
- Does it cover modification and distribution of modified versions? **[YES / NO; REQUIRED]**
- Additional attribution, notice, patent, trademark, or source-offer conditions: **[REQUIRED; state NONE only after review]**
- Effective date and version/commit scope of the grant: **[REQUIRED]**

Do not select MIT, Apache-2.0, GPL, public domain, or another license merely to make packaging checks pass. A selection is valid only when made by an authorized rights holder or supported by an already applicable license instrument.

## C. Source and third-party provenance

For each file group in `docs/PACKAGE_COMPONENT_INVENTORY.md`, provide:

| File group / paths | Original / derived / third-party | Original source or upstream URL | Copyright notice | Applicable license / SPDX | Required notices | Evidence reference |
|---|---|---|---|---|---|---|
| `bridge/*.py` | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] |
| `bridge/*.json` | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] |
| `scripts/provision-mtls-local.sh` | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] |
| `bridge/deploy/*.service.in`, `*.timer.in` | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] |
| `bridge/*.md`, `bridge/CONTRACT.v0.json` | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] | [REQUIRED] |

Confirm whether copied/adapted snippets, generated files, model-generated material, icons, fonts, certificates, voice/TTS models or other assets are distributed. If none, identify the inspected paths/manifests and the reviewer; do not make an unsupported blanket assertion.

## D. Authorized package maintainer contact

- Maintainer display name: **[REQUIRED]**
- Operational email address: **[REQUIRED]**
- Confirmation method (reply from that address or other verifiable authorization): **[REQUIRED]**
- Confirmation date: **[REQUIRED]**

The current `Louksna Project <maintainers@louksna.invalid>` value is a HOLD marker, not an operational contact. The address in Git commit metadata is only a lead and must not be substituted without explicit confirmation.

## E. Approval and evidence

- Signed/approved by: **[REQUIRED]**
- Date (UTC): **[REQUIRED]**
- Evidence URL or immutable document reference: **[REQUIRED]**
- SHA-256 of the signed declaration, if stored as a file: **[REQUIRED FOR EVIDENCE RECORD]**
- Independent reviewer and result: **[REQUIRED BEFORE RELEASE]**

## Completion gate

Only after sections A–E are supported by evidence may maintainers prepare `debian/copyright` in Debian copyright-format 1.0 (DEP-5), compare every packaged file group against the declaration, run the package build and Lintian, and obtain independent review. A successful build does not itself authorize redistribution. Until then, retain HOLD and do not merge/release on the basis of this template.
