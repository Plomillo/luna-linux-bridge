# ECOSYSTEM CONTRACT — V1

## 1. Authority topology

`Louksna.md` remains sole canonical architectural authority. This package is subordinate operational infrastructure. MetaOS governs execution policy; CUSTOSZ V7 is the worker when a CUSTOSZ mission is assigned; CUSTOSZ_RUNTIME_V1 provides runtime services; PUAC2 is assurance machinery; GitHub is execution/evidence infrastructure; G23 and G24 remain distinct validation/certification stages.

No subordinate component may:
- create canonical identity;
- redefine Louksna;
- self-certify;
- silently substitute another component;
- silently change an executor or runtime binding;
- convert a technical PASS into authority.

## 2. Mandatory federation interface

Every component adapter SHALL expose:
`COMPONENT_ID, VERSION, ROLE, AUTHORITY_LEVEL, INPUT_CONTRACT, OUTPUT_CONTRACT, DEPENDENCIES, SECURITY_BOUNDARY, RESOURCE_BOUNDARY, EVIDENCE_SCHEMA, FAILURE_STATES, ROLLBACK, COMPATIBILITY_RANGE`.

A future canonical architecture is admitted by adding a new versioned adapter. Existing adapters are never silently overwritten.

## 3. State machine

```text
DECLARED
 -> EVIDENCED
 -> VALIDATED
 -> INDEPENDENTLY_VALIDATED
 -> CERTIFIED
 -> ACTIVE
```

Forbidden: `DECLARED->CERTIFIED`, `EVIDENCED->CERTIFIED`, `VALIDATED->CERTIFIED_WITHOUT_G23`, and any `ACTIVE` transition without a complete evidence chain.

## 4. Execution/data separation

Control plane: GitHub repository + workflows + manifests + small evidence.  
Compute plane: GitHub-hosted runners by default; external cloud compute only through explicit adapters.  
Data plane: remote object stores, datasets, streams and databases.  
User host: no heavy corpus/model/translation workload by default.

`REMOTE_DESKTOP_COMMANDER` is auxiliary observation/transport only and must never substitute CUSTOSZ.

## 5. NetKaizen

```text
OBSERVE
 -> FIND_GAP
 -> CAPABILITY_GRAPH_DUPLICATE_CHECK
 -> PROPOSE
 -> SHADOW_SIMULATE
 -> VALIDATE
 -> G23
 -> G24
 -> ACTIVATE
 -> MONITOR_VALIDITY
```

A proposal that cannot show distinct inputs/outputs/failure modes is rejected as decorative or duplicative.
