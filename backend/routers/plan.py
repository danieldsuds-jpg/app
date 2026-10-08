"""
Rotas de plano: GET /plan e POST /plan/upgrade (vitrine — pagamento fica para depois).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import PlanOut
from backend.security import get_current_user
from backend.services.usage import get_usage

router = APIRouter(prefix="/plan", tags=["Plano"])


@router.get("", response_model=PlanOut)
def get_plan(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return PlanOut(
        plan_type=user.plan_type,
        usage=get_usage(db, user),
        premium_price=settings.premium_price,
        premium_promo_price=settings.premium_promo_price,
        premium_available=False,
    )


@router.post("/upgrade", status_code=501)
def upgrade(user: User = Depends(get_current_user)):
    """Ainda não implementado (decisão da Sprint 2: Premium é vitrine "em breve")."""
    raise HTTPException(
        status_code=501,
        detail="O plano Premium está em breve. O pagamento ainda não está disponível nesta versão.",
    )
