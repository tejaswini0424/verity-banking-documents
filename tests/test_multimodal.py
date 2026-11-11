import base64
import json
import httpx
import pytest
from backend.app import multimodal

def test_adapter_schema_and_evidence(monkeypatch,tmp_path):
    monkeypatch.setenv('OLLAMA_MODEL','test-vision')
    monkeypatch.setattr(multimodal,'ROOT',tmp_path)
    (tmp_path/'page.png').write_bytes(b'test-image')
    seen=[]
    def respond(request):
        data=json.loads(request.content);seen.append(data)
        return httpx.Response(200,json={'message':{'content':json.dumps({'document_type':'salary_slip','fields':[{'name':'name','value':'Asha Example','page':1,'evidence':'Name: Asha Example'}]})}})
    with httpx.Client(transport=httpx.MockTransport(respond),base_url='http://local.test') as client:
        result=multimodal.extract([{'text':'Name: Asha Example','image':'page.png'}],client)
    assert result['fields'][0]['grounding']=='text_verified'
    assert seen[0]['messages'][0]['images']==[base64.b64encode(b'test-image').decode()]
    assert seen[0]['format']['type']=='object'
    assert seen[0]['stream'] is False

def test_adapter_rejects_out_of_range_page(monkeypatch,tmp_path):
    monkeypatch.setenv('OLLAMA_MODEL','test-vision');monkeypatch.setattr(multimodal,'ROOT',tmp_path)
    (tmp_path/'page.png').write_bytes(b'test')
    transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'message':{'content':json.dumps({'document_type':'identity','fields':[{'name':'name','value':'Example','page':2,'evidence':'Example'}]})}}))
    with httpx.Client(transport=transport,base_url='http://local.test') as client:
        with pytest.raises(ValueError,match='outside'):multimodal.extract([{'text':'','image':'page.png'}],client)

def test_adapter_requires_configuration(monkeypatch):
    monkeypatch.delenv('OLLAMA_MODEL',raising=False)
    with pytest.raises(ValueError,match='Configure'):multimodal.extract([])
