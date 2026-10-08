"""
Conexão com o banco de dados (SQLAlchemy).

Passo a passo para iniciantes:
1. O "engine" é o objeto que sabe conversar com o banco (PostgreSQL no Render,
   SQLite no computador do desenvolvedor).
2. Uma "sessão" (SessionLocal) é uma conversa curta com o banco: abrimos,
   fazemos consultas/gravações e fechamos. Cada requisição HTTP usa a sua.
3. `get_db()` é uma dependência do FastAPI: ela entrega a sessão para a rota
   e garante que ela será fechada no final, mesmo se der erro.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

DATABASE_URL = settings.effective_database_url

# O SQLite precisa de uma opção extra porque o FastAPI pode usar várias threads.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # testa a conexão antes de usar (evita erro de conexão "morta" no Render)
)

# Fábrica de sessões. autoflush/autocommit desligados = nós controlamos quando gravar.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Classe base de todos os modelos (tabelas). Veja backend/models.py."""


def get_db():
    """Dependência do FastAPI: abre uma sessão e fecha ao terminar a requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Cria as tabelas que ainda não existem. Chamado quando o app inicia.
    (Para um MVP isso basta; em projetos maiores usa-se Alembic para migrações.)"""
    from backend import models  # noqa: F401  (importa para registrar as tabelas na Base)

    Base.metadata.create_all(bind=engine)
