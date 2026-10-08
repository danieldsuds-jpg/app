"""
Configuração compartilhada dos testes (pytest).

Passo a passo para iniciantes:
- Antes de importar o app, forçamos variáveis de ambiente de teste:
  banco SQLite em memória e OPENAI_API_KEY vazia (modo demonstração).
- `client` é um TestClient do FastAPI: faz requisições HTTP ao app sem
  precisar subir o servidor.
"""

import os

# Precisa vir ANTES de importar backend.config (que lê as variáveis ao iniciar)
os.environ["DATABASE_URL"] = "sqlite://"            # SQLite em memória
os.environ["OPENAI_API_KEY"] = ""                    # modo demonstração
os.environ["JWT_SECRET"] = "segredo-de-teste-apenas-para-pytest-com-32-bytes-ou-mais"
os.environ["FREE_MONTHLY_LIMIT"] = "20"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.database as database
from backend.database import Base

# SQLite em memória precisa de UMA conexão compartilhada (StaticPool), senão
# cada sessão veria um banco vazio diferente.
test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
database.engine = test_engine
database.SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

from main import app  # noqa: E402  (importa depois de trocar o engine)


@pytest.fixture()
def client():
    """App limpo para cada teste: recria as tabelas do zero."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as c:
        yield c


def register(client, email="ana@exemplo.com", password="senha-forte-123"):
    """Atalho: cria uma conta e devolve os cabeçalhos com o token."""
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
