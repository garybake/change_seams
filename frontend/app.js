'use strict';

const sessionId = crypto.randomUUID();
let isLoading = false;

// ── DOM refs ──────────────────────────────────────────────────────────────
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('msg-input');
const sendBtn = document.getElementById('send-btn');
const traceContent = document.getElementById('trace-content');
const traceIdDisplay = document.getElementById('trace-id-display');
const tokenSummary = document.getElementById('token-summary');
const configSummary = document.getElementById('config-summary');

// ── Load runtime config on startup ───────────────────────────────────────
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    configSummary.textContent =
      `${cfg.llm_provider}/${cfg.llm_model} · tools: ${cfg.enabled_tools.join(', ')} · ${cfg.policy_mode}`;
  } catch {
    configSummary.textContent = 'config unavailable';
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────
function appendMessage(role, text) {
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isLoading) return;

  isLoading = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  appendMessage('user', text);
  const thinking = appendMessage('thinking', '…');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });

    if (!res.ok) {
      const err = await res.text();
      thinking.remove();
      appendMessage('agent', `Error ${res.status}: ${err}`);
      return;
    }

    const data = await res.json();
    thinking.remove();
    appendMessage('agent', data.answer);
    renderTrace(data);
  } catch (err) {
    thinking.remove();
    appendMessage('agent', `Request failed: ${err.message}`);
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

// ── Trace panel ───────────────────────────────────────────────────────────
function renderTrace(data) {
  traceIdDisplay.textContent = data.trace_id ? data.trace_id.slice(0, 8) + '…' : '';
  traceContent.innerHTML = '';

  if (!data.spans || data.spans.length === 0) {
    traceContent.innerHTML = '<div class="trace-placeholder">No spans captured.</div>';
  } else {
    data.spans.forEach(span => traceContent.appendChild(buildSpanCard(span)));
  }

  // Token summary
  const u = data.token_usage || {};
  if (u.total_tokens) {
    tokenSummary.innerHTML =
      `<strong>${u.prompt_tokens ?? 0}</strong> prompt + ` +
      `<strong>${u.completion_tokens ?? 0}</strong> completion = ` +
      `<strong>${u.total_tokens}</strong> total tokens`;
    tokenSummary.style.display = 'flex';
  } else {
    tokenSummary.style.display = 'none';
  }
}

function buildSpanCard(span) {
  const isTool = span.name.startsWith('tool.');
  const isLlm = span.name.startsWith('llm.');

  const card = document.createElement('div');
  card.className = `span-card${isTool ? ' tool' : ''}${isLlm ? ' llm' : ''}`;

  const header = document.createElement('div');
  header.className = 'span-header';

  const nameEl = document.createElement('span');
  nameEl.className = 'span-name';
  nameEl.textContent = span.name;

  const latencyEl = document.createElement('span');
  latencyEl.className = 'span-latency';
  latencyEl.textContent = span.latency_ms != null ? `${span.latency_ms}ms` : '';

  const toggle = document.createElement('span');
  toggle.className = 'span-toggle';
  toggle.textContent = '▶';

  header.append(nameEl, latencyEl, toggle);

  const body = document.createElement('div');
  body.className = 'span-body';

  // Render attributes as chips
  const attrs = span.attributes || {};
  const attrRow = document.createElement('div');
  attrRow.className = 'attr-row';

  Object.entries(attrs).forEach(([k, v]) => {
    if (v === null || v === undefined || v === 0 && k.includes('tokens') && !String(v)) return;
    const chip = document.createElement('div');
    chip.className = 'attr-chip';
    chip.title = `${k}=${v}`;
    chip.innerHTML = `${escHtml(k)}=<span>${escHtml(String(v))}</span>`;
    attrRow.appendChild(chip);
  });

  body.appendChild(attrRow);
  card.append(header, body);

  // Toggle expand/collapse
  header.addEventListener('click', () => {
    const open = body.classList.toggle('open');
    toggle.classList.toggle('open', open);
  });

  return card;
}

function escHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Input handling ────────────────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

// ── Init ──────────────────────────────────────────────────────────────────
loadConfig();
inputEl.focus();
