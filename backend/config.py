"""
Configurações do PerformanceAI.

Passo a passo para iniciantes:
1. Todos os valores sensíveis (chave da OpenAI, segredo do JWT, URL do banco)
   são lidos de VARIÁVEIS DE AMBIENTE. Em desenvolvimento, elas vêm do arquivo
   ".env" (carregado automaticamente pela biblioteca pydantic-settings).
2. Nada de segredo fica escrito no código. Se uma variável não existir,
   usamos um valor padrão seguro para desenvolvimento.
3. Para usar: `from backend.config import settings` e depois `settings.openai_api_key`.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Pasta raiz do projeto (a pasta que contém main.py)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Cada atributo abaixo corresponde a uma variável de ambiente de mesmo nome
    (sem diferenciar maiúsculas/minúsculas). Ex.: OPENAI_API_KEY -> openai_api_key."""

    # --- OpenAI ---------------------------------------------------------------
    openai_api_key: str = ""            # vazio = modo demonstração (sem chamar a OpenAI)
    openai_model: str = "gpt-4o-mini"   # modelo configurável

    # --- Banco de dados -------------------------------------------------------
    # Vazio = SQLite local (arquivo performanceai.db). No Render recebe a URL do PostgreSQL.
    database_url: str = ""

    # --- Sessão (JWT) ---------------------------------------------------------
    jwt_secret: str = "dev-segredo-inseguro-troque-no-arquivo-.env-por-favor"
    jwt_expire_hours: int = 72

    # --- Regras de negócio (decisões do time, 08/10/2026) ---------------------
    free_monthly_limit: int = 20                 # mensagens/mês no plano Gratuito
    premium_price: str = "R$ 24,90/mês"
    premium_promo_price: str = "R$ 19,90/mês"   # promoção de lançamento

    # Diz ao pydantic-settings para ler o arquivo .env na raiz do projeto
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def demo_mode(self) -> bool:
        """True quando não há chave da OpenAI: o Chip responde com texto simulado."""
        return not self.openai_api_key.strip()

    @property
    def effective_database_url(self) -> str:
        """Resolve a URL do banco.

        - Sem DATABASE_URL: SQLite local para desenvolvimento.
        - Com DATABASE_URL no formato antigo "postgres://" (comum no Render):
          converte para "postgresql://", que é o que o SQLAlchemy entende.
        """
        url = self.database_url.strip()
        if not url:
            return f"sqlite:///{BASE_DIR / 'performanceai.db'}"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


# Instância única usada por todo o app
settings = Settings()
