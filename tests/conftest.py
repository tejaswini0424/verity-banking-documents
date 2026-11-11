"""Set test isolation before any application module is imported."""
import os
import tempfile
from pathlib import Path

test_parent=Path(__file__).resolve().parents[1]/'storage'
test_parent.mkdir(exist_ok=True)
test_root=Path(tempfile.mkdtemp(prefix='test-app-',dir=test_parent))
os.environ['STORAGE_DIR']=str(test_root)
os.environ['DATABASE_URL']='sqlite:///'+str(test_root/'test.db')
os.environ.pop('VERCEL',None)
os.environ.pop('ARTIFACT_STORAGE',None)
