"""
Controle do limite mensal do plano Gratuito (20 mensagens/mês — decisão do time).

Passo a passo para iniciantes:
- Contamos quantas mensagens com role="user" o usuário enviou desde o 1º dia
  do mês atual (UTC). Não há tabela extra: a própria tabela messages é a fonte.
- Premium: sem limite (limit = None).
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Conversation, Message, User
from backend.schemas import UsageOut


def month_start() -> datetime:
    """Primeiro instante do mês atual, em UTC."""
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def count_user_messages_this_month(db: Session, user: User) -> int:
    """Quantas mensagens o usuário enviou ao Chip neste mês."""
    stmt = (
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.user_id == user.id,
            Message.role == "user",
            Message.created_at >= month_start(),
        )
    )
    return int(db.execute(stmt).scalar_one())


def get_usage(db: Session, user: User) -> UsageOut:
    """Resumo de uso para o frontend mostrar "X de 20 mensagens"."""
    used = count_user_messages_this_month(db, user)
    if user.plan_type == "premium":
        return UsageOut(plan_type="premium", used=used, limit=None, remaining=None, limit_reached=False)
    limit = settings.free_monthly_limit
    return UsageOut(
        plan_type="free",
        used=used,
        limit=limit,
        remaining=max(limit - used, 0),
        limit_reached=used >= limit,
    )
