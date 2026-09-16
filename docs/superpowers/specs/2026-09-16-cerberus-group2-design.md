# UNG-CERBERUS Group 2 — Biometric Gateway & Operator Casework Design

Date: 2026-09-16
Status: Approved design

## Purpose

Group 2 adds a provider-neutral biometric integration layer and expands the CERBERUS operator workspace. It does not turn biometric similarity into an automatic immigration or watchlist decision. Consequential outcomes remain authorized human decisions with provenance and audit.

## Architecture

CERBERUS owns biometric workflow authorization, transaction metadata, case linkage, review state, and audit. Specialized biometric providers remain behind adapters. Raw captures and provider-native templates are not ordinary Person fields and are not exposed through general identity APIs.

The gateway supports three modalities: fingerprint, face, and iris. Provider adapters expose enrollment, 1:1 verification, and explicitly authorized 1:N identification capabilities. A provider may support only a subset of those operations.

## Components

### Biometric Enrollment

An enrollment binds a person to a protected provider reference and records modality, provider, capture device reference, operator reference, purpose/legal-authority reference, provenance, status, and timestamps. CERBERUS stores the minimum reference material needed to address the provider; it does not place raw biometric images in the identity registry.

### 1:1 Verification

Verification compares an authorized presented sample through the provider adapter against one enrolled reference for a known person. CERBERUS records the provider result, transaction reference, modality, operator/device, purpose, and review status. Provider similarity or match output is evidence, not an immigration/watchlist decision.

### Controlled 1:N Identification

Identification is a separately authorized operation. Requests require a documented purpose and authorization reference. Returned candidates are stored as candidates only. A candidate never becomes confirmed identity solely because a provider returned it. Consequential use requires human review.

### Human Review and Casework

Operators can inspect the linked person/case, enrollment provenance, biometric transaction, provider result, and candidate evidence. Review dispositions preserve the original evidence and reviewer/reason. Existing CERBERUS watchlist adjudication remains separate from biometric identity review so one does not silently confirm the other.

### Operator Workspace

The responsive workspace adds Biometric Enrollment, Verification, Identification, Case Review, Match History, and Audit views alongside Group 1 areas. It exposes workflow state and provenance without displaying raw biometric material by default.

## Data Boundaries

Biometric references are segregated from ordinary identity fields. Provider credentials, cryptographic keys, raw captures, and production biometric templates must not be committed to the repository. The repository contains adapters/interfaces, synthetic test fixtures, and configuration examples only.

Every biometric transaction records purpose, actor/operator, provider, modality, device reference when available, correlation/transaction reference, timestamp, and provenance/authorization reference.

## Data Flow

Enrollment: Authorized operator -> CERBERUS authorization/purpose check -> provider adapter -> protected provider reference -> CERBERUS enrollment metadata + audit.

Verification: Known person + authorized sample -> 1:1 provider operation -> evidence/result -> CERBERUS transaction -> human/case workflow where consequential.

Identification: Authorized sample + explicit 1:N authority -> provider operation -> candidate set -> CERBERUS candidate records -> human review -> reviewed disposition.

## Integration Boundaries

JANUS is the future identity/RBAC/MFA authority; VAULT is the future cryptographic/key-protection boundary; NEXUS is the controlled external-system integration boundary; PULSAR is the governed event/data transport boundary. Group 2 must remain testable with local stub adapters when those systems are offline.

KINSHIP remains isolated and is not a biometric screening source.

## Failure Handling

Provider timeout/unavailability produces an explicit failed or unavailable transaction, never a guessed result. Unsupported modality/operation is rejected. Missing purpose/authorization for 1:N is rejected. Cross-person enrollment/reference misuse is rejected. Provider errors are recorded without leaking secrets or raw biometric payloads into logs.

## Testing and Acceptance

Group 2 tests use synthetic references only. Acceptance requires: fingerprint/face/iris enrollment metadata; provider-neutral adapter contract; controlled 1:1 verification; separately authorized 1:N identification; candidate-not-confirmed invariant; human review; transaction/audit metadata; provider failure behavior; no raw biometric payload in general identity responses; and responsive operator workspace markers for enrollment, verification, identification, case review, match history, and audit.

## Explicit Non-Goals

Group 2 does not implement covert biometric collection, autonomous adverse decisions, predictive risk scoring, raw biometric repositories in Git, destructive security controls, or KINSHIP-derived screening.