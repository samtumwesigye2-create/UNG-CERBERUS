from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import Base, engine, get_db
from app.models import Person, PersonAlias, TravelDocument, ImmigrationCase, CaseStatusHistory
from app.schemas import PersonCreate, DocumentCreate, CaseCreate, CaseTransition

# Ensure model metadata is registered and schema exists for direct TestClient use.
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title='UNG-CERBERUS', version='0.2.0', lifespan=lifespan)

@app.get('/health')
def health():
    return {'status': 'ok', 'system': 'UNG-CERBERUS'}

def person_out(p: Person):
    return {'id': p.id, 'person_code': p.person_code, 'primary_name': p.primary_name,
            'date_of_birth': p.date_of_birth, 'nationality': p.nationality,
            'citizenship': p.citizenship, 'status': p.status,
            'source_authority': p.source_authority,
            'provenance_reference': p.provenance_reference,
            'aliases': [a.name for a in p.aliases]}

@app.post('/v1/people', status_code=status.HTTP_201_CREATED)
def create_person(data: PersonCreate, db: Session = Depends(get_db)):
    p = Person(person_code=f'CER-P-{uuid4().hex[:8].upper()}', primary_name=data.primary_name,
               date_of_birth=data.date_of_birth, nationality=data.nationality,
               citizenship=data.citizenship, source_authority=data.source_authority,
               provenance_reference=data.provenance_reference)
    db.add(p); db.flush()
    for name in data.aliases:
        db.add(PersonAlias(person_id=p.id, name=name, source_authority=data.source_authority))
    db.commit(); db.refresh(p)
    return person_out(p)

@app.get('/v1/people/{person_id}')
def get_person(person_id: int, db: Session = Depends(get_db)):
    p = db.get(Person, person_id)
    if not p: raise HTTPException(404, 'Person not found')
    return person_out(p)

@app.post('/v1/people/{person_id}/documents', status_code=status.HTTP_201_CREATED)
def create_document(person_id: int, data: DocumentCreate, db: Session = Depends(get_db)):
    if not db.get(Person, person_id): raise HTTPException(404, 'Person not found')
    duplicate = db.scalar(select(TravelDocument).where(
        TravelDocument.issuing_jurisdiction == data.issuing_jurisdiction,
        TravelDocument.document_number == data.document_number,
        TravelDocument.status == 'active'))
    if duplicate: raise HTTPException(409, 'Active document already registered')
    d = TravelDocument(person_id=person_id, **data.model_dump())
    db.add(d); db.commit(); db.refresh(d)
    return {'id': d.id, 'person_id': d.person_id, 'document_type': d.document_type,
            'document_number': d.document_number, 'issuing_jurisdiction': d.issuing_jurisdiction,
            'issued_on': d.issued_on, 'expires_on': d.expires_on, 'status': d.status,
            'verification_provenance': d.verification_provenance}

@app.post('/v1/cases', status_code=status.HTTP_201_CREATED)
def open_case(data: CaseCreate, db: Session = Depends(get_db)):
    if not db.get(Person, data.person_id): raise HTTPException(404, 'Person not found')
    c = ImmigrationCase(**data.model_dump(), status='open')
    db.add(c); db.commit(); db.refresh(c)
    return case_out(c)

def case_out(c: ImmigrationCase):
    return {'id': c.id, 'person_id': c.person_id, 'case_type': c.case_type,
            'jurisdiction': c.jurisdiction, 'status': c.status, 'assigned_unit': c.assigned_unit,
            'history': [{'status': h.status, 'actor_ref': h.actor_ref, 'reason': h.reason,
                         'created_at': h.created_at} for h in c.history]}

@app.post('/v1/cases/{case_id}/transitions')
def transition_case(case_id: int, data: CaseTransition, db: Session = Depends(get_db)):
    c = db.get(ImmigrationCase, case_id)
    if not c: raise HTTPException(404, 'Case not found')
    allowed = {'open': {'under_review'}, 'under_review': {'decided'}, 'decided': set()}
    if data.status not in allowed.get(c.status, set()):
        raise HTTPException(409, 'Unsupported case transition')
    c.status = data.status
    db.add(CaseStatusHistory(case_id=c.id, status=data.status, actor_ref=data.actor_ref, reason=data.reason))
    db.commit(); db.refresh(c)
    return case_out(c)
