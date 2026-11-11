"""Private small-file persistence for the serverless research deployment.

Local development uses files. Cloud files live in the database; /tmp is only a cache.
"""
import os
from pathlib import Path
from .database import Artifact, ROOT, Session

def persistent(): return os.getenv('ARTIFACT_STORAGE')=='database'

def save(path: Path, owner: str):
    if not persistent(): return
    with Session() as db:
        existing=db.get(Artifact,path.name)
        if existing:
            if existing.owner!=owner: raise ValueError('Artifact owner mismatch')
            existing.content=path.read_bytes()
        else: db.add(Artifact(name=path.name,owner=owner,content=path.read_bytes()))
        db.commit()

def restore(name: str, owner: str) -> Path:
    if Path(name).name!=name: raise ValueError('Invalid artifact name')
    path=ROOT/name
    if persistent():
        # Always authorize the artifact, including on a warm instance with cached files.
        with Session() as db:
            artifact=db.get(Artifact,name)
            if not artifact or artifact.owner!=owner: raise ValueError('Private artifact not found')
            if not path.exists(): path.write_bytes(artifact.content)
    return path
