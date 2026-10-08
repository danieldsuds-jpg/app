"""
Rotas de autenticação: /auth/register, /auth/login, /auth/logout, /auth/me (RF-01, RF-02).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from backend.security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    """Cria a conta. O e-mail é normalizado para minúsculas e precisa ser único."""
    email = data.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Este e-mail já está cadastrado.")

    user = User(email=email, password_hash=hash_password(data.password), plan_type="free")
    db.add(user)
    db.commit()
    db.refresh(user)
    # Já devolvemos o token: a pessoa entra logada após o cadastro.
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    """Confere e-mail + senha e devolve o token de sessão."""
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    # Mesma mensagem para e-mail inexistente ou senha errada (não revela qual falhou).
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """Com JWT sem estado, o logout real acontece no navegador (apaga o token).
    A rota existe para o frontend confirmar que a sessão era válida."""
    return {"ok": True, "message": "Sessão encerrada. Até logo!"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Dados do usuário logado (usado ao recarregar a página)."""
    return user
