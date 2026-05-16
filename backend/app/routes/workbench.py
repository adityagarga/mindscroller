"""Prompt iteration workbench.

Single-page HTML served at GET /workbench. Pick a category + topic + hook type,
tweak the system prompt and image style prefix, generate a card, see the result.

Edited prompts live in the browser's localStorage only — when you're happy,
copy them back into `app/content/prompts.py` to make them the new defaults.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.content.generator import generate_card
from app.content.prompts import IMAGE_STYLE_PREFIX, SYSTEM_PROMPT
from app.content.topics import HOOK_TYPE_SPECS, HOOK_TYPES, TAXONOMY, is_valid


router = APIRouter()


@router.get("/api/workbench/defaults")
async def get_defaults() -> dict:
    return {
        "system_prompt": SYSTEM_PROMPT,
        "style_prefix": IMAGE_STYLE_PREFIX,
    }


@router.get("/api/workbench/taxonomy")
async def get_taxonomy() -> dict:
    return {
        "taxonomy": TAXONOMY,
        "hook_types": HOOK_TYPES,
        "hook_type_specs": HOOK_TYPE_SPECS,
    }


class WorkbenchGenerateRequest(BaseModel):
    category: str
    topic: str
    hook_type: str
    system_prompt: str | None = None
    style_prefix: str | None = None
    skip_audio: bool = True
    skip_image: bool = False


@router.post("/api/workbench/generate")
async def post_generate(req: WorkbenchGenerateRequest) -> dict:
    if not is_valid(req.category, req.topic, req.hook_type):
        raise HTTPException(
            422,
            f"invalid combination: category={req.category!r} topic={req.topic!r} hook_type={req.hook_type!r}",
        )
    card = await generate_card(
        category=req.category,
        topic=req.topic,
        hook_type=req.hook_type,
        skip_audio=req.skip_audio,
        skip_image=req.skip_image,
        system_prompt_override=req.system_prompt,
        style_prefix_override=req.style_prefix,
    )
    return {"card": card}


@router.get("/workbench", response_class=HTMLResponse)
async def workbench_page() -> str:
    return _HTML


_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>mindscroller · prompt workbench</title>
<style>
  :root { color-scheme: dark; --accent: #8b5cf6; --bg: #0a0a0b; --panel: #14141a; --border: #232328; --muted: #888; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: #e9e9ea; line-height: 1.45; }
  .layout { display: grid; grid-template-columns: minmax(420px, 1fr) minmax(420px, 1fr); gap: 16px; padding: 16px; min-height: 100vh; }
  @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px; display:flex; flex-direction:column; gap: 12px; }
  h1 { font-size: 16px; margin: 0; letter-spacing: 0.02em; }
  h2 { font-size: 13px; margin: 0; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }
  label { font-size: 12px; color: var(--muted); display:block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  textarea, input[type=text], select { width:100%; background:#0d0d10; color:#e9e9ea; border:1px solid var(--border); border-radius: 6px; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; line-height: 1.5; resize: vertical; }
  textarea.system { min-height: 260px; }
  textarea.prefix { min-height: 80px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  @media (max-width: 720px) { .grid3 { grid-template-columns: 1fr; } }
  .checks { display:flex; gap: 16px; align-items: center; font-size: 13px; color: var(--muted); }
  .checks label { display:flex; align-items: center; gap: 6px; text-transform: none; letter-spacing: 0; font-size: 13px; color: #c9c9d0; margin: 0; }
  button { background: var(--accent); color: white; border: 0; padding: 10px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 14px; }
  button:hover { filter: brightness(1.1); }
  button.ghost { background: transparent; border: 1px solid var(--border); color: #c9c9d0; }
  button:disabled { opacity: 0.5; cursor: progress; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .status { font-size: 12px; color: var(--muted); }
  .status.err { color: #ef4444; }
  .result { display:flex; flex-direction:column; gap: 14px; }
  .empty { color: var(--muted); font-size: 14px; padding: 60px 20px; text-align:center; border: 1px dashed var(--border); border-radius: 8px; }
  .img-wrap { position: relative; background: #0d0d10; border-radius: 10px; overflow:hidden; aspect-ratio: 3 / 4; }
  .img-wrap img { width:100%; height:100%; object-fit: cover; display:block; }
  .visual-hook-overlay {
    position: absolute; inset: 0; display:flex; align-items: center; justify-content: center;
    text-align: center; padding: 20px;
    font-family: "Helvetica Neue", "Arial Black", Impact, "Inter", system-ui, sans-serif;
    font-weight: 900;
    font-stretch: 100%;
    text-transform: uppercase;
    font-size: clamp(34px, 9.5vw, 68px);
    line-height: 0.92;
    letter-spacing: -0.02em;
    color: white;
    -webkit-text-stroke: 1px rgba(0,0,0,0.55);
    text-shadow:
      0 0 1px rgba(0,0,0,0.95),
      3px 3px 0 rgba(0,0,0,0.75);
    background: linear-gradient(180deg, rgba(0,0,0,0) 35%, rgba(0,0,0,0.5) 100%);
  }
  .img-wrap.no-img { background: linear-gradient(135deg, #1a1a25, #0d0d12); display:flex; align-items:center; justify-content:center; }
  .script { padding: 14px 16px; background: #11111a; border-radius: 6px; font-size: 15px; line-height: 1.55; }
  .meta { display:flex; flex-wrap: wrap; gap:6px; font-size: 11px; }
  .meta span { background: #1f1f24; color: #c2c2c8; padding: 3px 8px; border-radius: 999px; }
  .meta span.cat { background: #2a1f3d; color: #d6c8ff; }
  .meta span.topic { background: #1f2a3d; color: #c8dcff; }
  .meta span.hook { background: #2a3d1f; color: #d6f0c0; }
  details { background: #0d0d10; border-radius: 6px; padding: 8px 12px; font-size: 12.5px; }
  details summary { cursor: pointer; user-select: none; color: var(--muted); }
  details pre { white-space: pre-wrap; word-break: break-word; margin: 8px 0 0; font-family: ui-monospace, monospace; color: #cfcfd6; font-size: 12px; }
  .history { display:flex; gap:8px; overflow-x: auto; padding-bottom: 4px; }
  .history .item { flex: 0 0 88px; cursor: pointer; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background:#0d0d10; position: relative; }
  .history .item img { width: 88px; height: 116px; object-fit: cover; display:block; }
  .history .item .ovl { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; text-align:center; padding:6px; font-size: 9px; color: white; font-weight:700; text-shadow: 0 1px 4px rgba(0,0,0,0.8); }
  .history .item.placeholder { display:flex; align-items:center; justify-content:center; height: 116px; color: var(--muted); font-size: 11px; padding: 8px; text-align:center; }
  .history .item.selected { border-color: var(--accent); }
  .spacer { flex: 1; }
  .dot { display:inline-block; width:6px; height:6px; border-radius: 50%; background: #555; margin-right: 6px; vertical-align: middle; }
  .dot.ok { background: #10b981; }
  .dot.busy { background: #f59e0b; animation: pulse 1s infinite; }
  .dot.err { background: #ef4444; }
  @keyframes pulse { 50% { opacity: 0.4; } }
  .count { font-size: 11px; color: var(--muted); }
  .hint {
    background: #11111a; border-left: 3px solid var(--accent); border-radius: 4px;
    padding: 10px 12px; font-size: 12.5px; line-height: 1.5; color: #c9c9d0;
    margin-top: 4px;
  }
  .hint .tag { color: var(--accent); font-weight: 700; }
  .hint .rule { display: block; margin-top: 4px; }
  .hint .ex { display: block; margin-top: 6px; font-style: italic; color: #a8a8b2; }
  .hint .ex::before { content: "ex: "; font-style: normal; color: var(--muted); }
</style>
</head>
<body>
<div class="layout">
  <!-- LEFT: prompt editor + controls -->
  <div class="panel">
    <div style="display:flex; align-items:center; gap:8px;">
      <h1>prompt workbench</h1>
      <div class="spacer"></div>
      <span class="status"><span class="dot" id="dot"></span><span id="statusText">ready</span></span>
    </div>

    <div class="grid3">
      <div>
        <label>category</label>
        <select id="category"></select>
      </div>
      <div>
        <label>topic</label>
        <select id="topic"></select>
      </div>
      <div>
        <label>hook type</label>
        <select id="hookType"></select>
      </div>
    </div>

    <div class="hint" id="hookHint"></div>

    <div class="checks">
      <label><input type="checkbox" id="skipAudio" checked /> skip audio</label>
      <label><input type="checkbox" id="skipImage" /> skip image</label>
    </div>

    <div class="btn-row">
      <button id="generate">Generate</button>
      <button class="ghost" id="randomize">Randomize topic + hook</button>
      <div class="spacer"></div>
      <button class="ghost" id="resetPrompts">Reset prompts to defaults</button>
    </div>

    <div>
      <label>system prompt</label>
      <textarea class="system" id="sys" spellcheck="false"></textarea>
      <div class="count" id="sysCount"></div>
    </div>

    <div>
      <label>image style prefix (prepended client-side before the fal.ai call)</label>
      <textarea class="prefix" id="prefix" spellcheck="false"></textarea>
      <div class="count" id="prefixCount"></div>
    </div>
  </div>

  <!-- RIGHT: result + history -->
  <div class="panel">
    <h2>result</h2>
    <div id="result" class="empty">Pick a topic and hit Generate.</div>

    <div style="display:flex; align-items:center; gap:8px;">
      <h2>history (this session)</h2>
      <div class="spacer"></div>
      <button class="ghost" id="clearHistory" style="padding:4px 10px; font-size:12px;">Clear</button>
    </div>
    <div id="history" class="history"></div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const LS = {
  sys: "mindscroller.workbench.sys",
  prefix: "mindscroller.workbench.prefix",
  history: "mindscroller.workbench.history",
  category: "mindscroller.workbench.category",
  topic: "mindscroller.workbench.topic",
  hookType: "mindscroller.workbench.hookType",
};
let defaults = { system_prompt: "", style_prefix: "" };
let taxonomy = {}; let hookTypes = []; let hookSpecs = {};
let history = JSON.parse(localStorage.getItem(LS.history) || "[]");

async function init() {
  const [defR, taxR] = await Promise.all([
    fetch("/api/workbench/defaults").then(r => r.json()),
    fetch("/api/workbench/taxonomy").then(r => r.json()),
  ]);
  defaults = defR;
  taxonomy = taxR.taxonomy;
  hookTypes = taxR.hook_types;
  hookSpecs = taxR.hook_type_specs || {};

  // prompts (with localStorage overrides)
  $("sys").value = localStorage.getItem(LS.sys) ?? defaults.system_prompt;
  $("prefix").value = localStorage.getItem(LS.prefix) ?? defaults.style_prefix;
  updateCounts();
  $("sys").addEventListener("input", () => { localStorage.setItem(LS.sys, $("sys").value); updateCounts(); });
  $("prefix").addEventListener("input", () => { localStorage.setItem(LS.prefix, $("prefix").value); updateCounts(); });

  // category dropdown
  const cats = Object.keys(taxonomy);
  $("category").innerHTML = cats.map(c => `<option>${escapeHtml(c)}</option>`).join("");
  $("category").value = localStorage.getItem(LS.category) || cats[0];
  populateTopics();
  $("category").addEventListener("change", () => {
    localStorage.setItem(LS.category, $("category").value);
    populateTopics();
  });
  $("topic").addEventListener("change", () => localStorage.setItem(LS.topic, $("topic").value));

  // hook type dropdown
  $("hookType").innerHTML = hookTypes.map(h => `<option>${escapeHtml(h)}</option>`).join("");
  $("hookType").value = localStorage.getItem(LS.hookType) || hookTypes[0];
  $("hookType").addEventListener("change", () => {
    localStorage.setItem(LS.hookType, $("hookType").value);
    renderHookHint();
  });
  renderHookHint();

  // buttons
  $("generate").addEventListener("click", onGenerate);
  $("randomize").addEventListener("click", onRandomize);
  $("resetPrompts").addEventListener("click", () => {
    $("sys").value = defaults.system_prompt;
    $("prefix").value = defaults.style_prefix;
    localStorage.removeItem(LS.sys);
    localStorage.removeItem(LS.prefix);
    updateCounts();
  });
  $("clearHistory").addEventListener("click", () => {
    history = [];
    localStorage.removeItem(LS.history);
    renderHistory();
  });

  renderHistory();
}

function renderHookHint() {
  const ht = $("hookType").value;
  const spec = hookSpecs[ht];
  const root = $("hookHint");
  if (!spec) { root.innerHTML = ""; return; }
  root.innerHTML = `
    <span class="tag">${escapeHtml(ht)}</span> — ${escapeHtml(spec.tagline)}
    <span class="rule">${escapeHtml(spec.rule)}</span>
    <span class="ex">${escapeHtml(spec.example)}</span>
  `;
}

function populateTopics() {
  const cat = $("category").value;
  const topics = taxonomy[cat] || [];
  $("topic").innerHTML = topics.map(t => `<option>${escapeHtml(t)}</option>`).join("");
  const stored = localStorage.getItem(LS.topic);
  if (stored && topics.includes(stored)) $("topic").value = stored;
  else { $("topic").value = topics[0]; localStorage.setItem(LS.topic, $("topic").value); }
}

function onRandomize() {
  const cats = Object.keys(taxonomy);
  const cat = cats[Math.floor(Math.random() * cats.length)];
  $("category").value = cat;
  localStorage.setItem(LS.category, cat);
  populateTopics();
  const topics = taxonomy[cat];
  $("topic").value = topics[Math.floor(Math.random() * topics.length)];
  localStorage.setItem(LS.topic, $("topic").value);
  $("hookType").value = hookTypes[Math.floor(Math.random() * hookTypes.length)];
  localStorage.setItem(LS.hookType, $("hookType").value);
}

function updateCounts() {
  $("sysCount").textContent = $("sys").value.length + " chars";
  $("prefixCount").textContent = $("prefix").value.length + " chars";
}

function setStatus(state, text) {
  $("dot").className = "dot" + (state ? " " + state : "");
  $("statusText").textContent = text;
}

async function onGenerate() {
  $("generate").disabled = true;
  setStatus("busy", "generating…");
  const t0 = performance.now();
  try {
    const r = await fetch("/api/workbench/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        category: $("category").value,
        topic: $("topic").value,
        hook_type: $("hookType").value,
        system_prompt: $("sys").value,
        style_prefix: $("prefix").value,
        skip_audio: $("skipAudio").checked,
        skip_image: $("skipImage").checked,
      }),
    });
    if (!r.ok) {
      const text = await r.text();
      throw new Error("HTTP " + r.status + ": " + text.slice(0, 400));
    }
    const data = await r.json();
    const card = data.card;
    history.unshift(card);
    history = history.slice(0, 30);
    localStorage.setItem(LS.history, JSON.stringify(history));
    renderCard(card);
    renderHistory(card.id);
    const ms = Math.round(performance.now() - t0);
    setStatus("ok", "done in " + ms + " ms");
  } catch (e) {
    setStatus("err", "error");
    $("result").innerHTML = "<div class='empty' style='color:#ef4444'>" + escapeHtml(String(e)) + "</div>";
  } finally {
    $("generate").disabled = false;
  }
}

function renderCard(card) {
  const wordCount = (card.script || "").trim().split(/\s+/).length;
  const hookWordCount = (card.visual_hook || "").trim().split(/\s+/).length;

  const imgInner = card.image_path
    ? `<img src="${card.image_path}" alt="" onerror="this.parentElement.classList.add('no-img'); this.remove();" />`
    : `<div style="color:#555;font-size:13px">(image skipped)</div>`;
  const audioBlock = card.audio_path
    ? `<audio controls style="width:100%" src="${card.audio_path}"></audio>`
    : "";

  $("result").classList.remove("empty");
  $("result").innerHTML = `
    <div class="result">
      <div class="meta">
        <span class="cat">${escapeHtml(card.category)}</span>
        <span class="topic">${escapeHtml(card.topic)}</span>
        <span class="hook">hook: ${escapeHtml(card.hook_type)}</span>
        <span>${hookWordCount}w hook · ${wordCount}w script</span>
      </div>
      <div class="img-wrap ${card.image_path ? "" : "no-img"}">
        ${imgInner}
        <div class="visual-hook-overlay">${escapeHtml(card.visual_hook)}</div>
      </div>
      ${audioBlock}
      <div class="script">${escapeHtml(card.script)}</div>
      <details>
        <summary>image_prompt (LLM-authored, before style prefix)</summary>
        <pre>${escapeHtml(card.image_prompt)}</pre>
      </details>
    </div>
  `;
}

function renderHistory(selectedId) {
  const root = $("history");
  if (!history.length) {
    root.innerHTML = "<div class='item placeholder'>generated cards will appear here</div>";
    return;
  }
  root.innerHTML = history.map(c => {
    const sel = c.id === selectedId ? " selected" : "";
    const bg = c.image_path
      ? `<img src="${c.image_path}" alt="" onerror="this.style.display='none'" />`
      : `<div style="width:88px;height:116px;background:linear-gradient(135deg,#1a1a25,#0d0d12)"></div>`;
    return `<div class="item${sel}" data-id="${c.id}" title="${escapeHtml(c.visual_hook)} — ${escapeHtml(c.topic)}">
      ${bg}
      <div class="ovl">${escapeHtml((c.visual_hook || "").slice(0, 40))}</div>
    </div>`;
  }).join("");
  for (const el of root.querySelectorAll(".item[data-id]")) {
    el.addEventListener("click", () => {
      const card = history.find(c => c.id === el.dataset.id);
      if (card) { renderCard(card); renderHistory(card.id); }
    });
  }
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
}

init();
</script>
</body>
</html>
"""
