from contextlib import asynccontextmanager
from datetime import date
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import Base, engine, ensure_schema, get_db
from app.models import Person, PersonAlias, TravelDocument, ImmigrationCase, CaseStatusHistory, WatchlistEntry, ScreeningEvent, CandidateMatch, Adjudication
from app.schemas import PersonCreate, DocumentCreate, CaseCreate, CaseTransition, WatchlistCreate, ScreeningCreate, AdjudicationCreate
from app.passport_verification import router as passport_verification_router
ensure_schema()
@asynccontextmanager
async def lifespan(app:FastAPI): ensure_schema(); yield
app=FastAPI(title='UNG-CERBERUS',version='0.4.0',lifespan=lifespan)
app.include_router(passport_verification_router)
@app.get('/health')
def health(): return {'status':'ok','system':'UNG-CERBERUS'}
@app.get('/v1/profiles/uganda')
def uganda_profile(): return {'country_code':'UG','name':'Uganda','document_types':['passport','national_id','permit'],'ports':{'EBB':'Entebbe International Airport'},'policy_mode':'configurable'}
@app.get('/',response_class=HTMLResponse)
def workspace():
 return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-CERBERUS</title><style>body{font-family:system-ui;margin:0;background:#0b0f14;color:#eef3f8}header{padding:24px;background:#121a24}main{padding:18px;display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}.card{background:#151e29;border:1px solid #2a3747;border-radius:16px;padding:18px}.safe{color:#7ee0a1}.warn{color:#ffd166}small{color:#9db0c4}</style></head><body><header><h1>UNG-CERBERUS</h1><small>Centralized Entry, Risk & Biometric Evaluation, Registration & Unified Screening</small></header><main><div class="card"><h2>Identity Registry</h2><p>People, aliases and provenance.</p></div><div class="card"><h2>Travel Documents</h2><p>Passports and verification records.</p></div><div class="card"><h2>Immigration Cases</h2><p>Case status and review history.</p></div><div class="card"><h2>Border Events</h2><p>Entry and exit event registry.</p></div><div class="card"><h2>Watchlist Screening</h2><p class="warn">Candidate match does not confirm identity.</p></div><div class="card"><h2>Human Review</h2><p class="safe">Clear or confirm only after authorized review.</p></div></main></body></html>'''
def person_out(p): return {'id':p.id,'person_code':p.person_code,'primary_name':p.primary_name,'date_of_birth':p.date_of_birth,'nationality':p.nationality,'citizenship':p.citizenship,'status':p.status,'source_authority':p.source_authority,'provenance_reference':p.provenance_reference,'aliases':[a.name for a in p.aliases]}
@app.post('/v1/people',status_code=201)
def create_person(data:PersonCreate,db:Session=Depends(get_db)):
 p=Person(person_code=f'CER-P-{uuid4().hex[:8].upper()}',primary_name=data.primary_name,date_of_birth=data.date_of_birth,nationality=data.nationality,citizenship=data.citizenship,source_authority=data.source_authority,provenance_reference=data.provenance_reference); db.add(p); db.flush()
 for n in data.aliases: db.add(PersonAlias(person_id=p.id,name=n,source_authority=data.source_authority))
 db.commit(); db.refresh(p); return person_out(p)
@app.get('/v1/people/{person_id}')
def get_person(person_id:int,db:Session=Depends(get_db)):
 p=db.get(Person,person_id)
 if not p: raise HTTPException(404,'Person not found')
 return person_out(p)
@app.post('/v1/people/{person_id}/documents',status_code=201)
def create_document(person_id:int,data:DocumentCreate,db:Session=Depends(get_db)):
 if not db.get(Person,person_id): raise HTTPException(404,'Person not found')
 duplicate=db.scalar(select(TravelDocument).where(TravelDocument.issuing_jurisdiction==data.issuing_jurisdiction,TravelDocument.document_number==data.document_number,TravelDocument.status=='active'))
 if duplicate: raise HTTPException(409,'Active document already registered')
 d=TravelDocument(person_id=person_id,**data.model_dump()); db.add(d); db.commit(); db.refresh(d); return {'id':d.id,'person_id':d.person_id,'document_type':d.document_type,'document_number':d.document_number,'issuing_jurisdiction':d.issuing_jurisdiction,'issued_on':d.issued_on,'expires_on':d.expires_on,'status':d.status,'verification_provenance':d.verification_provenance}
def case_out(c): return {'id':c.id,'person_id':c.person_id,'case_type':c.case_type,'jurisdiction':c.jurisdiction,'status':c.status,'assigned_unit':c.assigned_unit,'history':[{'status':h.status,'actor_ref':h.actor_ref,'reason':h.reason,'created_at':h.created_at} for h in c.history]}
@app.post('/v1/cases',status_code=201)
def open_case(data:CaseCreate,db:Session=Depends(get_db)):
 if not db.get(Person,data.person_id): raise HTTPException(404,'Person not found')
 c=ImmigrationCase(**data.model_dump(),status='open'); db.add(c); db.commit(); db.refresh(c); return case_out(c)
@app.post('/v1/cases/{case_id}/transitions')
def transition_case(case_id:int,data:CaseTransition,db:Session=Depends(get_db)):
 c=db.get(ImmigrationCase,case_id)
 if not c: raise HTTPException(404,'Case not found')
 allowed={'open':{'under_review'},'under_review':{'decided'},'decided':set()}
 if data.status not in allowed.get(c.status,set()): raise HTTPException(409,'Unsupported case transition')
 c.status=data.status; db.add(CaseStatusHistory(case_id=c.id,status=data.status,actor_ref=data.actor_ref,reason=data.reason)); db.commit(); db.refresh(c); return case_out(c)
@app.post('/v1/watchlist',status_code=201)
def watchlist(data:WatchlistCreate,db:Session=Depends(get_db)):
 if not data.legal_authority_reference.strip() or not data.originating_authority.strip(): raise HTTPException(422,'authority and legal authority are required')
 w=WatchlistEntry(**data.model_dump()); db.add(w); db.commit(); db.refresh(w); return {'id':w.id,'status':w.status,'subject_name':w.subject_name,'valid_until':w.valid_until,'originating_authority':w.originating_authority}
def screening_out(s): return {'id':s.id,'person_id':s.person_id,'purpose':s.purpose,'decision':s.decision,'matches':[{'watchlist_entry_id':m.watchlist_entry_id,'confidence':m.confidence,'confirmed_identity':m.confirmed_identity,'rationale':m.rationale} for m in s.matches]}
@app.post('/v1/screenings',status_code=201)
def screen(data:ScreeningCreate,db:Session=Depends(get_db)):
 p=db.get(Person,data.person_id)
 if not p: raise HTTPException(404,'Person not found')
 active=db.scalars(select(WatchlistEntry).where(WatchlistEntry.status=='active',WatchlistEntry.valid_until>=date.today())).all(); hits=[]; names={p.primary_name.casefold(),*[a.name.casefold() for a in p.aliases]}
 for w in active:
  if w.subject_name.casefold() in names and (w.date_of_birth is None or p.date_of_birth is None or w.date_of_birth==p.date_of_birth): hits.append(w)
 s=ScreeningEvent(person_id=p.id,purpose=data.purpose,actor_ref=data.actor_ref,decision='pending_review' if hits else 'no_active_match'); db.add(s); db.flush()
 for w in hits: db.add(CandidateMatch(screening_id=s.id,watchlist_entry_id=w.id,confidence=1.0,confirmed_identity=False,rationale='Biographic candidate match; human adjudication required'))
 db.commit(); db.refresh(s); return screening_out(s)
@app.post('/v1/screenings/{screening_id}/adjudicate')
def adjudicate(screening_id:int,data:AdjudicationCreate,db:Session=Depends(get_db)):
 s=db.get(ScreeningEvent,screening_id)
 if not s: raise HTTPException(404,'Screening not found')
 if s.decision!='pending_review': raise HTTPException(409,'Screening is not pending human review')
 if data.outcome not in {'cleared','confirmed'}: raise HTTPException(422,'Unsupported adjudication outcome')
 s.decision=data.outcome; db.add(Adjudication(screening_id=s.id,outcome=data.outcome,actor_ref=data.actor_ref,reason=data.reason)); db.commit(); db.refresh(s); return screening_out(s)
