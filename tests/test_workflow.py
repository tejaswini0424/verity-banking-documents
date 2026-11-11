from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.processing import create_synthetic, extract_pages, analyze

@pytest.fixture
def client():
    with TestClient(app) as c:
        response=c.post('/api/v1/auth/register',json={'email':f'{uuid4().hex}@example.test','password':'TestPassword-123!'})
        assert response.status_code==200,response.text
        yield c

@pytest.mark.parametrize('kind',['salary_slip','bank_statement','identity','address_proof','loan_application'])
def test_clean_documents(tmp_path,kind):
    path=tmp_path/'demo.pdf'
    create_synthetic(path,kind=kind)
    result=analyze(extract_pages(path))
    assert result['document_type']==kind
    assert result['findings']==[]
    assert result['fields'][0]['page']==1
    assert result['recommendation']=='review_required'

@pytest.mark.parametrize('scenario',['arithmetic_mismatch','missing_field'])
def test_alterations_are_detected(tmp_path,scenario):
    path=tmp_path/'demo.pdf';create_synthetic(path,scenario=scenario)
    result=analyze(extract_pages(path))
    assert result['findings']
    if scenario=='arithmetic_mismatch': assert result['recommendation']=='checks_failed'

def test_full_workflow(client):
    ds=client.post('/api/v1/datasets/generate',json={'count':6,'seed':19,'scenario':'mixed','document_type':'salary_slip'})
    assert ds.status_code==200,ds.text
    dataset=ds.json()
    ws=client.get('/api/v1/workspace').json()
    assert len(ws['documents'])==6
    assert all(d['status']=='completed' for d in ws['documents'])
    assert all(j['status']=='completed' for j in ws['jobs'])
    e=client.post('/api/v1/experiments',json={'name':'Baseline evaluation','dataset_id':dataset['id']})
    assert e.status_code==200,e.text
    assert e.json()['metrics']=={'precision':1.0,'recall':1.0,'f1':1.0,'tp':4,'fp':0,'tn':2,'fn':0,'count':6}
    case=client.post('/api/v1/cases/'+dataset['case_id']+'/verify').json()
    assert case['recommendation']=='checks_failed'
    review=client.post('/api/v1/cases/'+dataset['case_id']+'/reviews',json={'outcome':'needs_information','reason':'Synthetic salary mismatch requires inspection.'})
    assert review.status_code==200
    export=client.get('/api/v1/reports/'+dataset['case_id'])
    assert export.status_code==200
    assert 'disclaimer' in export.json()
    assert 'path' not in export.json()['documents'][0]
    assert client.get('/api/v1/reports/'+e.json()['id']+'?format=csv').headers['content-type'].startswith('text/csv')

def test_account_isolation(client):
    case=client.post('/api/v1/cases',json={'name':'Private applicant'}).json()
    client.post('/api/v1/logout')
    client.post('/api/v1/auth/register',json={'email':f'{uuid4().hex}@example.test','password':'AnotherPassword-123!'})
    assert client.get('/api/v1/workspace').json()['cases']==[]
    assert client.post(f"/api/v1/cases/{case['id']}/verify").status_code==404
    assert client.get('/api/v1/reports/'+case['id']).status_code==404

def test_upload_validation_and_evidence(client,tmp_path):
    case=client.post('/api/v1/cases',json={'name':'Upload test'}).json()
    url=f"/api/v1/cases/{case['id']}/documents"
    assert client.post(url,files={'file':('bad.pdf',b'not a PDF','application/pdf')}).status_code==415
    assert client.post(url,files={'file':('code.exe',b'MZ','application/octet-stream')}).status_code==415
    path=tmp_path/'salary.pdf';create_synthetic(path)
    result=client.post(url,files={'file':('salary.pdf',path.read_bytes(),'application/pdf')})
    assert result.status_code==200,result.text
    id=result.json()['document']['id']
    doc=client.get('/api/v1/documents/'+id).json()
    assert doc['status']=='completed'
    assert client.get(f'/api/v1/documents/{id}/file?page=1').status_code==200
    assert client.get(f'/api/v1/documents/{id}/file?page=0').status_code==404
    events=client.get('/api/v1/jobs/'+result.json()['job']['id']+'/events')
    assert 'completed' in events.text

def test_login_logout_and_origin(client):
    assert client.get('/api/v1/auth/me').status_code==200
    assert client.post('/api/v1/cases',json={'name':'Blocked'},headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post('/api/v1/logout').status_code==200
    assert client.get('/api/v1/workspace').status_code==401

def test_invalid_generation_does_not_create_case(client):
    before=len(client.get('/api/v1/workspace').json()['cases'])
    r=client.post('/api/v1/datasets/generate',json={'scenario':'expired','document_type':'salary_slip'})
    assert r.status_code==422
    assert len(client.get('/api/v1/workspace').json()['cases'])==before

def test_review_requires_evidence(client):
    c=client.post('/api/v1/cases',json={'name':'Empty case'}).json()
    assert client.post(f"/api/v1/cases/{c['id']}/reviews",json={'outcome':'approved','reason':'No evidence available'}).status_code==409
