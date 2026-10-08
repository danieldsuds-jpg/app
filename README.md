# PerformanceAI — MVP da Sprint 2

**Mais rápido. Sem trocar tudo.**

Site com o **Chip**, assistente de IA que ajuda a otimizar PCs antigos e novos a partir da
configuração declarada pelo usuário — sem acesso remoto, começando sempre pelas ações
gratuitas e seguras e explicando *por que* cada dica serve àquela máquina.

| Item | Tecnologia |
|---|---|
| Backend | Python 3.11 · FastAPI · Uvicorn · SQLAlchemy · Pydantic |
| Frontend | HTML, CSS e JavaScript puros (mobile-first), servidos pelo próprio FastAPI |
| Banco | PostgreSQL (Render) — SQLite automático em desenvolvimento |
| IA | OpenAI (chave e modelo via `.env`); **modo demonstração** sem chave |
| Segurança | Senhas com bcrypt (fator 12) · sessão por token JWT · segredos só no `.env` |

---

## 1. Estrutura de pastas

```
app/
├── main.py                      # Ponto de entrada: cria o app, registra rotas e serve o frontend
├── requirements.txt             # Dependências Python
├── render.yaml                  # Blueprint do Render (Web Service + PostgreSQL)
├── .env.example                 # Modelo das variáveis de ambiente (copie para .env)
├── .gitignore                   # Ignora .env, banco local, caches
├── pytest.ini                   # Configuração dos testes
├── backend/
│   ├── config.py                # Lê as variáveis do .env (Settings)
│   ├── database.py              # Conexão com o banco (PostgreSQL ou SQLite)
│   ├── models.py                # Tabelas: users, machines, conversations, messages
│   ├── schemas.py               # Validação de entrada/saída (Pydantic)
│   ├── security.py              # Hash de senha (bcrypt) e tokens JWT
│   ├── prompts/
│   │   └── chip_system_prompt.md   # PERSONA + REGRAS + BASE DE CONHECIMENTO do Chip (edite aqui)
│   ├── services/
│   │   ├── ai.py                # Monta o prompt e chama a OpenAI (ou simula em modo demo)
│   │   └── usage.py             # Contagem do limite mensal do plano Gratuito
│   └── routers/
│       ├── auth.py              # /auth/register, /auth/login, /auth/logout, /auth/me
│       ├── machines.py          # /machines (perfil do PC)
│       ├── conversations.py     # /conversations e /conversations/{id}/messages
│       ├── chat.py              # /chat (fala com o Chip + limite de 20 msgs)
│       └── plan.py              # /plan e /plan/upgrade (vitrine Premium)
├── static/
│   ├── index.html               # Única página: landing + login/cadastro + app de chat
│   ├── css/style.css            # Estilos mobile-first com a paleta da marca
│   ├── js/app.js                # Lógica do frontend (fetch + token)
│   └── img/                     # Logos e favicons (copiados de /branding)
└── tests/
    ├── conftest.py              # Banco SQLite em memória + cliente de teste
    ├── test_auth.py             # Cadastro e login
    └── test_chat.py             # Chat em modo demo, histórico, limite de 20 mensagens
```

---

## 2. Como rodar localmente

Pré-requisito: Python 3.11+.

```bash
# 1) Entre na pasta do projeto
cd app

# 2) (Opcional, recomendado) crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3) Instale as dependências
pip install -r requirements.txt

# 4) Crie o arquivo .env a partir do modelo
cp .env.example .env             # Windows: copy .env.example .env

# 5) Suba o servidor
uvicorn main:app --reload --port 3000
```

Abra **http://localhost:3000** no navegador. A documentação interativa da API fica em
**http://localhost:3000/docs**.

- Sem `OPENAI_API_KEY` no `.env`, o app roda em **modo demonstração**: o Chip responde com um
  texto simulado identificado como tal. Serve para testar cadastro, login, chat e histórico.
- Sem `DATABASE_URL`, o app cria o arquivo `performanceai.db` (SQLite). Em produção use PostgreSQL.

### Rodar os testes

```bash
python -m pytest
```

Os testes usam SQLite em memória e modo demonstração — não precisam de banco nem de chave.

---

## 3. Variáveis do `.env`

| Variável | Obrigatória? | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | Não (recomendada) | Chave da OpenAI. Vazia = modo demonstração. |
| `OPENAI_MODEL` | Não | Modelo usado pelo Chip. Padrão: `gpt-4o-mini`. |
| `DATABASE_URL` | Não local / **Sim no Render** | URL do PostgreSQL. Vazia = SQLite local. |
| `JWT_SECRET` | **Sim** (em produção) | Segredo que assina os tokens de sessão. Gere com `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `JWT_EXPIRE_HOURS` | Não | Validade da sessão em horas. Padrão: `72`. |
| `FREE_MONTHLY_LIMIT` | Não | Mensagens/mês do plano Gratuito. Padrão: `20`. |

> O arquivo `.env` **nunca** deve ir para o GitHub. Ele já está no `.gitignore`.

---

## 4. Como funciona (resumo para iniciantes)

1. **Cadastro/login** (`backend/routers/auth.py`): a senha vira um hash bcrypt; o login devolve um
   token JWT que o navegador guarda no `localStorage` e envia em todas as requisições.
2. **Perfil do PC** (`/machines`): SO, CPU, RAM, armazenamento, GPU, idade, uso e sintomas.
3. **Conversa** (`/conversations`): pode ser ligada a um PC. Todas as mensagens ficam no banco.
4. **Chat** (`/chat`): o backend monta o *system prompt* a partir de
   `backend/prompts/chip_system_prompt.md` + o contexto do usuário (plano e máquina), envia o
   histórico à OpenAI e grava a resposta. No plano Gratuito, após 20 mensagens no mês, responde
   `429` com o aviso e a oferta do Premium (R$ 24,90/mês; promoção de lançamento R$ 19,90/mês).
5. **Premium**: ainda não tem pagamento. Aparece como vitrine "em breve"; `POST /plan/upgrade`
   responde `501`.

Para mudar a persona, as regras ou a base de conhecimento do Chip, edite apenas
`backend/prompts/chip_system_prompt.md` e reinicie o servidor.

---

## 5. Subir no GitHub

O repositório Git local já está iniciado com um commit. Para publicar:

1. Crie um repositório vazio no GitHub (ex.: `performanceai`), **sem** README nem .gitignore.
2. No terminal, dentro da pasta `app`:

```bash
git remote add origin https://github.com/SEU-USUARIO/performanceai.git
git branch -M main
git push -u origin main
```

Confirme no GitHub que o arquivo `.env` **não** foi enviado (só o `.env.example`).

---

## 6. Deploy no Render (Web Service + PostgreSQL)

### Opção A — Blueprint (mais rápida)

1. No painel do Render: **New → Blueprint**.
2. Conecte o repositório do GitHub. O Render lê o `render.yaml` e propõe criar:
   - o Web Service `performanceai` (Python, `uvicorn main:app --host 0.0.0.0 --port $PORT`);
   - o banco PostgreSQL `performanceai-db` (a `DATABASE_URL` é ligada automaticamente).
3. Quando pedir, preencha `OPENAI_API_KEY` (marcada como `sync: false`, ou seja, manual).
4. Clique em **Apply**. Aguarde o build. A URL pública aparece no topo do serviço.

### Opção B — Manual

1. **New → PostgreSQL**: nome `performanceai-db`, plano Free. Copie a **Internal Database URL**.
2. **New → Web Service** → conecte o repositório.
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/health`
3. Em **Environment**, adicione:
   - `DATABASE_URL` = Internal Database URL copiada
   - `JWT_SECRET` = valor longo e aleatório
   - `OPENAI_API_KEY` = sua chave
   - `OPENAI_MODEL` = `gpt-4o-mini`
   - `PYTHON_VERSION` = `3.11.6`
4. **Create Web Service**. As tabelas são criadas automaticamente na primeira inicialização.

Checagens após o deploy:
- `https://SEU-APP.onrender.com/health` deve responder `{"status":"ok","demo_mode":false,...}`.
- Se `demo_mode` vier `true`, a `OPENAI_API_KEY` não foi lida — confira a variável no painel.
- No plano Free do Render o serviço "dorme" após inatividade; a primeira visita pode demorar
  alguns segundos.

---

## 7. Endpoints da API

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/register` | — | Cadastro (devolve token) |
| POST | `/auth/login` | — | Login (devolve token) |
| POST | `/auth/logout` | ✓ | Encerra sessão (token descartado no navegador) |
| GET | `/auth/me` | ✓ | Usuário logado |
| GET/POST | `/machines` | ✓ | Lista / cria perfil de PC |
| PUT/DELETE | `/machines/{id}` | ✓ | Atualiza / remove PC |
| GET/POST | `/conversations` | ✓ | Lista / cria conversa |
| GET | `/conversations/{id}/messages` | ✓ | Reabre conversa |
| DELETE | `/conversations/{id}` | ✓ | Exclui conversa |
| POST | `/chat` | ✓ | Envia mensagem ao Chip (429 ao atingir o limite Gratuito) |
| GET | `/plan` | ✓ | Plano atual e uso do mês |
| POST | `/plan/upgrade` | ✓ | Ainda não disponível (501) |
| GET | `/health` | — | Health check |
| GET | `/config` | — | Configurações públicas para o frontend |

---

## 8. O que ficou fora desta sprint (planejado)

- Pagamento e ativação do Premium (vitrine "em breve").
- Guia de BIOS Premium, termo de aceite e playbooks (Atlas OS/ReviOS).
- Recuperação de senha, exportar conversa, prova social (RF-09, RF-10, RF-12).
- Resposta em streaming (SSE) — a resposta atual chega completa de uma vez.
- Rate limiting por IP (RNF-05) e política de privacidade/exclusão de conta (RNF-07).
- Atendimento humano: **não existe e não existirá** (decisão do time). Quando não conseguir
  resolver, o Chip recomenda procurar um técnico.
