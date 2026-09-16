from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def now_utc(): return datetime.now(timezone.utc)

class Person(Base):
    __tablename__='people'
    id: Mapped[int]=mapped_column(primary_key=True); person_code: Mapped[str]=mapped_column(String(40),unique=True,index=True)
    primary_name: Mapped[str]=mapped_column(String(200)); date_of_birth: Mapped[date|None]=mapped_column(Date,nullable=True)
    nationality: Mapped[str|None]=mapped_column(String(3),nullable=True); citizenship: Mapped[str|None]=mapped_column(String(3),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default='active'); source_authority: Mapped[str]=mapped_column(String(120))
    provenance_reference: Mapped[str|None]=mapped_column(String(200),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)
    aliases: Mapped[list['PersonAlias']]=relationship(cascade='all, delete-orphan')
class PersonAlias(Base):
    __tablename__='person_aliases'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True)
    name: Mapped[str]=mapped_column(String(200)); alias_type: Mapped[str]=mapped_column(String(40),default='known_as'); source_authority: Mapped[str]=mapped_column(String(120)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)
class TravelDocument(Base):
    __tablename__='travel_documents'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True)
    document_type: Mapped[str]=mapped_column(String(40)); document_number: Mapped[str]=mapped_column(String(100),index=True); issuing_jurisdiction: Mapped[str]=mapped_column(String(8)); issued_on: Mapped[date|None]=mapped_column(Date,nullable=True); expires_on: Mapped[date|None]=mapped_column(Date,nullable=True); status: Mapped[str]=mapped_column(String(30),default='active'); verification_provenance: Mapped[str|None]=mapped_column(String(200),nullable=True)
class ImmigrationCase(Base):
    __tablename__='immigration_cases'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True); case_type: Mapped[str]=mapped_column(String(80)); jurisdiction: Mapped[str]=mapped_column(String(8)); status: Mapped[str]=mapped_column(String(30),default='open'); assigned_unit: Mapped[str|None]=mapped_column(String(120),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc); history: Mapped[list['CaseStatusHistory']]=relationship(cascade='all, delete-orphan')
class CaseStatusHistory(Base):
    __tablename__='case_status_history'; id: Mapped[int]=mapped_column(primary_key=True); case_id: Mapped[int]=mapped_column(ForeignKey('immigration_cases.id'),index=True); status: Mapped[str]=mapped_column(String(30)); actor_ref: Mapped[str]=mapped_column(String(120)); reason: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)
class BorderEvent(Base):
    __tablename__='border_events'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True); passport_verification_id: Mapped[int|None]=mapped_column(ForeignKey('passport_verifications.id'), unique=True, nullable=True, index=True); direction: Mapped[str]=mapped_column(String(10)); port_code: Mapped[str]=mapped_column(String(20)); country_code: Mapped[str]=mapped_column(String(3)); occurred_at: Mapped[datetime]=mapped_column(DateTime(timezone=True)); source_authority: Mapped[str]=mapped_column(String(120)); provenance_reference: Mapped[str]=mapped_column(String(200))
class WatchlistEntry(Base):
    __tablename__='watchlist_entries'; id: Mapped[int]=mapped_column(primary_key=True); subject_name: Mapped[str]=mapped_column(String(200),index=True); date_of_birth: Mapped[date|None]=mapped_column(Date,nullable=True); originating_authority: Mapped[str]=mapped_column(String(120)); reason_category: Mapped[str]=mapped_column(String(80)); legal_authority_reference: Mapped[str]=mapped_column(String(200)); valid_until: Mapped[date]=mapped_column(Date); provenance_reference: Mapped[str]=mapped_column(String(200)); status: Mapped[str]=mapped_column(String(30),default='active'); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)
class ScreeningEvent(Base):
    __tablename__='screening_events'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True); purpose: Mapped[str]=mapped_column(String(80)); actor_ref: Mapped[str]=mapped_column(String(120)); decision: Mapped[str]=mapped_column(String(30)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc); matches: Mapped[list['CandidateMatch']]=relationship(cascade='all, delete-orphan'); adjudications: Mapped[list['Adjudication']]=relationship(cascade='all, delete-orphan')
class CandidateMatch(Base):
    __tablename__='candidate_matches'; id: Mapped[int]=mapped_column(primary_key=True); screening_id: Mapped[int]=mapped_column(ForeignKey('screening_events.id'),index=True); watchlist_entry_id: Mapped[int]=mapped_column(ForeignKey('watchlist_entries.id')); confidence: Mapped[float]=mapped_column(Float); confirmed_identity: Mapped[bool]=mapped_column(Boolean,default=False); rationale: Mapped[str]=mapped_column(Text)
class Adjudication(Base):
    __tablename__='adjudications'; id: Mapped[int]=mapped_column(primary_key=True); screening_id: Mapped[int]=mapped_column(ForeignKey('screening_events.id'),index=True); outcome: Mapped[str]=mapped_column(String(30)); actor_ref: Mapped[str]=mapped_column(String(120)); reason: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)

class BiometricReference(Base):
    __tablename__='biometric_references'; id: Mapped[int]=mapped_column(primary_key=True); person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True); modality: Mapped[str]=mapped_column(String(20)); provider: Mapped[str]=mapped_column(String(80)); provider_reference: Mapped[str]=mapped_column(String(200),unique=True); status: Mapped[str]=mapped_column(String(30),default='active'); enrolled_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc); expires_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); source_authority: Mapped[str]=mapped_column(String(120)); device_reference: Mapped[str|None]=mapped_column(String(120),nullable=True); purpose: Mapped[str]=mapped_column(String(120)); provenance_reference: Mapped[str]=mapped_column(String(200))
class BiometricTransaction(Base):
    __tablename__='biometric_transactions'; id: Mapped[int]=mapped_column(primary_key=True); transaction_code: Mapped[str]=mapped_column(String(60),unique=True,index=True); operation: Mapped[str]=mapped_column(String(20)); person_id: Mapped[int|None]=mapped_column(ForeignKey('people.id'),nullable=True,index=True); modality: Mapped[str]=mapped_column(String(20)); provider: Mapped[str]=mapped_column(String(80)); operator_ref: Mapped[str]=mapped_column(String(120)); device_reference: Mapped[str|None]=mapped_column(String(120),nullable=True); purpose: Mapped[str]=mapped_column(String(120)); result_status: Mapped[str]=mapped_column(String(30)); correlation_id: Mapped[str]=mapped_column(String(80),index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)
class BiometricCandidate(Base):
    __tablename__='biometric_candidates'; id: Mapped[int]=mapped_column(primary_key=True); transaction_id: Mapped[int]=mapped_column(ForeignKey('biometric_transactions.id'),index=True); candidate_person_id: Mapped[int]=mapped_column(ForeignKey('people.id'),index=True); provider_score: Mapped[float]=mapped_column(Float); candidate_status: Mapped[str]=mapped_column(String(30),default='candidate'); rationale: Mapped[str]=mapped_column(Text)
class BiometricDisposition(Base):
    __tablename__='biometric_dispositions'; id: Mapped[int]=mapped_column(primary_key=True); transaction_id: Mapped[int]=mapped_column(ForeignKey('biometric_transactions.id'),index=True); outcome: Mapped[str]=mapped_column(String(30)); reviewer_ref: Mapped[str]=mapped_column(String(120)); reason: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now_utc)


class PassportVerification(Base):
    """Result metadata only: never a capture, passport session, or template."""
    __tablename__ = 'passport_verifications'
    review: Mapped['PassportReview | None'] = relationship(uselist=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id'), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('travel_documents.id'), index=True)
    modality: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(80))
    synthetic: Mapped[bool] = mapped_column(Boolean)
    operator_ref: Mapped[str] = mapped_column(String(120), index=True)
    device_reference: Mapped[str] = mapped_column(String(120))
    purpose: Mapped[str] = mapped_column(String(80), default='border_identity_verification')
    authorization_reference: Mapped[str] = mapped_column(String(200))
    provenance_reference: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    comparison: Mapped[str] = mapped_column(String(30))
    passport_authenticated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    presentation_live: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), default='pending_officer_review')
    correlation_id: Mapped[str] = mapped_column(String(36), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class PassportReview(Base):
    """One final review per check; original provider evidence remains untouched."""
    __tablename__ = 'passport_reviews'
    id: Mapped[int] = mapped_column(primary_key=True)
    verification_id: Mapped[int] = mapped_column(ForeignKey('passport_verifications.id'), unique=True)
    reviewer_ref: Mapped[str] = mapped_column(String(120))
    outcome: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(1000))
    source_comparison: Mapped[str] = mapped_column(String(30))
    synthetic: Mapped[bool] = mapped_column(Boolean)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    """Append-only operational metadata; never stores raw biometric material or capture handles."""
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(index=True)
    actor_ref: Mapped[str] = mapped_column(String(120), index=True)
    purpose: Mapped[str] = mapped_column(String(120))
    outcome: Mapped[str] = mapped_column(String(80))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


@event.listens_for(AuditEvent, 'before_update')
def _audit_event_is_append_only(mapper, connection, target):
    raise ValueError('Audit events are append-only')


@event.listens_for(AuditEvent, 'before_delete')
def _audit_event_cannot_be_deleted(mapper, connection, target):
    raise ValueError('Audit events are append-only')
