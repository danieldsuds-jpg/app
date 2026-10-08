"""
Rota do chat: POST /chat (RF-03) + controle do limite do Gratuito (Seção 6.2).

Fluxo de uma mensagem:
1. Confere se a conversa é do usuário.
2. Se for plano Gratuito e já usou 20 mensagens no mês → responde 429 com a oferta Premium
   (o frontend mostra o aviso; as conversas antigas continuam legíveis).
3. Grava a mensagem do usuário, monta o histórico e pede a resposta ao Chip (ou modo demo).
4. Grava a resposta e devolve as duas mensagens + uso atualizado.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import Message, User
from backend.routers.conversations import get_owned_conversation
from backend.schemas import ChatIn, ChatOut, MessageOut
from backend.security import get_current_user
from backend.services.ai import generate_reply
from backend.services.usage import get_usage

router = APIRouter(tags=["Chat"])


def limit_detail() -> dict:
    """Corpo do erro 429: texto do aviso + oferta Premium (sem pagamento nesta sprint)."""
    return {
        "code": "FREE_LIMIT_REACHED",
        "message": (
            f"Você usou as {settings.free_monthly_limit} mensagens do plano Gratuito neste mês. "
            "Suas conversas continuam salvas e o limite renova no próximo mês."
        ),
        "premium_offer": {
            "price": settings.premium_price,
            "promo_price": settings.premium_promo_price,
            "available": False,
            "note": "O plano Premium está em breve. Ainda não há pagamento nesta versão.",
        },
    }


@router.post("/chat", response_model=ChatOut)
def chat(data: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = get_owned_conversation(db, user, data.conversation_id)

    # 2) Limite do plano Gratuito
    usage = get_usage(db, user)
    if usage.limit_reached:
        raise HTTPException(status_code=429, detail=limit_detail())

    # 3) Grava a mensagem do usuário
    content = data.content.strip()
    user_msg = Message(conversation_id=conv.id, role="user", content=content)
    db.add(user_msg)
    # Título automático da conversa = começo da primeira mensagem
    if conv.title == "Nova conversa":
        conv.title = (content[:60] + "…") if len(content) > 60 else content
    db.commit()
    db.refresh(user_msg)

    # Histórico para o modelo (apenas user/assistant)
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
        if m.role in ("user", "assistant")
    ]

    machine = conv.machine
    reply_text = generate_reply(
        history=history,
        plan_type=user.plan_type,
        machine_name=machine.name if machine else None,
        specs=machine.specs if machine else None,
    )

    # 4) Grava a resposta do Chip
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatOut(
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(assistant_msg),
        usage=get_usage(db, user),
        demo_mode=settings.demo_mode,
    )
