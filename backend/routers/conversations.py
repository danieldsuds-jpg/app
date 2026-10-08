"""
Rotas de histórico: /conversations (RF-04, RF-06).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Conversation, Machine, User
from backend.schemas import ConversationIn, ConversationOut, MessageOut
from backend.security import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversas"])


def get_owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    """Busca a conversa e garante que pertence ao usuário logado."""
    conv = db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lista as conversas do usuário, da mais recente para a mais antiga."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Abre uma nova conversa, opcionalmente ligada a um PC cadastrado."""
    machine_id = None
    if data.machine_id:
        machine = db.get(Machine, data.machine_id)
        if machine is None or machine.user_id != user.id:
            raise HTTPException(status_code=404, detail="Máquina não encontrada.")
        machine_id = machine.id
    conv = Conversation(user_id=user.id, machine_id=machine_id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reabre uma conversa: devolve todas as mensagens em ordem cronológica."""
    conv = get_owned_conversation(db, user, conversation_id)
    return conv.messages


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = get_owned_conversation(db, user, conversation_id)
    db.delete(conv)
    db.commit()
