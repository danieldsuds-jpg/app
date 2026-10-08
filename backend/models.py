"""
Modelos (tabelas) do banco — segue o modelo ER da Seção 4.3 da documentação.

Tabelas:
- users         : contas (e-mail, hash da senha, plano free/premium)
- machines      : perfis de PC do usuário (specs em JSON)
- conversations : conversas com o Chip (ligadas a um usuário e, opcionalmente, a um PC)
- messages      : mensagens de cada conversa (user / assistant / system)

Passo a passo para iniciantes:
- Cada classe vira uma tabela; cada atributo `Mapped[...]` vira uma coluna.
- Usamos UUID (texto de 36 caracteres) como chave primária, como pede o documento.
- `relationship` cria "atalhos" para navegar entre tabelas (ex.: user.machines).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def new_uuid() -> str:
    """Gera um identificador único (UUID v4) como texto."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Data/hora atual em UTC (padrão para gravar no banco)."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Plano do usuário: "free" ou "premium" (RNF-10). Guardado como texto para
    # funcionar igual no SQLite e no PostgreSQL.
    plan_type: Mapped[str] = mapped_column(String(10), default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    machines: Mapped[list["Machine"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # specs: dicionário com SO, CPU, RAM, armazenamento, GPU, idade, uso, sintomas.
    # JSON funciona no SQLite e vira JSON/JSONB no PostgreSQL.
    specs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="machines")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="machine")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    # machine_id pode ser nulo: o usuário pode conversar sem cadastrar um PC.
    machine_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(120), default="Nova conversa")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="conversations")
    machine: Mapped["Machine | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), index=True
    )
    # Papel no chat: "user" (pessoa), "assistant" (Chip) ou "system".
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
