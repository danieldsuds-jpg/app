"""
Schemas Pydantic — o "contrato" dos dados que entram e saem da API (RNF-06).

Passo a passo para iniciantes:
- Quando o navegador envia JSON para uma rota, o FastAPI usa estas classes
  para VALIDAR os dados (tipo, tamanho, formato de e-mail...). Se algo estiver
  errado, o FastAPI responde automaticamente com erro 422 e nem executa a rota.
- As classes com sufixo "Out" descrevem o que devolvemos ao navegador.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ----------------------------------------------------------------------------
# Autenticação
# ----------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Mínimo 8 caracteres")


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    email: str
    plan_type: str
    created_at: datetime

    model_config = {"from_attributes": True}  # permite criar a partir do objeto do banco


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----------------------------------------------------------------------------
# Perfil de máquina (Seção 2.3 — fluxo de coleta de contexto)
# ----------------------------------------------------------------------------
class MachineSpecs(BaseModel):
    """Campos opcionais: o usuário preenche o que souber."""

    os: str = Field(default="", max_length=80, description="Ex.: Windows 10, Windows 11, Ubuntu 24.04")
    cpu: str = Field(default="", max_length=120, description="Ex.: Intel Core i5-7200U")
    ram_gb: str = Field(default="", max_length=20, description="Ex.: 8")
    storage: str = Field(default="", max_length=120, description="Ex.: HDD 1 TB, SSD 240 GB")
    gpu: str = Field(default="", max_length=120, description="Ex.: Intel integrada, GTX 1050")
    age: str = Field(default="", max_length=40, description="Ex.: 2 a 5 anos")
    main_use: str = Field(default="", max_length=120, description="Ex.: estudo, escritório, jogos")
    symptoms: str = Field(default="", max_length=500, description="Ex.: demora para ligar")


class MachineIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    specs: MachineSpecs = MachineSpecs()


class MachineOut(BaseModel):
    id: str
    name: str
    specs: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# ----------------------------------------------------------------------------
# Conversas e mensagens
# ----------------------------------------------------------------------------
class ConversationIn(BaseModel):
    machine_id: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    machine_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatIn(BaseModel):
    conversation_id: str
    content: str = Field(min_length=1, max_length=4000)


class UsageOut(BaseModel):
    """Quantas mensagens o usuário já usou no mês (plano Gratuito)."""

    plan_type: str
    used: int
    limit: int | None        # None = ilimitado (Premium)
    remaining: int | None
    limit_reached: bool


class ChatOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    usage: UsageOut
    demo_mode: bool


# ----------------------------------------------------------------------------
# Plano
# ----------------------------------------------------------------------------
class PlanOut(BaseModel):
    plan_type: str
    usage: UsageOut
    premium_price: str
    premium_promo_price: str
    premium_available: bool = False  # pagamento NÃO implementado nesta sprint
