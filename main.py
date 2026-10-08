"""
Ponto de entrada do PerformanceAI.

Como rodar localmente:
    uvicorn main:app --reload --port 3000

Passo a passo para iniciantes:
1. Criamos o app FastAPI e registramos as rotas da API (backend/routers/*).
2. Na inicialização, criamos as tabelas do banco se ainda não existirem.
3. O FastAPI também serve o frontend (pasta static/): "/" devolve o index.html.
4. /health é usado pelo Render para saber se o serviço está no ar.
5. /docs (gerado automaticamente) mostra a documentação interativa da API.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import create_tables
from backend.routers import auth, chat, conversations, machines, plan

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Código executado uma vez quando o servidor sobe (antes do yield) e ao desligar (depois)."""
    create_tables()
    modo = "DEMONSTRAÇÃO (sem OPENAI_API_KEY)" if settings.demo_mode else f"OpenAI ({settings.openai_model})"
    print(f"[PerformanceAI] Chip em modo: {modo}")
    yield


app = FastAPI(
    title="PerformanceAI — Chip",
    description="Assistente de IA para otimizar PCs. Slogan: Mais rápido. Sem trocar tudo.",
    version="0.2.0 (Sprint 2 — MVP)",
    lifespan=lifespan,
)

# Rotas da API
app.include_router(auth.router)
app.include_router(machines.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(plan.router)


@app.get("/health", tags=["Infra"])
def health():
    """Health check (Render). Também informa se o Chip está em modo demonstração."""
    return {"status": "ok", "demo_mode": settings.demo_mode, "model": settings.openai_model}


@app.get("/config", tags=["Infra"])
def public_config():
    """Configurações públicas usadas pelo frontend (sem segredos)."""
    return {
        "demo_mode": settings.demo_mode,
        "free_monthly_limit": settings.free_monthly_limit,
        "premium_price": settings.premium_price,
        "premium_promo_price": settings.premium_promo_price,
    }


# Frontend: arquivos estáticos (CSS, JS, imagens) e a página inicial
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "img" / "favicon.ico")
