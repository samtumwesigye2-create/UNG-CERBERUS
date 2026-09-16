from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_group1_end_to_end_candidate_requires_human_review():
    with client:
        p = client.post('/v1/people', json={'primary_name':'Grace Atim','date_of_birth':'1988-05-04','nationality':'UG','source_authority':'IMMIGRATION','provenance_reference':'REG-100'}).json()
        d = client.post(f"/v1/people/{p['id']}/documents", json={'document_type':'passport','document_number':'UG-P-100','issuing_jurisdiction':'UG','verification_provenance':'DOC-100'})
        assert d.status_code == 201
        c = client.post('/v1/cases', json={'person_id':p['id'],'case_type':'entry_review','jurisdiction':'UG','assigned_unit':'EBB'})
        assert c.status_code == 201
        b = client.post('/v1/border-events', json={'person_id':p['id'],'direction':'entry','port_code':'EBB','country_code':'UG','occurred_at':'2026-09-16T06:00:00Z','source_authority':'IMMIGRATION','provenance_reference':'BORDER-100'})
        assert b.status_code == 201
        future=(date.today()+timedelta(days=30)).isoformat()
        w=client.post('/v1/watchlist',json={'subject_name':'Grace Atim','date_of_birth':'1988-05-04','originating_authority':'AUTHORIZED-UNIT','reason_category':'manual_review','legal_authority_reference':'AUTH-100','valid_until':future,'provenance_reference':'WL-100'})
        assert w.status_code==201
        s=client.post('/v1/screenings',json={'person_id':p['id'],'purpose':'border_entry','actor_ref':'OFFICER-100'}).json()
        assert s['decision']=='pending_review'
        assert s['matches'] and s['matches'][0]['confirmed_identity'] is False
        a=client.post(f"/v1/screenings/{s['id']}/adjudicate",json={'outcome':'cleared','actor_ref':'SUPERVISOR-100','reason':'Identity reviewed and candidate cleared'})
        assert a.status_code==200 and a.json()['decision']=='cleared'


def test_uganda_profile_and_operator_workspace_contract():
    with client:
        profile=client.get('/v1/profiles/uganda')
        assert profile.status_code==200
        assert profile.json()['country_code']=='UG'
        page=client.get('/')
        assert page.status_code==200
        for marker in ['Identity Registry','Travel Documents','Immigration Cases','Border Events','Watchlist Screening','Human Review']:
            assert marker in page.text
