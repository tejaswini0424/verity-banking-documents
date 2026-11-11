import pytest
import pymupdf
from backend.app.processing import create_synthetic, extract_pages, analyze, tesseract_command

@pytest.mark.skipif(not tesseract_command(),reason='Tesseract executable not installed')
def test_scanned_salary_document(tmp_path):
    source=tmp_path/'salary.pdf'
    create_synthetic(source)
    with pymupdf.open(source) as pdf:
        pdf[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(tmp_path/'scan.png')
    pages=extract_pages(tmp_path/'scan.png')
    assert pages[0]['mode']=='tesseract_ocr'
    result=analyze(pages)
    assert result['document_type']=='salary_slip'
    assert any(f['name']=='name' and 'Asha' in f['value'] for f in result['fields'])
