# UNG-CERBERUS

CERBERUS is a border entry/exit workflow prototype. The current biometric scope is **one traveler presenting at a border compared with the biometric in that traveler's presented passport**. The user superseded the earlier enrollment and registry identification plan on 2026-09-16.

## Passport verification

- `POST /v1/passport-verifications` checks one registered passport belonging to one claimed person and records comparison evidence for officer review.
- `GET /v1/passport-verifications/{id}` returns result metadata to the same authenticated operator.
- `POST /v1/passport-verifications/{id}/review` records an officer review (`consistent`, `inconsistent`, or `inconclusive`) with a required reason. It preserves the original evidence, prevents conflicting outcomes, and never admits or denies a traveler by itself.
- Both endpoints require a server-configured bearer token and operator identity. Missing configuration fails closed. The request cannot select a provider or impersonate another operator.
- The passport must be active, unexpired, and associated with the claimed person. Missing expiry or a future issue date blocks verification.
- A trusted provider must authenticate the presented passport and verify document number/issuer binding and live presentation before a comparison is usable. Authentication/liveness failure gives `inconclusive`, regardless of a claimed match.
- Results stay `pending_officer_review`; they do not change immigration cases, border events, watchlist screening, or identity dispositions.
- The route stores metadata, correlation ID, time, operator, device, purpose, authorization/provenance references, and outcome. Capture/session handles, raw samples, passport images, and biometric templates are not persisted or returned. Validation and provider errors omit input payloads and exception text.
- Enrollment and registry-search routes are absent. The previous unused biometric model/adapter scaffolding remains for migration compatibility; the passport route never invokes it or creates its reference/candidate records.

### Runtime modes

**Default:** no trusted provider is installed. An authenticated valid request creates an `inconclusive` / `provider_unavailable` record and returns HTTP 503. Other provider exceptions or malformed evidence produce a retrievable `failed` record and HTTP 502. No outcome is guessed.

**Explicit synthetic demo:** set `CERBERUS_PASSPORT_PROVIDER=synthetic`. Every result is marked `synthetic: true` and names `synthetic-passport-demo`. This is deterministic fixture logic, not facial/fingerprint/iris recognition and not passport authenticity validation.

Demo fixture:

- Document number `SYNTH-PASSPORT-001`, issuing jurisdiction `TEST`, document type `passport`, active with a future expiry.
- Passport session `synthetic://passport/face/demo-001`.
- Traveler sample `synthetic://traveler/face/demo-001` produces a simulated match.
- Traveler sample `synthetic://traveler/face/demo-other` produces a simulated non-match.
- Unknown sample/session handles give an inconclusive result. Replace `face` consistently with `fingerprint` or `iris` for synthetic interface tests only. Real passport modality availability must be determined by the reader/provider; support is not implied by the demo.

### Local startup

Use Python 3.12 in a virtual environment, then:

```sh
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./cerberus-local.db
export CERBERUS_PASSPORT_OPERATOR=demo-officer
export CERBERUS_PASSPORT_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CERBERUS_PASSPORT_PROVIDER=synthetic
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep generated tokens secret and out of source control. `/docs` describes the API. Register a **synthetic** person and the demo passport through the existing person/document APIs, then use their IDs in this request with `Authorization: Bearer <your token>`:

```json
{
  "person_id": 1,
  "document_id": 1,
  "modality": "face",
  "passport_session_reference": "synthetic://passport/face/demo-001",
  "traveler_sample_reference": "synthetic://traveler/face/demo-001",
  "device_reference": "demo-reader",
  "authorization_reference": "DEMO-AUTH-001",
  "provenance_reference": "DEMO-CHECK-001"
}
```

Use actual returned IDs rather than assuming 1. Never paste real samples, templates, passport details, or production credentials into this public repository or the demo.

### Tests

```sh
DATABASE_URL=sqlite:///./cerberus-test.db python -m pytest -q
```

The passport tests use isolated in-memory databases. Existing Group 1 tests assume a fresh test database. Tests exercise match/non-match/inconclusive behavior; server authentication; document binding; invalid input; provider failure; result persistence; protected reads; and no biometric enrollment, registry search, or capture persistence.

## Live integration boundary

This change is an API workflow, **not a deployed or certified border biometric system**. A real trusted passport reader/matcher adapter is not installed. Its implementation must satisfy `PassportProvider.verify_presented_passport` in `app/passport_provider.py`, authenticate the chip/document evidence, resolve short-lived handles in a trusted capture service, bind sessions to the document, device and authenticated operator, enforce anti-replay/freshness and liveness, and report unsupported/unavailable evidence explicitly. References are opaque; the application must not fetch arbitrary caller-supplied URLs. Only trusted server configuration can register an adapter through `get_passport_provider`.

The single configured operator token is a prototype authentication boundary for the passport endpoints, not JANUS/RBAC/MFA integration. Earlier Group 1 APIs remain unauthenticated and the static workspace has no new passport capture controls. Do not expose this prototype to real traveler data. Production deployment needs system-wide authenticated document/capture provenance, authenticated operators, TLS, provider/device integration, database migration/release controls, and retention/audit policy. These are not claimed as completed by this change.
