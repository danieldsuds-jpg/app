"""
Serviço de IA — monta o prompt do Chip e chama a OpenAI (ou simula, em modo demo).

Passo a passo para iniciantes:
1. `load_system_prompt()` lê o arquivo backend/prompts/chip_system_prompt.md
   (a persona, as regras e a base de conhecimento) e remove os comentários HTML.
2. `build_context_block()` acrescenta o contexto do usuário: plano (free/premium)
   e o perfil da máquina, para o Chip explicar POR QUE cada dica serve àquele PC.
3. `generate_reply()` envia tudo à OpenAI. Se não houver OPENAI_API_KEY,
   devolve uma resposta simulada clara — assim o app roda e pode ser testado
   sem gastar créditos.

Toda a integração com a IA fica isolada aqui (mitigação do risco de dependência
da OpenAI, Seção 8.2): trocar de provedor no futuro = alterar só este arquivo.
"""

import re
from functools import lru_cache
from pathlib import Path

from backend.config import settings

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "chip_system_prompt.md"

# Quantas mensagens anteriores da conversa enviamos ao modelo (controle de custo).
HISTORY_WINDOW = 20

# Rótulos em português para exibir o perfil da máquina no prompt.
SPEC_LABELS = {
    "os": "Sistema operacional",
    "cpu": "Processador",
    "ram_gb": "Memória RAM (GB)",
    "storage": "Armazenamento",
    "gpu": "Placa de vídeo",
    "age": "Idade do PC",
    "main_use": "Uso principal",
    "symptoms": "Sintomas relatados",
}


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Lê o arquivo do prompt uma vez e guarda em cache (reinicie o servidor após editar)."""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    # Remove comentários HTML <!-- ... --> (são instruções para quem edita, não para o modelo)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def build_context_block(plan_type: str, machine_name: str | None, specs: dict | None) -> str:
    """Monta o bloco "CONTEXTO DO USUÁRIO" anexado ao final do system prompt."""
    lines = ["", "## CONTEXTO DO USUÁRIO (preenchido pelo sistema)"]
    lines.append(f"- plan_type: {plan_type}")
    if plan_type == "free":
        lines.append(
            "- Regras ativas: plano Gratuito — NÃO orientar BIOS/firmware; "
            "conteúdo educativo liberado; Premium é 'em breve'."
        )
    else:
        lines.append("- Regras ativas: plano Premium — lista aprovada de BIOS liberada com alertas.")

    if specs and any(str(v).strip() for v in specs.values()):
        lines.append(f"- Perfil da máquina: {machine_name or 'PC do usuário'}")
        for key, label in SPEC_LABELS.items():
            value = str(specs.get(key, "")).strip()
            if value:
                lines.append(f"  - {label}: {value}")
        lines.append(
            "- Use esse perfil para personalizar cada dica e explicar por que ela serve a esta máquina. "
            "Não pergunte novamente o que já está informado."
        )
    else:
        lines.append(
            "- Nenhum perfil de máquina informado. Colete o contexto de forma progressiva antes de recomendar."
        )
    return "\n".join(lines)


def demo_reply(user_text: str, specs: dict | None) -> str:
    """Resposta simulada usada quando não há chave da OpenAI (modo demonstração)."""
    resumo = ""
    if specs:
        partes = [str(specs.get(k, "")).strip() for k in ("os", "cpu", "storage")]
        if str(specs.get("ram_gb", "")).strip():
            partes.append(f"{specs['ram_gb']} GB de RAM")
        partes = [p for p in partes if p]
        if partes:
            resumo = f" Vi no seu perfil: {', '.join(partes)}."
    return (
        "**[MODO DEMONSTRAÇÃO]** A chave da OpenAI não está configurada, então esta resposta é simulada "
        "— nenhuma IA foi consultada.\n\n"
        f"Você escreveu: \"{user_text[:200]}\".{resumo}\n\n"
        "Quando a variável OPENAI_API_KEY estiver no arquivo .env (ou no painel do Render), "
        "eu, o Chip, vou responder de verdade: primeiro pergunto o que falta sobre sua máquina, "
        "depois sugiro as ações gratuitas e seguras e explico por que cada uma serve ao seu PC."
    )


def generate_reply(
    history: list[dict],
    plan_type: str,
    machine_name: str | None,
    specs: dict | None,
) -> str:
    """Gera a resposta do Chip.

    history: lista de dicts {"role": "user"|"assistant", "content": "..."} em ordem
             cronológica, incluindo a mensagem nova do usuário no final.
    """
    if settings.demo_mode:
        return demo_reply(history[-1]["content"] if history else "", specs)

    # Importa aqui para o app funcionar mesmo sem a biblioteca em modo demo.
    from openai import OpenAI

    system_prompt = load_system_prompt() + "\n" + build_context_block(plan_type, machine_name, specs)
    messages = [{"role": "system", "content": system_prompt}]
    messages += history[-HISTORY_WINDOW:]

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.4,      # respostas mais consistentes para um assistente técnico
            max_tokens=900,
        )
        return (completion.choices[0].message.content or "").strip() or (
            "Desculpe, não consegui gerar uma resposta agora. Pode tentar de novo?"
        )
    except Exception as exc:  # noqa: BLE001 — qualquer falha da API vira mensagem amigável
        return (
            "Não consegui falar com o serviço de IA neste momento "
            f"(erro técnico: {type(exc).__name__}). Tente novamente em alguns instantes."
        )
