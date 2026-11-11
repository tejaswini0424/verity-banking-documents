"""Evidence-preserving local baseline. No issuer-authenticity claims."""
import io
import re
import shutil
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageStat

FIELD_NAMES = ('Name', 'Address', 'Account Number', 'Employer', 'Period', 'Gross Pay', 'Deductions', 'Net Pay', 'Opening Balance', 'Credits', 'Debits', 'Closing Balance', 'Expiry Date')
REQUIRED = {'salary_slip': ['name', 'employer', 'gross_pay', 'deductions', 'net_pay'], 'bank_statement': ['name', 'account_number', 'opening_balance', 'credits', 'debits', 'closing_balance'], 'identity': ['name', 'expiry_date'], 'address_proof': ['name', 'address'], 'loan_application': ['name', 'address']}

def tesseract_command():
    configured=os.getenv('TESSERACT_CMD')
    candidates=[configured,shutil.which('tesseract')]
    if os.name=='nt': candidates.append(str(Path(os.getenv('ProgramFiles','C:/Program Files'))/'Tesseract-OCR'/'tesseract.exe'))
    return next((str(p) for p in candidates if p and Path(p).is_file()),None)

def classify(text: str) -> str:
    t = text.lower()
    for word, kind in [('salary', 'salary_slip'), ('bank statement', 'bank_statement'), ('identity', 'identity'), ('address proof', 'address_proof'), ('loan application', 'loan_application')]:
        if word in t: return kind
    return 'unknown'

def extract_pages(path: Path, require_ocr=True):
    pages = []
    if path.suffix == '.pdf':
        with fitz.open(path) as pdf:
            if pdf.is_encrypted: raise ValueError('Encrypted PDFs are unsupported. Upload an unlocked document.')
            if len(pdf) > 30: raise ValueError('Maximum 30 pages per document.')
            for n, p in enumerate(pdf):
                pix = p.get_pixmap(matrix=fitz.Matrix(1.4, 1.4))
                image_path = path.with_name(f'{path.stem}-page-{n+1}.png')
                pix.save(image_path)
                text = p.get_text()
                mode = 'pdf_text'
                if not text.strip():
                    text = ocr(image_path) if require_ocr or tesseract_command() else ''
                    mode = 'tesseract_ocr' if text else 'image_only'
                pages.append({'number': n+1, 'text': text, 'mode': mode, 'image': image_path.name})
    else:
        with Image.open(path) as im:
            if im.width * im.height > 25_000_000: raise ValueError('Image exceeds 25 megapixels.')
            image_path = path.with_suffix('.png')
            im.convert('RGB').save(image_path)
        text=ocr(image_path) if require_ocr or tesseract_command() else ''
        pages.append({'number': 1, 'text': text, 'mode': 'tesseract_ocr' if text else 'image_only', 'image': image_path.name})
    return pages

def ocr(path):
    command=tesseract_command()
    if not command:
        raise ValueError('Tesseract executable is unavailable. Install Tesseract for scanned documents; text PDFs work without it.')
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd=command
    return pytesseract.image_to_string(Image.open(path), timeout=45)

def analyze(pages, structured=None):
    fields = []
    for p in pages:
        for label in FIELD_NAMES:
            for m in re.finditer(r'(?im)^\s*' + re.escape(label) + r'\s*:\s*([^\r\n]+)', p['text']):
                fields.append({'name': label.lower().replace(' ', '_'), 'value': m.group(1).strip(), 'page': p['number'], 'evidence': m.group(0).strip(), 'method': 'label_regex', 'confidence': None})
    text = '\n'.join(p['text'] for p in pages)
    kind = classify(text)
    if structured is not None:
        fields=structured['fields']
        kind=structured['document_type']
    values = {f['name']: f['value'] for f in fields}
    checks = []
    def check(rule, status, detail): checks.append({'rule': rule, 'status': status, 'detail': detail})
    for f in fields:
        if f.get('grounding')=='model_reported_unverified':
            check('Unverified model evidence: '+f['name'],'review',f'Page {f["page"]}: model quote could not be verified against extracted text')
    check('Document classification', 'passed' if kind != 'unknown' else 'review', kind.replace('_', ' '))
    for key in REQUIRED.get(kind, ['name']):
        check('Required: ' + key.replace('_', ' '), 'passed' if values.get(key) else 'review', 'Field extracted' if values.get(key) else 'Not extracted; inspect document manually')
    def number(key):
        value = re.sub(r'(?i)INR|Rs\.?|₹|,|\s', '', values[key])
        return Decimal(value)
    sets = [('salary_slip', ['gross_pay', 'deductions', 'net_pay']), ('bank_statement', ['opening_balance', 'credits', 'debits', 'closing_balance'])]
    for typ, keys in sets:
        if kind == typ and all(k in values for k in keys):
            try:
                ns = [number(k) for k in keys]
                expected = ns[0] - ns[1] if typ == 'salary_slip' else ns[0] + ns[1] - ns[2]
                valid = abs(expected - ns[-1]) <= Decimal('0.01')
                check('Financial arithmetic', 'passed' if valid else 'failed', f'Calculated {expected}; reported {ns[-1]}')
            except (InvalidOperation, ValueError): check('Financial arithmetic', 'review', 'Unrecognized numeric format')
    if 'expiry_date' in values:
        from datetime import date
        try:
            expired = date.fromisoformat(values['expiry_date']) < date.today()
            check('Expiry date', 'failed' if expired else 'passed', values['expiry_date'])
        except ValueError: check('Expiry date', 'review', 'Expected YYYY-MM-DD')
    findings = [{'indicator': c['rule'], 'severity': 'high' if c['status'] == 'failed' else 'medium', 'detail': c['detail']} for c in checks if c['status'] != 'passed']
    return {'document_type': kind, 'fields': fields, 'checks': checks, 'findings': findings, 'mode': 'ocr_rules', 'recommendation': 'checks_failed' if any(c['status']=='failed' for c in checks) else 'review_required', 'limitations': ['Local label-based extraction supports the synthetic templates. Other layouts may need manual extraction.', 'Passing checks does not authenticate the issuer.', 'Visual tampering and multimodal inference are not implemented in this baseline.']}

def create_synthetic(path: Path, name='Asha Example', scenario='clean', kind='salary_slip', seed=42):
    import random
    r = random.Random(seed)
    gross = r.randrange(40000, 100000, 1000)
    deductions = r.randrange(1000, 8000, 500)
    titles = {'salary_slip': 'SALARY SLIP', 'bank_statement': 'BANK STATEMENT', 'identity': 'SYNTHETIC IDENTITY', 'address_proof': 'ADDRESS PROOF', 'loan_application': 'LOAN APPLICATION'}
    rows = [titles[kind], 'SYNTHETIC RESEARCH DOCUMENT - NOT VALID FOR BANKING', '', f'Name: {name}', 'Address: 14 Example Road, Sample City']
    if kind == 'salary_slip': rows += ['Employer: Fictional Labs Ltd', 'Period: 2026-10', f'Gross Pay: {gross}', f'Deductions: {deductions}', f'Net Pay: {gross-deductions+(17000 if scenario=="arithmetic_mismatch" else 0)}']
    elif kind == 'bank_statement': rows += ['Account Number: DEMO-XXXX-1024', 'Period: 2026-10', 'Opening Balance: 25000', 'Credits: 60000', 'Debits: 18000', f'Closing Balance: {67000 if scenario!="arithmetic_mismatch" else 92000}']
    elif kind == 'identity': rows += [f'Expiry Date: {"2020-01-01" if scenario=="expired" else "2030-01-01"}']
    if scenario == 'missing_field': rows = [x for x in rows if not x.startswith('Name:')]
    pdf = fitz.open()
    page = pdf.new_page()
    page.draw_rect(fitz.Rect(35, 35, 560, 800), color=(.13,.34,.30), width=2)
    for i, line in enumerate(rows): page.insert_text((55, 80+i*30), line, fontsize=11 if i else 20)
    page.insert_text((55, 760), f'Fictional benchmark | Seed {seed} | Document intelligence research', fontsize=9)
    pdf.save(path)
    pdf.close()
    return {'scenario': scenario, 'expected_finding': scenario != 'clean', 'seed': seed, 'document_type': kind}
