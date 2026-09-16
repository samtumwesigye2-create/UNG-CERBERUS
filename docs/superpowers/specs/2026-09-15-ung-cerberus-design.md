# UNG-CERBERUS Architecture Specification

## Name
UNG-CERBERUS — Centralized Entry, Risk & Biometric Evaluation, Registration & Unified Screening.

## Purpose
CERBERUS is a country-neutral identity, immigration, border-screening, biometric-integration, and protected-information platform. Its first configuration targets Uganda while keeping jurisdiction-specific rules outside the reusable core.

## System boundaries
CERBERUS owns identity and travel-document records, immigration cases, border entry/exit events, authorized watchlist records, screening cases, human review/disposition, biometric references and transaction metadata, and CERBERUS audit/provenance records.

CERBERUS does not duplicate portfolio infrastructure. JANUS provides identity/access integration; NEXUS provides controlled interoperability; PULSAR provides governed event/data transport; VAULT provides cryptographic/key-protection integration. KINSHIP remains isolated and family relationships are not silently used as watchlist or immigration evidence.

## Group 1: Identity, immigration and screening

### Identity Registry
Maintain a durable person identity with aliases, citizenship/nationality attributes, birth data, identity-document references, source/provenance and record status. Corrections are auditable rather than silently overwriting material history.

### Travel Documents
Register passports and other configured travel-document types, issuing jurisdiction, document number, issue/expiry dates, status and verification metadata. Document identifiers are treated as sensitive data.

### Immigration Cases
Represent applications, referrals and immigration casework with case type, jurisdiction, status, assigned unit/operator reference, decisions, timestamps and provenance.

### Entry/Exit Events
Record port/border events with person, document, direction, port, timestamp, carrier/journey metadata where authorized, inspection status and provenance.

### Watchlist Management
Each authorized watchlist record carries a stable record ID, source authority, category, reason/reference, validity dates, status, identifying attributes, review state and provenance. A watchlist record is not itself proof that a screened traveler is the same person.

### Screening and Human Review
Screening creates candidate matches using authorized biographic/document attributes. A candidate match remains distinct from a confirmed identity. Consequential dispositions require human review. Review outcomes include cleared, confirmed and escalated, with reviewer identity/reference, reasons and timestamps preserved.

### Audit and Provenance
Material reads/writes, screening actions, review decisions, exports, integration events and security-control actions generate append-oriented audit events. Audit records include actor/reference, action, target, timestamp, correlation ID and relevant provenance.

## Group 2: Biometrics and operator casework
Biometric services are isolated behind a gateway supporting appropriately authorized enrollment, 1:1 verification and 1:N identification. Raw biometric material should be minimized; protected templates/references are segregated from ordinary identity records. Transactions retain modality, device/system provenance, authorization purpose, result metadata and audit correlation. Operator interfaces expose only data allowed by role, purpose and compartment.

## Group 3: Classified-information protection and containment
Protected information supports classification/compartment labels, need-to-know authorization, controlled export and forensic document watermarking tied to an authorized copy/session/issuance event. Watermarks support later attribution of a controlled copy without exposing unnecessary sensitive information in visible markings.

Emergency security controls use scoped containment rather than one unrestricted destructive switch: revoke credentials, terminate sessions, isolate services, suspend integrations, quarantine endpoints, rotate keys and lock protected repositories. Highly destructive actions such as cryptographic erasure require multiple authorized approvers, explicit scope, retention/legal validation, tamper-evident audit records and tested recovery safeguards.

## Core data flow
Enrollment or border event -> identity resolution -> document and, when authorized, biometric verification -> authorized watchlist screening -> candidate match -> human review when required -> immigration decision/referral -> audit/security event -> controlled downstream distribution.

## Safety and governance invariants
- Candidate match != confirmed identity.
- Consequential watchlist matches require human adjudication.
- Every watchlist record has source authority, validity and provenance.
- Access is least-privilege and purpose-bound.
- Biometric data is segregated from ordinary identity records.
- Destructive security actions cannot be single-operator shortcuts.
- Material actions are auditable and correlation IDs connect cross-system events.
- Jurisdiction-specific policy is configurable; Uganda is the first operational profile.
- KINSHIP data is not automatically consumed for screening.

## Initial technical architecture
Use a service-oriented modular application with a PostgreSQL authoritative store, versioned HTTP/JSON APIs, an append-oriented audit model, and a responsive operator/admin web interface. External portfolio systems are reached through explicit adapters so the CERBERUS core remains testable without those systems being online.

## Acceptance criteria for Group 1
1. Register and retrieve a person without conflating aliases with separate identities.
2. Register a travel document and associate it with the correct person.
3. Open and progress an immigration case with an auditable status history.
4. Record entry and exit events with port and document provenance.
5. Create authorized watchlist records with authority, validity and review metadata.
6. Screen a person/document and produce zero or more candidate matches without auto-confirming identity.
7. Require a human disposition for a consequential candidate match.
8. Preserve cleared/confirmed/escalated decisions with reasons and reviewer reference.
9. Produce audit events and correlation IDs for material workflows.
10. Demonstrate strict module boundaries for future JANUS, NEXUS, PULSAR and VAULT adapters.