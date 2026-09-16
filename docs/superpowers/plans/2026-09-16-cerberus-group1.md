# CERBERUS Group 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable CERBERUS Group 1 service for identity registry, travel documents, immigration cases, border events, authorized watchlists, candidate screening, human disposition, and append-oriented audit/provenance.

**Architecture:** FastAPI exposes versioned REST endpoints over SQLAlchemy models in PostgreSQL, with SQLite allowed only for isolated tests. Domain services enforce the key invariant that candidate matches never auto-confirm identity and that consequential matches require human disposition. Integration adapters for JANUS, NEXUS, PULSAR and VAULT are interfaces/stubs in Group 1, keeping the core independently testable.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL/psycopg, Pydantic 2.x, pytest, httpx, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-ung-cerberus-design.md`

## Global Constraints
- Candidate match != confirmed identity.
- Consequential watchlist matches require human adjudication.
- Every watchlist record has source authority, validity and provenance.
- Access is least-privilege and purpose-bound.
- Biometric data is segregated from ordinary identity records.
- Destructive security actions cannot be single-operator shortcuts.
- Material actions are auditable and correlation IDs connect cross-system events.
- Jurisdiction-specific policy is configurable; Uganda is the first operational profile.
- KINSHIP data is not automatically consumed for screening.

---

## File structure
- `app/main.py` — FastAPI composition and health endpoint.
- `app/db.py` — SQLAlchemy engine/session/base.
- `app/models.py` — Group 1 persistence models.
- `app/schemas.py` — request/response schemas.
- `app/audit.py` — append-oriented audit writer.
- `app/identity.py` — person and alias registration/retrieval.
- `app/documents.py` — travel-document registration.
- `app/cases.py` — immigration case workflow and status history.
- `app/border.py` — entry/exit event recording.
- `app/watchlists.py` — authorized watchlist lifecycle.
- `app/screening.py` — candidate matching and human disposition.
- `app/integrations.py` — JANUS/NEXUS/PULSAR/VAULT adapter protocols.
- `app/routers/*.py` — versioned HTTP route modules.
- `config/uganda.json` — first jurisdiction profile.
- `tests/` — focused domain/API acceptance tests.
- `.github/workflows/ci.yml` — automated tests.

### Task 1: Service foundation and persistence

**Files:** Create `requirements.txt`, `app/__init__.py`, `app/db.py`, `app/main.py`, `tests/test_health.py`, `.github/workflows/ci.yml`.

**Interfaces:** Produces `Base`, `SessionLocal`, `get_db()` and FastAPI `app` used by all later tasks.

- [ ] Write `tests/test_health.py` asserting `GET /health` returns `{"status":"ok","system":"UNG-CERBERUS"}`.
- [ ] Run `pytest tests/test_health.py -v`; expect failure because `app.main` does not exist.
- [ ] Implement SQLAlchemy database setup and FastAPI `/health`; dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg[binary]`, `pydantic`, `pytest`, `httpx`.
- [ ] Run `pytest tests/test_health.py -v`; expect PASS.
- [ ] Add CI with Python 3.12, `PYTHONPATH=.`, test `DATABASE_URL=sqlite:///./cerberus-test.db`, install requirements, run `pytest -q`.
- [ ] Commit `feat: bootstrap CERBERUS service`.

### Task 2: Identity registry and aliases

**Files:** Create `app/models.py`, `app/schemas.py`, `app/identity.py`, `app/routers/identity.py`, `tests/test_identity.py`; modify `app/main.py`.

**Interfaces:** Produces `Person`, `PersonAlias`, `create_person(db, data, correlation_id)`, `get_person(db, person_id)` and `/v1/people` APIs.

- [ ] Write tests proving a person receives a stable `CER-P-########` identifier, aliases remain attached to the same person, provenance is stored, and retrieval does not create a second identity.
- [ ] Run `pytest tests/test_identity.py -v`; expect import/route failures.
- [ ] Implement `Person` fields: id, person_code, primary_name, date_of_birth, nationality, citizenship, status, source_authority, provenance_reference, created_at; implement `PersonAlias` with person_id, name, alias_type, source_authority, created_at.
- [ ] Implement `POST /v1/people`, `GET /v1/people/{person_id}` and `POST /v1/people/{person_id}/aliases`.
- [ ] Run identity tests; expect PASS.
- [ ] Commit `feat: add identity registry`.

### Task 3: Travel documents

**Files:** Create `app/documents.py`, `app/routers/documents.py`, `tests/test_documents.py`; modify `app/models.py`, `app/schemas.py`, `app/main.py`.

**Interfaces:** Produces `TravelDocument`, `register_document(db, person_id, data, correlation_id)` and `/v1/people/{person_id}/documents`.

- [ ] Write tests proving a passport is associated with exactly one registered person and stores type, number, issuing jurisdiction, issue date, expiry date, status and verification provenance.
- [ ] Run document tests; expect failure.
- [ ] Implement `TravelDocument` and registration/retrieval APIs; reject missing people and duplicate active issuer+document-number combinations.
- [ ] Run document tests; expect PASS.
- [ ] Commit `feat: add travel document registry`.

### Task 4: Immigration case workflow

**Files:** Create `app/cases.py`, `app/routers/cases.py`, `tests/test_cases.py`; modify `app/models.py`, `app/schemas.py`, `app/main.py`.

**Interfaces:** Produces `ImmigrationCase`, `CaseStatusHistory`, `open_case(...)`, `transition_case(...)`, `/v1/cases`.

- [ ] Write tests opening a case and transitioning `open -> under_review -> decided`, asserting actor/reference, reason and timestamps are retained in history.
- [ ] Run case tests; expect failure.
- [ ] Implement case and immutable status-history models plus POST/open, GET and transition endpoints; reject unsupported transitions.
- [ ] Run case tests; expect PASS.
- [ ] Commit `feat: add immigration case workflow`.

### Task 5: Border entry and exit events

**Files:** Create `app/border.py`, `app/routers/border.py`, `tests/test_border.py`; modify `app/models.py`, `app/schemas.py`, `app/main.py`, create `config/uganda.json`.

**Interfaces:** Produces `BorderEvent`, `record_border_event(...)`, `/v1/border-events`; Uganda profile contains configured jurisdiction code and initial port identifiers without hard-coding policy into domain logic.

- [ ] Write tests recording ENTRY and EXIT with person, document, port, event time, inspection status and provenance; reject a document belonging to another person.
- [ ] Run border tests; expect failure.
- [ ] Implement border event model/service/API and load `config/uganda.json` through configuration rather than domain constants.
- [ ] Run border tests; expect PASS.
- [ ] Commit `feat: add border event registry`.

### Task 6: Authorized watchlist management

**Files:** Create `app/watchlists.py`, `app/routers/watchlists.py`, `tests/test_watchlists.py`; modify `app/models.py`, `app/schemas.py`, `app/main.py`.

**Interfaces:** Produces `WatchlistRecord`, `create_watchlist_record(...)`, `active_watchlist_records(db, at_time)` and `/v1/watchlists`.

- [ ] Write tests requiring stable record ID, source authority, category, reason/reference, valid-from/valid-until, status, identifying attributes, review state and provenance.
- [ ] Write tests proving expired/inactive records are excluded from active screening input while remaining retrievable for audit/history.
- [ ] Run watchlist tests; expect failure.
- [ ] Implement watchlist model/service/API with explicit validation that source authority and reason/reference cannot be blank.
- [ ] Run watchlist tests; expect PASS.
- [ ] Commit `feat: add governed watchlist registry`.

### Task 7: Candidate screening without automatic confirmation

**Files:** Create `app/screening.py`, `app/routers/screening.py`, `tests/test_screening.py`; modify `app/models.py`, `app/schemas.py`, `app/main.py`.

**Interfaces:** Produces `Screening`, `CandidateMatch`, `screen_person(db, person_id, document_id, correlation_id)` and `POST /v1/screenings`.

- [ ] Write tests for exact normalized document-number and biographic candidate matching against active records, asserting every result has status `candidate` and never `confirmed`.
- [ ] Write a zero-match test returning a completed screening with an empty candidates array.
- [ ] Run screening tests; expect failure.
- [ ] Implement deterministic V1 candidate rules with match reasons stored per candidate; do not implement predictive risk scoring.
- [ ] Run screening tests; expect PASS.
- [ ] Commit `feat: add candidate watchlist screening`.

### Task 8: Human review and disposition

**Files:** Modify `app/screening.py`, `app/routers/screening.py`, `app/models.py`, `app/schemas.py`; create `tests/test_disposition.py`.

**Interfaces:** Produces `ScreeningDisposition`, `dispose_candidate(db, candidate_id, outcome, reviewer_ref, reason, correlation_id)` and `POST /v1/screenings/{screening_id}/candidates/{candidate_id}/disposition`.

- [ ] Write tests that candidate status cannot become confirmed/escalated without reviewer reference and reason; allowed outcomes are `cleared`, `confirmed`, `escalated`.
- [ ] Write test preserving the original candidate evidence after disposition.
- [ ] Run disposition tests; expect failure.
- [ ] Implement append-only disposition records and derive current candidate disposition without overwriting match evidence.
- [ ] Run disposition tests; expect PASS.
- [ ] Commit `feat: require human screening disposition`.

### Task 9: Audit, correlation and integration boundaries

**Files:** Create `app/audit.py`, `app/integrations.py`, `tests/test_audit.py`, `tests/test_integrations.py`; modify Group 1 services to call audit writer.

**Interfaces:** Produces `AuditEvent`, `write_audit(db, actor_ref, action, target_type, target_id, correlation_id, provenance)` and Protocols `JanusAdapter`, `NexusAdapter`, `PulsarAdapter`, `VaultAdapter`.

- [ ] Write tests asserting material create/screen/disposition workflows emit audit events sharing the supplied correlation ID.
- [ ] Write tests proving the four adapter protocols can be replaced with test doubles and Group 1 works with no external UNG service online.
- [ ] Run audit/integration tests; expect failure.
- [ ] Implement append-oriented audit writer and narrow adapter protocols; wire service calls without network implementations.
- [ ] Run audit/integration tests; expect PASS.
- [ ] Commit `feat: add audit and UNG integration boundaries`.

### Task 10: Group 1 acceptance suite

**Files:** Create `tests/test_group1_acceptance.py`, `README.md`; modify `.github/workflows/ci.yml` if needed.

**Interfaces:** Consumes all Group 1 APIs; produces end-to-end acceptance evidence.

- [ ] Write an acceptance test that registers a person and alias, registers a passport, opens a case, records an ENTRY, creates an authorized active watchlist record, runs screening, receives a candidate (not confirmed), records human disposition, and verifies correlated audit events.
- [ ] Write a second acceptance test proving an expired watchlist entry produces no active candidate.
- [ ] Run `pytest -q`; expect all tests PASS.
- [ ] Add README commands `pip install -r requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port 8080`, and `pytest -q`, plus the Group 1 safety invariants.
- [ ] Run `pytest -q` again and verify a clean pass before any completion claim.
- [ ] Commit `test: complete CERBERUS Group 1 acceptance`.

## Self-review
- Spec coverage: all ten Group 1 acceptance criteria are mapped to Tasks 2-10; future biometric/classified functions remain outside Group 1 implementation.
- Placeholder scan: no implementation placeholders are required to execute Group 1.
- Type/interface consistency: person -> document -> border/screening relationships and correlation IDs are defined before dependent tasks; candidate disposition remains separate from candidate evidence.
