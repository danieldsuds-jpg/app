/* =====================================================================
   PerformanceAI — frontend em JavaScript puro (sem frameworks)

   Passo a passo para iniciantes:
   1. "state" guarda o que o app precisa lembrar (token, usuário, PCs, conversas).
   2. "api()" é a única função que fala com o backend (fetch + token JWT).
   3. Cada tela tem funções de "render" (desenhar) e "handlers" (reagir a cliques).
   4. O token fica no localStorage: ao recarregar a página, continuamos logados.
   ===================================================================== */

"use strict";

// ---------------------------------------------------------------------
// Estado global
// ---------------------------------------------------------------------
const state = {
  token: localStorage.getItem("pai_token") || null,
  user: null,
  config: { demo_mode: false, free_monthly_limit: 20 },
  machines: [],
  conversations: [],
  currentConversation: null,
  selectedMachineId: null, // PC usado ao criar uma nova conversa
  usage: null,
};

// Atalho para document.querySelector
const $ = (sel) => document.querySelector(sel);

// ---------------------------------------------------------------------
// Chamadas à API
// ---------------------------------------------------------------------
async function api(path, { method = "GET", body = null, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;

  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });

  // 204 = sucesso sem conteúdo (ex.: DELETE)
  if (res.status === 204) return null;

  let data = null;
  try { data = await res.json(); } catch { /* resposta sem JSON */ }

  if (!res.ok) {
    // Sessão expirada → volta para a tela de login
    if (res.status === 401 && auth) { logout(false); }
    const err = new Error(extractDetail(data) || `Erro ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

// O FastAPI devolve erros em "detail": pode ser texto, objeto ou lista (validação).
function extractDetail(data) {
  if (!data || !data.detail) return "";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg).join("; ");
  if (data.detail.message) return data.detail.message;
  return JSON.stringify(data.detail);
}

// ---------------------------------------------------------------------
// Utilidades de interface
// ---------------------------------------------------------------------
function showToast(text, ms = 3000) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.remove("is-hidden");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => t.classList.add("is-hidden"), ms);
}

function showView(name) {
  $("#view-auth").classList.toggle("is-hidden", name !== "auth");
  $("#view-app").classList.toggle("is-hidden", name !== "app");
}

function openSidebar(open) {
  $("#sidebar").classList.toggle("is-open", open);
  $("#sidebar-backdrop").classList.toggle("is-open", open);
}

// Escapa HTML para evitar que texto do usuário vire código na página (segurança).
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Converte um Markdown bem simples (negrito, código, listas, parágrafos) em HTML.
function renderMarkdown(text) {
  const lines = escapeHtml(text).split("\n");
  let html = "", inList = null;
  const closeList = () => { if (inList) { html += `</${inList}>`; inList = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const ol = line.match(/^\s*(\d+)[.)]\s+(.*)/);
    const ul = line.match(/^\s*[-*•]\s+(.*)/);
    if (ol) { if (inList !== "ol") { closeList(); html += "<ol>"; inList = "ol"; } html += `<li>${inline(ol[2])}</li>`; }
    else if (ul) { if (inList !== "ul") { closeList(); html += "<ul>"; inList = "ul"; } html += `<li>${inline(ul[1])}</li>`; }
    else if (line.trim() === "") { closeList(); }
    else { closeList(); html += `<p>${inline(line.replace(/^#+\s*/, ""))}</p>`; }
  }
  closeList();
  return html;
  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " " +
    d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------
// Autenticação
// ---------------------------------------------------------------------
function setupAuthTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      const isLogin = tab.dataset.tab === "login";
      $("#form-login").classList.toggle("is-hidden", !isLogin);
      $("#form-register").classList.toggle("is-hidden", isLogin);
      $("#auth-error").textContent = "";
    });
  });
}

async function handleAuth(e, path) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  $("#auth-error").textContent = "";
  try {
    const data = await api(path, {
      method: "POST", auth: false,
      body: { email: form.email.value.trim(), password: form.password.value },
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem("pai_token", state.token);
    form.reset();
    await enterApp();
  } catch (err) {
    $("#auth-error").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

function logout(callServer = true) {
  if (callServer && state.token) api("/auth/logout", { method: "POST" }).catch(() => {});
  state.token = null; state.user = null; state.currentConversation = null;
  state.machines = []; state.conversations = [];
  localStorage.removeItem("pai_token");
  $("#messages").innerHTML = "";
  showView("auth");
}

// ---------------------------------------------------------------------
// Entrada no app: carrega tudo que a tela precisa
// ---------------------------------------------------------------------
async function enterApp() {
  showView("app");
  try {
    state.config = await api("/config", { auth: false });
    $("#demo-banner").classList.toggle("is-hidden", !state.config.demo_mode);
    if (!state.user) state.user = await api("/auth/me");
    await Promise.all([loadMachines(), loadConversations(), loadPlan()]);
    renderChat();
  } catch (err) {
    showToast(err.message);
  }
}

async function loadPlan() {
  const plan = await api("/plan");
  state.usage = plan.usage;
  renderUsage();
}

function renderUsage() {
  const u = state.usage;
  if (!u) return;
  const pill = $("#usage-pill");
  if (u.limit === null) {
    pill.textContent = "Premium · ilimitado";
    $("#plan-label").textContent = "Plano Premium";
    $("#plan-usage").textContent = `${u.used} mensagens este mês`;
  } else {
    pill.textContent = `${u.used}/${u.limit} msgs`;
    $("#plan-label").textContent = "Plano Gratuito";
    $("#plan-usage").textContent = `${u.remaining} de ${u.limit} mensagens restantes neste mês`;
  }
  pill.classList.toggle("pill--warn", u.limit_reached);
  renderLimitBox();
}

function renderLimitBox() {
  const u = state.usage;
  const box = $("#limit-box");
  const reached = !!(u && u.limit_reached);
  box.classList.toggle("is-hidden", !reached);
  if (reached) {
    $("#limit-text").textContent =
      `Você usou as ${u.limit} mensagens do plano Gratuito neste mês. Suas conversas continuam salvas e o limite renova no próximo mês.`;
  }
  $("#btn-send").disabled = reached;
  $("#chat-input").disabled = reached;
}

// ---------------------------------------------------------------------
// Máquinas (perfil do PC)
// ---------------------------------------------------------------------
async function loadMachines() {
  state.machines = await api("/machines");
  if (!state.selectedMachineId && state.machines.length) state.selectedMachineId = state.machines[0].id;
  renderMachines();
}

function renderMachines() {
  const ul = $("#machine-list");
  ul.innerHTML = "";
  if (!state.machines.length) {
    ul.innerHTML = `<li class="list__empty">Nenhum PC cadastrado. Clique em "+ PC".</li>`;
    return;
  }
  for (const m of state.machines) {
    const li = document.createElement("li");
    li.className = "list__item" + (m.id === state.selectedMachineId ? " is-active" : "");
    const specs = [m.specs.os, m.specs.cpu, m.specs.ram_gb ? `${m.specs.ram_gb} GB RAM` : ""].filter(Boolean).join(" · ");
    li.innerHTML = `<span class="grow">${escapeHtml(m.name)}<span class="sub">${escapeHtml(specs || "sem detalhes")}</span></span>
                    <button class="mini" title="Editar" aria-label="Editar PC">✎</button>`;
    li.addEventListener("click", () => { state.selectedMachineId = m.id; renderMachines(); showToast(`PC selecionado: ${m.name}`); });
    li.querySelector(".mini").addEventListener("click", (e) => { e.stopPropagation(); openMachineModal(m); });
    ul.appendChild(li);
  }
}

function openMachineModal(machine = null) {
  const form = $("#form-machine");
  form.reset();
  form.id.value = machine ? machine.id : "";
  $("#modal-machine-title").textContent = machine ? "Editar PC" : "Cadastrar PC";
  $("#btn-machine-delete").classList.toggle("is-hidden", !machine);
  if (machine) {
    form.name.value = machine.name;
    for (const key of ["os", "cpu", "ram_gb", "storage", "gpu", "age", "main_use", "symptoms"]) {
      if (form[key]) form[key].value = machine.specs[key] || "";
    }
  }
  $("#modal-machine").classList.remove("is-hidden");
  form.name.focus();
}

async function saveMachine(e) {
  e.preventDefault();
  const form = e.target;
  const body = {
    name: form.name.value.trim(),
    specs: {
      os: form.os.value, cpu: form.cpu.value.trim(), ram_gb: form.ram_gb.value,
      storage: form.storage.value.trim(), gpu: form.gpu.value.trim(), age: form.age.value,
      main_use: form.main_use.value, symptoms: form.symptoms.value.trim(),
    },
  };
  try {
    const id = form.id.value;
    const saved = id
      ? await api(`/machines/${id}`, { method: "PUT", body })
      : await api("/machines", { method: "POST", body });
    state.selectedMachineId = saved.id;
    $("#modal-machine").classList.add("is-hidden");
    await loadMachines();
    showToast("PC salvo. O Chip vai usar essas informações nas próximas conversas.");
  } catch (err) {
    showToast(err.message);
  }
}

async function deleteMachine() {
  const id = $("#form-machine").id.value;
  if (!id || !confirm("Excluir este PC? As conversas antigas continuam salvas.")) return;
  try {
    await api(`/machines/${id}`, { method: "DELETE" });
    if (state.selectedMachineId === id) state.selectedMachineId = null;
    $("#modal-machine").classList.add("is-hidden");
    await loadMachines();
  } catch (err) { showToast(err.message); }
}

// ---------------------------------------------------------------------
// Conversas
// ---------------------------------------------------------------------
async function loadConversations() {
  state.conversations = await api("/conversations");
  renderConversations();
}

function renderConversations() {
  const ul = $("#conv-list");
  ul.innerHTML = "";
  if (!state.conversations.length) {
    ul.innerHTML = `<li class="list__empty">Nenhuma conversa ainda.</li>`;
    return;
  }
  for (const c of state.conversations) {
    const li = document.createElement("li");
    const active = state.currentConversation && c.id === state.currentConversation.id;
    li.className = "list__item" + (active ? " is-active" : "");
    const machine = state.machines.find((m) => m.id === c.machine_id);
    li.innerHTML = `<span class="grow">${escapeHtml(c.title)}<span class="sub">${formatDate(c.created_at)}${machine ? " · " + escapeHtml(machine.name) : ""}</span></span>
                    <button class="mini" title="Excluir" aria-label="Excluir conversa">🗑</button>`;
    li.addEventListener("click", () => openConversation(c));
    li.querySelector(".mini").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Excluir esta conversa?")) return;
      try {
        await api(`/conversations/${c.id}`, { method: "DELETE" });
        if (active) state.currentConversation = null;
        await loadConversations();
        renderChat();
      } catch (err) { showToast(err.message); }
    });
    ul.appendChild(li);
  }
}

async function newConversation() {
  try {
    const conv = await api("/conversations", { method: "POST", body: { machine_id: state.selectedMachineId } });
    state.currentConversation = conv;
    await loadConversations();
    renderChat();
    // Mensagem de boas-vindas local (não é gravada no banco e não consome o limite)
    const machine = state.machines.find((m) => m.id === conv.machine_id);
    const intro = machine
      ? `Oi! Eu sou o Chip. Vi que esta conversa é sobre **${machine.name}**. Me conta o que está acontecendo com ele — lentidão, travamentos, demora para ligar?`
      : "Oi! Eu sou o Chip. Para te ajudar melhor, me diga qual é o sistema operacional do seu PC (Windows 10, 11, Linux...) e o que está acontecendo com ele.";
    appendMessage({ role: "assistant", content: intro, local: true });
    openSidebar(false);
    $("#chat-input").focus();
  } catch (err) { showToast(err.message); }
}

async function openConversation(conv) {
  state.currentConversation = conv;
  renderConversations();
  renderChat();
  openSidebar(false);
  try {
    const msgs = await api(`/conversations/${conv.id}/messages`);
    $("#messages").innerHTML = "";
    msgs.forEach(appendMessage);
    scrollToBottom();
  } catch (err) { showToast(err.message); }
}

// ---------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------
function renderChat() {
  const has = !!state.currentConversation;
  $("#chat-empty").classList.toggle("is-hidden", has);
  $("#messages").classList.toggle("is-hidden", !has);
  $("#form-chat").classList.toggle("is-hidden", !has);
  if (!has) $("#messages").innerHTML = "";
  renderLimitBox();
}

function appendMessage({ role, content, local = false }) {
  const wrap = document.createElement("div");
  wrap.className = `msg msg--${role === "user" ? "user" : "assistant"}`;
  const avatar = role === "user" ? "" : `<img class="msg__avatar" src="/static/img/logo_icon.png" alt="Chip">`;
  wrap.innerHTML = `${avatar}<div class="msg__bubble">${renderMarkdown(content)}</div>`;
  if (local) wrap.dataset.local = "1";
  $("#messages").appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function scrollToBottom() {
  const m = $("#messages");
  m.scrollTop = m.scrollHeight;
}

async function sendMessage(e) {
  e.preventDefault();
  const input = $("#chat-input");
  const text = input.value.trim();
  if (!text || !state.currentConversation) return;

  input.value = ""; autoResize(input);
  $("#btn-send").disabled = true;
  appendMessage({ role: "user", content: text });
  const typing = appendMessage({ role: "assistant", content: "Chip está digitando…" });
  typing.classList.add("msg--typing");

  try {
    const data = await api("/chat", {
      method: "POST", body: { conversation_id: state.currentConversation.id, content: text },
    });
    typing.remove();
    appendMessage(data.assistant_message);
    state.usage = data.usage;
    renderUsage();
    // Atualiza o título da conversa na lista (o backend define pelo 1º texto)
    await loadConversations();
  } catch (err) {
    typing.remove();
    if (err.status === 429) {
      // Limite do Gratuito: o backend manda o aviso + oferta Premium
      await loadPlan();
      showToast(err.message, 5000);
    } else {
      showToast(err.message);
      $("#btn-send").disabled = false;
    }
  } finally {
    if (!(state.usage && state.usage.limit_reached)) $("#btn-send").disabled = false;
    input.focus();
  }
}

function autoResize(ta) {
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 140) + "px";
}

// ---------------------------------------------------------------------
// Inicialização: liga os eventos e decide qual tela mostrar
// ---------------------------------------------------------------------
function init() {
  setupAuthTabs();
  $("#form-login").addEventListener("submit", (e) => handleAuth(e, "/auth/login"));
  $("#form-register").addEventListener("submit", (e) => handleAuth(e, "/auth/register"));
  $("#btn-logout").addEventListener("click", () => logout(true));

  $("#btn-menu").addEventListener("click", () => openSidebar(true));
  $("#sidebar-backdrop").addEventListener("click", () => openSidebar(false));

  $("#btn-new-machine").addEventListener("click", () => openMachineModal());
  $("#form-machine").addEventListener("submit", saveMachine);
  $("#btn-machine-cancel").addEventListener("click", () => $("#modal-machine").classList.add("is-hidden"));
  $("#btn-machine-delete").addEventListener("click", deleteMachine);

  $("#btn-new-conv").addEventListener("click", newConversation);
  $("#form-chat").addEventListener("submit", sendMessage);
  const input = $("#chat-input");
  input.addEventListener("input", () => autoResize(input));
  // Enter envia; Shift+Enter quebra linha
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#form-chat").requestSubmit(); }
  });

  $("#btn-premium").addEventListener("click", () => $("#modal-premium").classList.remove("is-hidden"));
  $("#btn-premium-close").addEventListener("click", () => $("#modal-premium").classList.add("is-hidden"));

  // Fecha modais com Esc
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") document.querySelectorAll(".modal").forEach((m) => m.classList.add("is-hidden"));
  });

  if (state.token) enterApp(); else showView("auth");
}

document.addEventListener("DOMContentLoaded", init);
