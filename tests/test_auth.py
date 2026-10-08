"""Testes de cadastro e login (RF-01, RF-02, RNF-01)."""

from tests.conftest import register


def test_register_cria_conta_free_e_devolve_token(client):
    res = client.post("/auth/register", json={"email": "Ana@Exemplo.com", "password": "senha-forte-123"})
    assert res.status_code == 201
    data = res.json()
    assert data["access_token"]
    assert data["user"]["email"] == "ana@exemplo.com"   # normalizado para minúsculas
    assert data["user"]["plan_type"] == "free"


def test_register_rejeita_email_duplicado(client):
    register(client)
    res = client.post("/auth/register", json={"email": "ana@exemplo.com", "password": "outra-senha-123"})
    assert res.status_code == 409


def test_register_rejeita_senha_curta_e_email_invalido(client):
    assert client.post("/auth/register", json={"email": "ana@exemplo.com", "password": "123"}).status_code == 422
    assert client.post("/auth/register", json={"email": "nao-e-email", "password": "senha-forte-123"}).status_code == 422


def test_login_ok_e_senha_errada(client):
    register(client)
    ok = client.post("/auth/login", json={"email": "ana@exemplo.com", "password": "senha-forte-123"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/auth/login", json={"email": "ana@exemplo.com", "password": "errada-123456"})
    assert bad.status_code == 401


def test_senha_nao_fica_em_texto_plano(client):
    from backend.database import SessionLocal
    from backend.models import User

    register(client, password="senha-forte-123")
    with SessionLocal() as db:
        user = db.query(User).first()
        assert user.password_hash != "senha-forte-123"
        assert user.password_hash.startswith("$2")  # prefixo do bcrypt


def test_rota_protegida_exige_token(client):
    assert client.get("/auth/me").status_code == 401
    headers = register(client)
    assert client.get("/auth/me", headers=headers).status_code == 200
