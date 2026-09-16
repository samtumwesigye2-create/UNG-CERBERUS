from datetime import date, datetime
from pydantic import BaseModel, Field
class PersonCreate(BaseModel):
    primary_name:str; date_of_birth:date|None=None; nationality:str|None=None; citizenship:str|None=None; source_authority:str; provenance_reference:str|None=None; aliases:list[str]=Field(default_factory=list)
class DocumentCreate(BaseModel):
    document_type:str; document_number:str; issuing_jurisdiction:str; issued_on:date|None=None; expires_on:date|None=None; status:str='active'; verification_provenance:str|None=None
class CaseCreate(BaseModel):
    person_id:int; case_type:str; jurisdiction:str; assigned_unit:str|None=None
class CaseTransition(BaseModel):
    status:str; actor_ref:str; reason:str
class BorderEventCreate(BaseModel):
    person_id:int; direction:str; port_code:str; country_code:str; occurred_at:datetime; source_authority:str; provenance_reference:str
class WatchlistCreate(BaseModel):
    subject_name:str; date_of_birth:date|None=None; originating_authority:str; reason_category:str; legal_authority_reference:str; valid_until:date; provenance_reference:str
class ScreeningCreate(BaseModel):
    person_id:int; purpose:str; actor_ref:str
class AdjudicationCreate(BaseModel):
    outcome:str; actor_ref:str; reason:str
