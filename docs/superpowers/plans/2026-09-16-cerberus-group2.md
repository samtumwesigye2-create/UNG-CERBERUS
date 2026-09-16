# CERBERUS Group 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a provider-neutral, governed biometric gateway and expanded operator casework workspace using synthetic data and human-reviewed candidate results.

**Architecture:** CERBERUS owns authorization metadata, biometric transaction/reference metadata, review state and audit while provider-specific biometric operations sit behind adapters. Raw biometric material is excluded from ordinary identity APIs and the public repository. Existing Group 1 identity/case/watchlist workflows remain independent.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL/SQLite tests, Pydantic 2.x, pytest/httpx, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-16-cerberus-group2-design.md`

## Global Constraints

- Repository is public: synthetic references only; no real biometric samples, credentials, keys, watchlist subjects or classified integration details.
- Modalities: fingerprint, face, iris.
- Candidate result is never automatically a confirmed identity.
- Consequential results require authorized human review.
- 1:N identification requires explicit purpose and authorization reference.
- No predictive risk scoring.
- Raw biometric captures/provider-native templates are not general Person fields or general identity API output.
- Provider failure returns explicit unavailable/failed state, not a guessed result.

---

### Task 1: Biometric metadata model and provider adapter contract

**Files:**
- Create: `app/biometrics.py`
- Modify: `app/models.py`
- Modify: `app/schemas.py`
- Test: `tests/test_biometric_gateway.py`

**Interfaces:**
- Produces `BiometricProvider` protocol with `enroll`, `verify`, `identify` operations and a deterministic `StubBiometricProvider` for synthetic tests.
- Produces `BiometricReference`, `BiometricTransaction`, `BiometricCandidate`, and `BiometricDisposition` persistence models.

- [ ] Write failing tests asserting fingerprint/face/iris references can be represented, provider capability errors are explicit, and raw sample bytes are not persisted in Person.
- [ ] Run `pytest tests/test_biometric_gateway.py -v`; expect failure because biometric models/provider contract do not exist.
- [ ] Implement the four metadata models and provider protocol/stub. Provider methods accept opaque synthetic sample references, never raw production material.
- [ ] Run the focused tests; expect PASS.
- [ ] Commit with `feat: add biometric gateway metadata and adapter contract`.

### Task 2: Governed biometric enrollment

**Files:**
- Modify: `app/main.py`
- Modify: `app/schemas.py`
- Modify: `app/biometrics.py`
- Test: `tests/test_biometric_enrollment.py`

**Interfaces:**
- Produces `POST /v1/biometrics/enrollments`.
- Requires `person_id`, `modality`, `provider`, `operator_ref`, `device_reference`, `purpose`, `authorization_reference`, and `provenance_reference`.

- [ ] Write a failing API test enrolling a synthetic fingerprint reference and asserting the response exposes metadata/provider reference but no raw capture field.
- [ ] Add negative tests for unsupported modality, missing purpose/authorization, and unknown person.
- [ ] Run focused tests; expect endpoint-not-found/validation failures.
- [ ] Implement enrollment through `StubBiometricProvider`, persist protected reference metadata and transaction/correlation metadata, and reject invalid requests before provider invocation.
- [ ] Run focused tests; expect PASS.
- [ ] Commit with `feat: add governed biometric enrollment`.

### Task 3: 1:1 verification

**Files:**
- Modify: `app/main.py`
- Modify: `app/schemas.py`
- Modify: `app/biometrics.py`
- Test: `tests/test_biometric_verification.py`

**Interfaces:**
- Produces `POST /v1/biometrics/verifications`.
- Verification consumes one active reference belonging to the claimed person and returns provider evidence plus a non-adverse workflow status.

- [ ] Write failing tests for a synthetic matching verification, inactive-reference rejection, and cross-person reference rejection.
- [ ] Run focused tests; expect failure.
- [ ] Implement the minimal 1:1 path, recording provider/modality/operator/device/purpose/provenance/correlation metadata.
- [ ] Ensure provider similarity output remains evidence and does not modify watchlist or immigration case disposition.
- [ ] Run focused tests; expect PASS.
- [ ] Commit with `feat: add biometric one-to-one verification`.

### Task 4: Controlled 1:N identification and human review

**Files:**
- Modify: `app/main.py`
- Modify: `app/schemas.py`
- Modify: `app/biometrics.py`
- Test: `tests/test_biometric_identification.py`

**Interfaces:**
- Produces `POST /v1/biometrics/identifications` and `POST /v1/biometrics/transactions/{transaction_id}/adjudicate`.
- Candidate output contains candidate person/reference, provider score/evidence and `confirmed_identity: false` until disposition.
- Allowed human outcomes: `cleared`, `confirmed`, `escalated`.

- [ ] Write failing tests proving 1:N is rejected without explicit authorization reference and purpose.
- [ ] Write a failing candidate test asserting every provider candidate is non-conclusive and requires review.
- [ ] Write failing adjudication tests requiring reviewer reference and reason and preserving original candidate evidence.
- [ ] Run focused tests; expect failure.
- [ ] Implement controlled identification and append-oriented disposition.
- [ ] Run focused tests; expect PASS.
- [ ] Commit with `feat: add controlled biometric identification review`.

### Task 5: Provider failure and audit/correlation behavior

**Files:**
- Modify: `app/biometrics.py`
- Modify: `app/main.py`
- Create: `app/audit.py`
- Test: `tests/test_biometric_failures_audit.py`

**Interfaces:**
- Produces explicit transaction states `completed`, `failed`, `provider_unavailable`.
- Produces append-oriented audit events keyed by correlation ID without raw biometric payloads.

- [ ] Write failing tests for provider timeout/unavailability and verify no guessed match/no-match is returned.
- [ ] Write failing tests asserting material enrollment/verification/identification/adjudication actions create audit metadata with actor, purpose and correlation ID.
- [ ] Implement provider error translation and audit writer.
- [ ] Run focused tests; expect PASS.
- [ ] Commit with `feat: add biometric failure handling and audit`.

### Task 6: Operator/casework workspace

**Files:**
- Modify: `app/main.py`
- Create: `app/operator_ui.py`
- Test: `tests/test_group2_workspace.py`

**Interfaces:**
- Workspace sections: Biometric Enrollment, Verification, Identification, Case Review, Match History, Audit.
- Candidate screens visibly state that a candidate is not confirmed identity until authorized human review.

- [ ] Write failing responsive workspace tests for all six sections and the candidate-warning text.
- [ ] Run focused tests; expect failure.
- [ ] Move workspace rendering into `app/operator_ui.py` and add the Group 2 panels while preserving Group 1 panels.
- [ ] Run focused tests; expect PASS.
- [ ] Commit with `feat: expand CERBERUS biometric operator workspace`.

### Task 7: Group 2 end-to-end acceptance

**Files:**
- Create: `tests/test_group2_acceptance.py`
- Modify: `README.md`

**Interfaces:**
- Acceptance chain: synthetic person -> biometric enrollment -> 1:1 verification -> authorized 1:N candidate -> human disposition -> audit/correlation evidence.

- [ ] Write the end-to-end acceptance test using only synthetic provider references.
- [ ] Assert general person retrieval contains no raw biometric payload/provider-native template.
- [ ] Assert provider-unavailable path is non-conclusive.
- [ ] Run `pytest -q`; expect all Group 1 and Group 2 tests PASS.
- [ ] Document local startup/test commands and public-repository safety constraints in README.
- [ ] Run `pytest -q` again and verify GitHub Actions CI on the exact head commit.
- [ ] Commit with `test: complete CERBERUS Group 2 acceptance`.
