import os
from pathlib import Path
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(os.getenv('STORAGE_DIR', '/tmp/verity' if os.getenv('VERCEL') else str(Path(__file__).resolve().parents[2] / 'storage')))
ROOT.mkdir(parents=True, exist_ok=True)
URL = os.getenv('DATABASE_URL', 'sqlite:///' + str(ROOT / 'verity.db'))
if os.getenv('VERCEL') and URL.startswith('sqlite'):
    raise RuntimeError('Cloud deployment requires a persistent DATABASE_URL; ephemeral SQLite is disabled.')
if URL.startswith(('postgres://','postgresql://')):
    URL = 'postgresql+psycopg://' + URL.split('://',1)[1]
engine = create_engine(URL, connect_args={'check_same_thread': False} if URL.startswith('sqlite') else {}, **({'poolclass': NullPool} if os.getenv('VERCEL') else {}))
Session = sessionmaker(engine, expire_on_commit=False)

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='analyst')
class LoginSession(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
class Record(Base):
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    owner: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    parent: Mapped[str | None] = mapped_column(String(36), index=True)
    data: Mapped[str] = mapped_column(Text, default='{}')
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Artifact(Base):
    __tablename__ = 'private_artifacts'
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    owner: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
