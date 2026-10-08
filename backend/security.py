"""
Segurança: hash de senha (bcrypt) e tokens de sessão (JWT).

Passo a passo para iniciantes:
1. NUNCA guardamos a senha. Guardamos um "hash" — um embaralhamento
   irreversível feito pelo bcrypt (RNF-01). No login, comparamos o hash.
2. Depois do login, entregamos um JWT: um "crachá" assinado com o JWT_SECRET.
   O navegador envia esse crachá em toda requisição (cabeçalho Authorization).
   Se alguém alterar o crachá, a assinatura não bate e ele é rejeitado (RNF-02).
3. `get_current_user` é a dependência que as rotas protegidas usam para
   descobrir quem está logado.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User

# Fator de custo do bcrypt (>= 12 conforme RNF-01). Maior = mais lento = mais seguro.
BCRYPT_ROUNDS = 12


# ----------------------------------------------------------------------------
# Senhas
# ----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Transforma a senha em hash bcrypt (com salt aleatório embutido)."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Confere se a senha digitada corresponde ao hash guardado."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ----------------------------------------------------------------------------
# Tokens JWT
# ----------------------------------------------------------------------------
def create_access_token(user_id: str) -> str:
    """Cria o token de sessão. "sub" = assunto (id do usuário); "exp" = expiração."""
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": user_id, "exp": expires, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    """Lê o token e devolve o id do usuário, ou None se for inválido/expirado."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# ----------------------------------------------------------------------------
# Dependência: usuário logado
# ----------------------------------------------------------------------------
# HTTPBearer lê o cabeçalho "Authorization: Bearer <token>".
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Devolve o usuário dono do token ou responde 401 (não autorizado)."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Faça login para continuar.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user
