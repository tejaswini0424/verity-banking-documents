import asyncio
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import shutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from .database import Base, engine, Session, User, LoginSession, Record, ROOT
from .processing import extract_pages, analyze, create_synthetic, tesseract_command
from . import multimodal
from . import storage

def pack(r): return {'id': r.id, 'kind': r.kind, 'parent': r.parent, 'created': r.created.replace(tzinfo=timezone.utc).isoformat(), **json.loads(r.data)}
def add(db, kind, owner, data, parent=None):
    r = Record(kind=kind, owner=owner, data=json.dumps(data), parent=parent)
    db.add(r); db.commit(); return r
def update(db, r, data):
    r.data = json.dumps({**json.loads(r.data), **data}); db.commit()
def rows(db, owner, kind): return list(db.scalars(select(Record).where(Record.owner==owner, Record.kind==kind).order_by(Record.created.desc())))
def get(db, id, owner, kind=None):
    r = db.get(Record, id)
    if not r or r.owner != owner or (kind and r.kind != kind): raise HTTPException(404, 'Resource not found')
    return r
def audit(db, user, action, resource): add(db, 'audit', user, {'action': action, 'resource': resource})

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if not os.getenv('VERCEL'):
        with Session() as db:
            for r in db.scalars(select(Record).where(Record.kind=='job')):
                if json.loads(r.data).get('status') in ('queued','running'):
                    update(db, r, {'status':'failed','stage':'Interrupted by server restart. Retry processing.'})
    yield

app = FastAPI(title='Verity Banking Document Intelligence', version='0.1.0', lifespan=lifespan)
DEFAULT_ORIGINS='http://localhost:5173,http://127.0.0.1:5173,http://localhost:5178,http://127.0.0.1:5178'
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('ALLOWED_ORIGINS',DEFAULT_ORIGINS).split(','), allow_credentials=True, allow_methods=['GET','POST','PATCH','PUT'], allow_headers=['Content-Type'])
attempts = defaultdict(deque)
@app.middleware('http')
async def headers(request, call_next):
    if request.url.path.startswith('/api/v1/auth/') and request.method == 'POST':
        key = request.client.host if request.client else 'unknown'
        q = attempts[key]; t = time.monotonic()
        while q and q[0] < t-60: q.popleft()
        if len(q) >= 20: return Response('Too many authentication attempts',status_code=429)
        q.append(t)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin = request.headers.get('origin')
        allowed = os.getenv('ALLOWED_ORIGINS',DEFAULT_ORIGINS).split(',')
        # Trust only the exact deployment aliases injected by Vercel, never a wildcard.
        allowed += ['https://'+os.environ[k] for k in ('VERCEL_URL','VERCEL_PROJECT_PRODUCTION_URL') if os.getenv(k)]
        if origin and origin not in allowed: return Response('Origin forbidden',status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Cache-Control']='no-store'
    return response

def current(request: Request):
    token = request.cookies.get('verity_session','')
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with Session() as db:
        s = db.get(LoginSession,token_hash)
        if not s or s.expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc): raise HTTPException(401,'Please sign in')
        user = db.get(User,s.user_id)
        if not user: raise HTTPException(401,'Please sign in')
        return {'id':user.id,'email':user.email,'role':user.role}

class Credentials(BaseModel):
    email: str = Field(min_length=5,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10,max_length=128)
def hash_password(password, salt): return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
@app.post('/api/v1/auth/{action}')
def auth(action: str, data: Credentials, response: Response):
    email=data.email.lower()
    with Session() as db:
        u = db.scalar(select(User).where(User.email==email))
        if action=='register':
            if u: raise HTTPException(409,'Email already registered')
            salt=secrets.token_hex(16)
            u=User(email=email,password=salt+':'+hash_password(data.password,salt),role='analyst')
            db.add(u); db.commit()
        elif action=='login':
            if not u: raise HTTPException(401,'Invalid email or password')
            salt,pw=u.password.split(':')
            if not hmac.compare_digest(pw,hash_password(data.password,salt)): raise HTTPException(401,'Invalid email or password')
        else: raise HTTPException(404,'Unknown auth action')
        token=secrets.token_urlsafe(32)
        db.add(LoginSession(token=hashlib.sha256(token.encode()).hexdigest(),user_id=u.id,expires=datetime.now(timezone.utc)+timedelta(hours=8)))
        db.commit()
        response.set_cookie('verity_session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=28800)
        audit(db,u.id,'Signed in',u.id)
        return {'id':u.id,'email':u.email,'role':u.role}
@app.get('/api/v1/auth/me')
def me(user=Depends(current)): return user
@app.post('/api/v1/logout')
def logout(request: Request,response: Response,user=Depends(current)):
    with Session() as db:
        db.execute(delete(LoginSession).where(LoginSession.token==hashlib.sha256(request.cookies.get('verity_session','').encode()).hexdigest())); db.commit()
    response.delete_cookie('verity_session'); return {'ok':True}

class CaseInput(BaseModel):
    name: str=Field(min_length=2,max_length=100)
    reference: str=Field(default='',max_length=100)
class ReviewInput(BaseModel):
    outcome: str=Field(pattern='^(approved|rejected|needs_information)$')
    reason: str=Field(min_length=8,max_length=2000)
class SyntheticInput(BaseModel):
    count: int=Field(default=4,ge=1,le=30)
    seed: int=Field(default=42,ge=0,le=2147483647)
    scenario: str=Field(default='clean',pattern='^(clean|arithmetic_mismatch|missing_field|expired|mixed)$')
    document_type: str=Field(default='salary_slip',pattern='^(salary_slip|bank_statement|identity|address_proof|loan_application)$')

@app.get('/api/v1/health')
def health():
    with engine.connect() as connection:
        from sqlalchemy import text
        connection.execute(text('SELECT 1'))
    return {'status':'ok','database':'connected','ocr': bool(tesseract_command()),'multimodal':'configured' if multimodal.configured() else 'not_configured','model':os.getenv('OLLAMA_MODEL'),'mode':'local OCR + rules baseline','storage':'persistent_database' if storage.persistent() else 'local_files','upload_limit_mb':4 if os.getenv('VERCEL') else 15,'deployment':'vercel' if os.getenv('VERCEL') else 'local'}
@app.get('/api/v1/workspace')
def workspace(user=Depends(current)):
    with Session() as db:
        kinds=['case','document','job','review','dataset','experiment','audit','report']
        result={k+'s':[pack(r) for r in rows(db,user['id'],k)[:500]] for k in kinds}
        result['user']=user
        return result
@app.post('/api/v1/cases')
def new_case(data: CaseInput,user=Depends(current)):
    with Session() as db:
        r=add(db,'case',user['id'],{**data.model_dump(),'status':'open','recommendation':'review_required'})
        audit(db,user['id'],'Created case',r.id); return pack(r)

def process(document_id, owner, job_id, mode='ocr_rules'):
    with Session() as db:
        d=get(db,document_id,owner,'document'); j=get(db,job_id,owner,'job')
        try:
            update(db,j,{'status':'running','stage':'Rendering and extracting text'})
            started=time.monotonic()
            path=storage.restore(json.loads(d.data)['path'],owner)
            pages=extract_pages(path,require_ocr=mode=='ocr_rules')
            for page in pages: storage.save(ROOT/page['image'],owner)
            structured=None
            if mode in ('multimodal','hybrid'):
                update(db,j,{'stage':'Running local vision-language inference'})
                structured=multimodal.extract(pages)
                if mode=='hybrid':
                    baseline=analyze(pages)
                    existing={f['name'] for f in structured['fields']}
                    structured['fields'] += [f for f in baseline['fields'] if f['name'] not in existing]
            update(db,j,{'stage':'Checking fields and arithmetic'})
            result=analyze(pages,structured)
            result['mode']=mode
            result['duration_seconds']=round(time.monotonic()-started,3)
            if structured:
                result['model']=structured['model']
                result['prompt_version']=structured['prompt_version']
                result['limitations']=['Model output may be incorrect. Unverified quotes require manual inspection.','Automated checks do not authenticate the issuer.','Visual forgery localization is not implemented.']
            add(db,'analysis_run',owner,{'document_id':d.id,**result},d.id)
            update(db,d,{'status':'completed','pages':pages,**result})
            update(db,j,{'status':'completed','stage':'Analysis complete'})
            audit(db,owner,'Processed document',d.id)
        except Exception as exc:
            message=str(exc) if isinstance(exc,ValueError) else 'Processing failed. Check the document format and server logs.'
            update(db,d,{'status':'failed','error':message})
            update(db,j,{'status':'failed','stage':message})

def queue(db,d,owner,background,mode='ocr_rules'):
    existing=[j for j in rows(db,owner,'job') if j.parent==d.id and json.loads(j.data)['status'] in ('queued','running')]
    if existing: return pack(existing[0])
    j=add(db,'job',owner,{'status':'queued','stage':'Waiting for worker','document_id':d.id,'mode':mode},d.id)
    update(db,d,{'status':'queued'})
    if os.getenv('VERCEL'):
        # Complete processing inside the function invocation rather than relying on
        # instance-local tasks surviving the response or another cold instance.
        process(d.id,owner,j.id,mode)
        db.refresh(j)
        db.refresh(d)
    else: background.add_task(process,d.id,owner,j.id,mode)
    return pack(j)
@app.post('/api/v1/cases/{case_id}/documents')
async def upload(case_id:str,background:BackgroundTasks,file:UploadFile=File(...),user=Depends(current)):
    with Session() as db:
        get(db,case_id,user['id'],'case')
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in ('.pdf','.png','.jpg','.jpeg'): raise HTTPException(415,'Only PDF, PNG, and JPEG files are supported')
        limit=4 if os.getenv('VERCEL') else 15
        content=await file.read(limit*1024*1024+1)
        if len(content)>limit*1024*1024: raise HTTPException(413,f'Maximum upload size is {limit} MB')
        if not content: raise HTTPException(400,'Empty file')
        valid=(suffix=='.pdf' and content.startswith(b'%PDF-')) or (suffix=='.png' and content.startswith(b'\x89PNG\r\n\x1a\n')) or (suffix in ('.jpg','.jpeg') and content.startswith(b'\xff\xd8\xff'))
        if not valid: raise HTTPException(415,'File signature does not match its extension')
        name=str(uuid4())+suffix
        (ROOT/name).write_bytes(content)
        storage.save(ROOT/name,user['id'])
        d=add(db,'document',user['id'],{'name':Path(file.filename).name,'path':name,'sha256':hashlib.sha256(content).hexdigest(),'size':len(content),'status':'uploaded','document_type':'unknown'},case_id)
        audit(db,user['id'],'Uploaded document',d.id)
        return {'document':pack(d),'job':queue(db,d,user['id'],background)}
@app.post('/api/v1/documents/{id}/process')
def retry(id:str,background:BackgroundTasks,mode:str='ocr_rules',user=Depends(current)):
    if mode not in ('ocr_rules','multimodal','hybrid'): raise HTTPException(422,'Unknown processing mode')
    if mode!='ocr_rules' and not multimodal.configured(): raise HTTPException(409,'Configure OLLAMA_MODEL to enable multimodal processing')
    with Session() as db: return queue(db,get(db,id,user['id'],'document'),user['id'],background,mode)
@app.get('/api/v1/documents/{id}')
def document(id:str,user=Depends(current)):
    with Session() as db: return pack(get(db,id,user['id'],'document'))
@app.get('/api/v1/documents/{id}/file')
def document_file(id:str,page:int|None=None,user=Depends(current)):
    with Session() as db:
        data=json.loads(get(db,id,user['id'],'document').data)
        if page is None: return FileResponse(storage.restore(data['path'],user['id']),filename=data['name'])
        pages=data.get('pages',[])
        if page<1 or page>len(pages): raise HTTPException(404,'Page not found')
        return FileResponse(storage.restore(pages[page-1]['image'],user['id']),media_type='image/png')
@app.get('/api/v1/jobs/{id}/events')
def events(id:str,user=Depends(current)):
    with Session() as db: get(db,id,user['id'],'job')
    async def stream():
        for _ in range(120):
            with Session() as db: data=pack(get(db,id,user['id'],'job'))
            yield 'data: '+json.dumps(data)+'\n\n'
            if data['status'] in ('completed','failed'): break
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream')

@app.post('/api/v1/cases/{id}/verify')
def verify(id:str,user=Depends(current)):
    with Session() as db:
        case=get(db,id,user['id'],'case')
        docs=[pack(r) for r in rows(db,user['id'],'document') if r.parent==id]
        checks=[]
        names=[]
        for d in docs:
            names.extend((f['value'].casefold().strip(),d['id']) for f in d.get('fields',[]) if f['name']=='name')
        unique={n[0] for n in names}
        checks.append({'rule':'Applicant name consistency','status':'failed' if len(unique)>1 else 'passed' if len(names)>1 else 'review','detail':f'{len(unique)} distinct names across {len(names)} extracted names'})
        types={d.get('document_type') for d in docs}
        for typ in ('identity','bank_statement','salary_slip'):
            checks.append({'rule':'Required document: '+typ,'status':'passed' if typ in types else 'review','detail':'Present' if typ in types else 'Missing from case'})
        hashes=[d['sha256'] for d in docs]
        checks.append({'rule':'Exact duplicates in case','status':'review' if len(set(hashes))<len(hashes) else 'passed','detail':str(len(hashes)-len(set(hashes)))+' duplicate uploads'})
        failed=any(c['status']=='failed' for c in checks) or any(d.get('recommendation')=='checks_failed' for d in docs)
        result={'checks':checks,'recommendation':'checks_failed' if failed else 'review_required','status':'awaiting_review'}
        update(db,case,result); audit(db,user['id'],'Verified case',id)
        return pack(case)
@app.post('/api/v1/cases/{id}/reviews')
def review(id:str,data:ReviewInput,user=Depends(current)):
    with Session() as db:
        c=get(db,id,user['id'],'case')
        if not any(r.parent==id and json.loads(r.data).get('status')=='completed' for r in rows(db,user['id'],'document')): raise HTTPException(409,'Process at least one document before review')
        r=add(db,'review',user['id'],{**data.model_dump(),'reviewer':user['email']},id)
        update(db,c,{'status':data.outcome}); audit(db,user['id'],'Recorded human review',id)
        return pack(r)

@app.post('/api/v1/datasets/generate')
def generate(data:SyntheticInput,background:BackgroundTasks,user=Depends(current)):
    if os.getenv('VERCEL') and data.count>10: raise HTTPException(422,'Cloud demonstration supports up to 10 documents per generation request')
    if data.scenario=='expired' and data.document_type!='identity': raise HTTPException(422,'Expired scenario requires identity documents')
    with Session() as db:
        c=add(db,'case',user['id'],{'name':f'Synthetic benchmark · seed {data.seed}','reference':'RESEARCH','status':'open','recommendation':'review_required'})
        dataset=add(db,'dataset',user['id'],{**data.model_dump(),'name':f'Benchmark {data.seed}','case_id':c.id,'items':[]})
        items=[]
        for i in range(data.count):
            scenario=data.scenario if data.scenario!='mixed' else ['clean','arithmetic_mismatch','missing_field'][i%3]
            if scenario=='expired' and data.document_type!='identity': raise HTTPException(422,'Expired scenario requires identity documents')
            if scenario=='arithmetic_mismatch' and data.document_type not in ('salary_slip','bank_statement'): scenario='missing_field'
            path=ROOT/(str(uuid4())+'.pdf')
            label=create_synthetic(path,scenario=scenario,kind=data.document_type,seed=data.seed+i)
            storage.save(path,user['id'])
            d=add(db,'document',user['id'],{'name':f'synthetic-{i+1}.pdf','path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':path.stat().st_size,'status':'uploaded','document_type':'unknown','synthetic':True},c.id)
            items.append({'document_id':d.id,**label}); queue(db,d,user['id'],background)
        update(db,dataset,{'items':items}); audit(db,user['id'],'Generated synthetic dataset',dataset.id)
        return pack(dataset)

class ExperimentInput(BaseModel):
    dataset_id: str
    name: str=Field(min_length=2,max_length=100)
@app.post('/api/v1/experiments')
def experiment(data:ExperimentInput,user=Depends(current)):
    with Session() as db:
        ds=pack(get(db,data.dataset_id,user['id'],'dataset'))
        tp=fp=tn=fn=0
        for item in ds['items']:
            d=pack(get(db,item['document_id'],user['id'],'document'))
            if d.get('status')!='completed': raise HTTPException(409,'Wait for every dataset document to complete processing')
            predicted=bool(d.get('findings'))
            actual=item['expected_finding']
            tp+=int(predicted and actual); fp+=int(predicted and not actual)
            tn+=int(not predicted and not actual); fn+=int(not predicted and actual)
        precision=tp/(tp+fp) if tp+fp else 0
        recall=tp/(tp+fn) if tp+fn else 0
        r=add(db,'experiment',user['id'],{'name':data.name,'dataset_id':ds['id'],'mode':'ocr_rules','status':'completed','metrics':{'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'tp':tp,'fp':fp,'tn':tn,'fn':fn,'count':tp+tn+fp+fn},'limitations':'Template-specific synthetic evaluation. Not a held-out real-world or multimodal benchmark.'})
        audit(db,user['id'],'Evaluated baseline',r.id); return pack(r)

@app.get('/api/v1/reports/{id}')
def report(id:str,format:str='json',user=Depends(current)):
    with Session() as db:
        r=get(db,id,user['id'])
        if r.kind not in ('case','experiment','dataset'): raise HTTPException(400,'Reports support cases, datasets, and experiments')
        data=pack(r)
        if r.kind=='case': data['documents']=[pack(d) for d in rows(db,user['id'],'document') if d.parent==id]
        def sanitize(value):
            if isinstance(value,dict): return {k:sanitize(v) for k,v in value.items() if k not in ('path','image','sha256')}
            if isinstance(value,list): return [sanitize(v) for v in value]
            return value
        data=sanitize(data)
        data['disclaimer']='Research assistance only. Automated checks do not establish issuer authenticity or prove fraud.'
        if format=='csv':
            out=io.StringIO(); w=csv.writer(out); w.writerow(['metric','value'])
            for k,v in data.get('metrics',data).items():
                text=str(v); w.writerow([k, "'"+text if text.lstrip().startswith(('=','+','-','@')) else text])
            return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="report-{id}.csv"'})
        if format!='json': raise HTTPException(422,'Supported formats: json, csv')
        audit(db,user['id'],'Exported report',id)
        return Response(json.dumps(data,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="report-{id}.json"'})
