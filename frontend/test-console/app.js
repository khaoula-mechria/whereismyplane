// Console de test AeroPulse : appels same-origin vers /v1/* (CloudFront relaie vers API Gateway).
"use strict";

const keyInput = document.getElementById("api-key");
const output = document.getElementById("output");
const statusEl = document.getElementById("status");
const summary = document.getElementById("summary");

try {
  keyInput.value = sessionStorage.getItem("aeropulse-key") || "";
} catch (_) { /* stockage indisponible : saisie à chaque fois */ }
keyInput.addEventListener("change", () => {
  try { sessionStorage.setItem("aeropulse-key", keyInput.value); } catch (_) { /* ignoré */ }
});

function render(status, body) {
  statusEl.textContent = String(status);
  statusEl.className = "status " + (status >= 200 && status < 300 ? "ok" : "ko");
  output.textContent = typeof body === "string" ? body : JSON.stringify(body, null, 2);
  summary.replaceChildren();
  if (body && typeof body.answer === "string") {
    const a = document.createElement("p");
    a.textContent = body.answer;
    const meta = document.createElement("p");
    const tools = (body.sources || []).map((s) => s.tool).join(", ") || "aucun";
    meta.textContent = `Outils : ${tools} · chiffres vérifiés : ${body.grounded ? "oui" : "non"}` +
      (body.truncated ? " · réponse interrompue (limite atteinte)" : "");
    summary.append(a, meta);
  }
  if (body && typeof body.delay_probability === "number") {
    const p = document.createElement("p");
    const pct = (body.delay_probability * 100).toFixed(1);
    p.textContent = `Probabilité de retard > 15 min : ${pct} % — ` +
      (body.is_delayed_predicted ? "retard prédit" : "pas de retard prédit") +
      ` (seuil ${body.threshold}, modèle ${body.model_versions.classification})`;
    summary.append(p);
    if (body.observed) {
      const o = document.createElement("p");
      o.textContent = "Issue historique réelle : " + (body.observed.is_delayed ? "retardé" : "à l'heure");
      summary.append(o);
    }
  }
}

async function call(method, path, payload) {
  const key = keyInput.value.trim();
  if (!key) { render(0, "Saisir la clé d'API."); return; }
  statusEl.textContent = "…";
  try {
    const res = await fetch(path, {
      method,
      headers: { "x-api-key": key, ...(payload ? { "Content-Type": "application/json" } : {}) },
      body: payload ? JSON.stringify(payload) : undefined,
    });
    const text = await res.text();
    let body = text;
    try { body = JSON.parse(text); } catch (_) { /* texte brut */ }
    render(res.status, body);
  } catch (err) {
    render(0, "Erreur réseau : " + err.message);
  }
}

document.getElementById("btn-health").addEventListener("click", () => call("GET", "/v1/health"));
document.getElementById("btn-meta").addEventListener("click", () => call("GET", "/v1/meta"));

document.getElementById("form-replay").addEventListener("submit", (e) => {
  e.preventDefault();
  const id = new FormData(e.target).get("flight_id").trim();
  call("POST", "/v1/predict", { flight_id: id });
});

document.getElementById("form-manual").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  call("POST", "/v1/predict", {
    airline: f.get("airline").trim().toUpperCase(),
    origin: f.get("origin"),
    destination: f.get("destination").trim().toUpperCase(),
    scheduled_departure: f.get("scheduled_departure").trim(),
  });
});

document.getElementById("form-stats").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const params = new URLSearchParams();
  for (const name of ["carrier", "origin", "year", "month", "limit"]) {
    const v = String(f.get(name) || "").trim();
    if (v) params.set(name, name === "carrier" || name === "origin" ? v.toUpperCase() : v);
  }
  const qs = params.toString();
  call("GET", `/v1/stats/${encodeURIComponent(f.get("dimension"))}` + (qs ? `?${qs}` : ""));
});

document.getElementById("form-chat").addEventListener("submit", (e) => {
  e.preventDefault();
  const message = String(new FormData(e.target).get("message") || "").trim();
  if (!message) { render(0, "Saisir une question."); return; }
  call("POST", "/v1/chat", { message });
});
