"""Testes do chat em modo demonstração, histórico e limite de 20 mensagens do Gratuito."""

from tests.conftest import register


def _nova_conversa(client, headers, machine_id=None):
    res = client.post("/conversations", json={"machine_id": machine_id}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_health_informa_modo_demo(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["demo_mode"] is True


def test_chat_modo_demonstracao_responde_e_persiste(client):
    headers = register(client)
    conv_id = _nova_conversa(client, headers)

    res = client.post("/chat", json={"conversation_id": conv_id, "content": "Meu PC está lento"}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["demo_mode"] is True
    assert "MODO DEMONSTRAÇÃO" in data["assistant_message"]["content"]
    assert data["usage"] == {"plan_type": "free", "used": 1, "limit": 20, "remaining": 19, "limit_reached": False}

    # Histórico persistido: 2 mensagens (usuário + Chip) e título automático
    msgs = client.get(f"/conversations/{conv_id}/messages", headers=headers).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    convs = client.get("/conversations", headers=headers).json()
    assert convs[0]["title"] == "Meu PC está lento"


def test_chat_usa_perfil_da_maquina_no_contexto(client):
    headers = register(client)
    machine = client.post(
        "/machines",
        json={"name": "Note velho", "specs": {"os": "Windows 10", "cpu": "i3-6006U", "ram_gb": "4", "storage": "HDD 500 GB"}},
        headers=headers,
    )
    assert machine.status_code == 201
    conv_id = _nova_conversa(client, headers, machine.json()["id"])
    res = client.post("/chat", json={"conversation_id": conv_id, "content": "o que faço?"}, headers=headers)
    assert res.status_code == 200
    assert "Windows 10" in res.json()["assistant_message"]["content"]


def test_limite_20_mensagens_plano_gratuito(client):
    headers = register(client)
    conv_id = _nova_conversa(client, headers)

    for i in range(20):
        res = client.post("/chat", json={"conversation_id": conv_id, "content": f"mensagem {i + 1}"}, headers=headers)
        assert res.status_code == 200, f"falhou na mensagem {i + 1}: {res.text}"
    assert res.json()["usage"]["limit_reached"] is True
    assert res.json()["usage"]["remaining"] == 0

    # A 21ª é bloqueada com aviso + oferta Premium (sem pagamento)
    bloqueada = client.post("/chat", json={"conversation_id": conv_id, "content": "mensagem 21"}, headers=headers)
    assert bloqueada.status_code == 429
    detail = bloqueada.json()["detail"]
    assert detail["code"] == "FREE_LIMIT_REACHED"
    assert detail["premium_offer"]["price"] == "R$ 24,90/mês"
    assert detail["premium_offer"]["promo_price"] == "R$ 19,90/mês"
    assert detail["premium_offer"]["available"] is False

    # O histórico continua acessível (sem interrupção abrupta)
    assert client.get(f"/conversations/{conv_id}/messages", headers=headers).status_code == 200
    plan = client.get("/plan", headers=headers).json()
    assert plan["usage"]["used"] == 20 and plan["usage"]["limit_reached"] is True


def test_premium_nao_tem_limite(client):
    from backend.database import SessionLocal
    from backend.models import User

    headers = register(client)
    with SessionLocal() as db:        # simula um usuário Premium direto no banco
        user = db.query(User).first()
        user.plan_type = "premium"
        db.commit()
    conv_id = _nova_conversa(client, headers)
    for i in range(21):
        assert client.post("/chat", json={"conversation_id": conv_id, "content": f"m{i}"}, headers=headers).status_code == 200
    plan = client.get("/plan", headers=headers).json()
    assert plan["usage"]["limit"] is None


def test_upgrade_ainda_nao_disponivel(client):
    headers = register(client)
    assert client.post("/plan/upgrade", headers=headers).status_code == 501


def test_usuario_nao_acessa_conversa_de_outro(client):
    h1 = register(client, "a@exemplo.com")
    h2 = register(client, "b@exemplo.com")
    conv_id = _nova_conversa(client, h1)
    assert client.get(f"/conversations/{conv_id}/messages", headers=h2).status_code == 404
    assert client.post("/chat", json={"conversation_id": conv_id, "content": "oi"}, headers=h2).status_code == 404


def test_pagina_inicial_e_estaticos(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Mais rápido. Sem trocar tudo." in res.text
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/img/logo_horizontal_dark.png").status_code == 200
