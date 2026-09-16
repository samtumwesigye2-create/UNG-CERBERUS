from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


def now_utc():
    return datetime.now(timezone.utc)

class Person(Base):
    __tablename__ = 'people'
    id: Mapped[int] = mapped_column(primary_key=True)
    person_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    primary_name: Mapped[str] = mapped_column(String(200))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(3), nullable=True)
    citizenship: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='active')
    source_authority: Mapped[str] = mapped_column(String(120))
    provenance_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    aliases: Mapped[list['PersonAlias']] = relationship(cascade='all, delete-orphan')

class PersonAlias(Base):
    __tablename__ = 'person_aliases'
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id'), index=True)
    name: Mapped[str] = mapped_column(String(200))
    alias_type: Mapped[str] = mapped_column(String(40), default='known_as')
    source_authority: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

class TravelDocument(Base):
    __tablename__ = 'travel_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id'), index=True)
    document_type: Mapped[str] = mapped_column(String(40))
    document_number: Mapped[str] = mapped_column(String(100), index=True)
    issuing_jurisdiction: Mapped[str] = mapped_column(String(8))
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='active')
    verification_provenance: Mapped[str | None] = mapped_column(String(200), nullable=True)

class ImmigrationCase(Base):
    __tablename__ = 'immigration_cases'
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('people.id'), index=True)
    case_type: Mapped[str] = mapped_column(String(80))
    jurisdiction: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(30), default='open')
    assigned_unit: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    history: Mapped[list['CaseStatusHistory']] = relationship(cascade='all, delete-orphan')

class CaseStatusHistory(Base):
    __tablename__ = 'case_status_history'
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('immigration_cases.id'), index=True)
    status: Mapped[str] = mapped_column(String(30))
    actor_ref: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
