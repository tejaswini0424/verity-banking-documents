from uuid import uuid4
import pytest
from backend.app.database import Base, engine, Session, User, ROOT
from backend.app import storage

def test_private_artifact_restores_after_cache_loss(monkeypatch):
    Base.metadata.create_all(engine)
    monkeypatch.setenv('ARTIFACT_STORAGE','database')
    owner=str(uuid4())
    with Session() as db:
        db.add(User(id=owner,email=owner+'@example.test',password='unused-test-hash'));db.commit()
    path=ROOT/(str(uuid4())+'.pdf')
    path.write_bytes(b'fictional-test-artifact')
    storage.save(path,owner)
    path.unlink()
    assert storage.restore(path.name,owner).read_bytes()==b'fictional-test-artifact'
    with pytest.raises(ValueError,match='not found'):storage.restore(path.name,'another-user')
    with pytest.raises(ValueError,match='Invalid'):storage.restore('../outside.pdf',owner)

def test_serverless_workflow_completes_and_restores_files(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('ARTIFACT_STORAGE','database')
    with TestClient(app) as client:
        r=client.post('/api/v1/auth/register',json={'email':str(uuid4())+'@example.test','password':'Cloud-test-password!2026'})
        assert r.status_code==200
        result=client.post('/api/v1/datasets/generate',json={'count':2,'seed':101,'scenario':'mixed'})
        assert result.status_code==200,result.text
        ws=client.get('/api/v1/workspace').json()
        assert all(j['status']=='completed' for j in ws['jobs'])
        doc=ws['documents'][0]
        source=ROOT/doc['path']
        source.unlink()
        assert client.get('/api/v1/documents/'+doc['id']+'/file').content.startswith(b'%PDF-')
        page=ROOT/doc['pages'][0]['image']
        page.unlink()
        assert client.get('/api/v1/documents/'+doc['id']+'/file?page=1').content.startswith(b'\x89PNG')
        assert client.get('/api/v1/health').json()['storage']=='persistent_database'
        assert client.post('/api/v1/datasets/generate',json={'count':11}).status_code==422
