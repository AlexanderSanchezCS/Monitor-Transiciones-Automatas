const state = { sessions: [], validationSessions: [], testSessions: [], activeDataset: "validation", patterns: [], summary: null, automaton: null };
const graphSimulation = { sequence: "", index: 0, current: "M0", running: false };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function getJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`No se pudo consultar ${path}`);
  return response.json();
}

function showSection(id) {
  $$(".page-section").forEach((section) => section.classList.toggle("active", section.id === id));
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.section === id));
  const titles = { overview: "Resumen ejecutivo", sessions: "Sesiones procesadas", patterns: "Patrones de anomalía", automaton: "Autómata", simulator: "Simulador", methodology: "Metodología y datos" };
  $("#page-title").textContent = titles[id];
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function sessionTable(sessions) {
  if (!sessions.length) return '<div class="empty-state">No hay sesiones que coincidan con el filtro.</div>';
  const isTest = state.activeDataset === "test";
  return `<table class="data-table"><thead><tr><th>IDENTIFICADOR</th><th>SECUENCIA</th><th>EVENTOS</th><th>RESULTADO MONITOR</th><th>ETIQUETA ${isTest ? "CLAVE" : "CSV"}</th><th>PATRÓN</th>${isTest ? "<th>COINCIDE</th>" : ""}</tr></thead><tbody>${sessions.map((session) => `<tr><td class="mono">${session.id}</td><td class="mono">${session.sequence}</td><td>${session.events}</td><td><span class="status ${session.detected.length ? "anomala" : "normal"}">${session.status}</span></td><td><span class="status ${session.label}">${session.label === "anomala" ? "Anómala" : "Normal"}</span></td><td class="pattern-tag">${session.pattern}</td>${isTest ? `<td><span class="match-badge ${session.match ? "match" : "mismatch"}">${session.match ? "Sí" : "No"}</span></td>` : ""}</tr>`).join("")}</tbody></table>`;
}

function renderSessions() {
  $("#recent-sessions").innerHTML = sessionTable(state.sessions.slice(0, 5));
  const filtered = state.sessions.filter((session) => {
    const query = $("#session-search").value.toLowerCase();
    const status = $("#status-filter").value;
    return (status === "all" || session.label === status) && (!query || `${session.id} ${session.sequence}`.toLowerCase().includes(query));
  });
  $("#session-count").textContent = `${filtered.length} de ${state.sessions.length} sesiones mostradas`;
  $("#all-sessions").innerHTML = sessionTable(filtered);
}

function renderPatterns() {
  $("#pattern-list").innerHTML = state.patterns.map((pattern, index) => `<div class="pattern-row"><div class="pattern-dot" style="background:${pattern.color}"></div><div><strong>${pattern.id} · ${pattern.name}</strong><small>${pattern.rule}</small><div class="bar-line"><i style="width:${[78,64,59,48][index]}%"></i></div></div><span class="pattern-count">${[14,14,13,13][index]}</span></div>`).join("");
  $("#pattern-cards").innerHTML = state.patterns.map((pattern) => `<article class="pattern-card" style="border-top-color:${pattern.color}"><div class="code">${pattern.id}</div><h2>${pattern.name}</h2><p>${pattern.description}</p><span class="example">${pattern.example}</span></article>`).join("");
}

function renderEvents(events) {
  $("#event-list").innerHTML = events.map((event) => `<div class="event-chip"><b>${event.symbol}</b><span>${event.name}</span></div>`).join("");
}

function updateGraphHighlight(activeFrom = "", activeTo = "", activeSymbol = "") {
  $$("#automaton-graph .graph-node").forEach((node) => {
    node.classList.toggle("current", node.dataset.state === graphSimulation.current);
  });
  $$("#automaton-graph .graph-edge").forEach((edge) => {
    const symbols = edge.dataset.symbols.split(",");
    edge.classList.toggle("active", edge.dataset.from === activeFrom && edge.dataset.to === activeTo && symbols.includes(activeSymbol));
  });
}

function resetGraphSimulation() {
  graphSimulation.sequence = "";
  graphSimulation.index = 0;
  graphSimulation.current = "M0";
  graphSimulation.running = false;
  $("#graph-next").disabled = true;
  $("#graph-step-status").textContent = "LISTO · M0";
  $("#graph-consumed").textContent = "Consumidos: —";
  $("#graph-current-symbol").textContent = "Símbolo actual: —";
  $("#graph-final-result").textContent = "Resultado: pendiente";
  updateGraphHighlight();
}

function startGraphSimulation() {
  const sequence = $("#graph-sequence").value.trim().toUpperCase();
  const invalid = [...sequence].find((symbol) => !state.automaton.alphabet.includes(symbol));
  if (!sequence || invalid) {
    $("#graph-step-status").textContent = invalid ? `Símbolo inválido · ${invalid}` : "Ingresa una secuencia";
    $("#graph-sequence").focus();
    return;
  }
  graphSimulation.sequence = sequence;
  graphSimulation.index = 0;
  graphSimulation.current = "M0";
  graphSimulation.running = true;
  $("#graph-next").disabled = false;
  $("#graph-step-status").textContent = "EN CURSO · M0";
  $("#graph-consumed").textContent = "Consumidos: —";
  $("#graph-current-symbol").textContent = `Siguiente símbolo: ${sequence[0]}`;
  $("#graph-final-result").textContent = "Resultado: pendiente";
  updateGraphHighlight();
}

function nextGraphStep() {
  if (!graphSimulation.running || graphSimulation.index >= graphSimulation.sequence.length) return;
  const symbol = graphSimulation.sequence[graphSimulation.index];
  const from = graphSimulation.current;
  const to = state.automaton.transitions[from][symbol];
  graphSimulation.current = to;
  graphSimulation.index += 1;
  updateGraphHighlight(from, to, symbol);
  $("#graph-step-status").textContent = `PASO ${graphSimulation.index}/${graphSimulation.sequence.length} · ${to}`;
  $("#graph-consumed").textContent = `Recorrido: ${graphSimulation.sequence.slice(0, graphSimulation.index)}`;
  $("#graph-current-symbol").textContent = graphSimulation.index < graphSimulation.sequence.length ? `Siguiente símbolo: ${graphSimulation.sequence[graphSimulation.index]}` : "Secuencia completa";
  if (graphSimulation.index >= graphSimulation.sequence.length) {
    graphSimulation.running = false;
    $("#graph-next").disabled = true;
    $("#graph-final-result").textContent = `Resultado: ${to === "M3" ? "ANÓMALA" : "NORMAL"} · estado final ${to}`;
  }
}

function renderAutomaton() {
  const { states, transitions, alphabet, models } = state.automaton;
  $("#automaton-summary").innerHTML = `<div class="model-stat"><strong>${states.length}</strong><span>Estados mínimos</span></div><div class="model-stat"><strong>${alphabet.length}</strong><span>Símbolos del alfabeto</span></div><div class="model-stat"><strong>${alphabet.length * states.length}</strong><span>Transiciones</span></div><div class="model-stat"><strong>M3</strong><span>Estado de aceptación</span></div>`;
  $("#state-list").innerHTML = states.map((item) => `<div class="state-row"><span class="state-id ${item.id === "M3" ? "accepting" : ""}">${item.id}</span><div><strong>${item.name}</strong><small>${item.description}</small></div><span class="state-label">${item.id === "M0" ? "Inicial" : item.id === "M3" ? "Final" : "Intermedio"}</span></div>`).join("");
  $("#transition-table").innerHTML = `<table class="data-table transition-table"><thead><tr><th>ESTADO</th>${alphabet.map((symbol) => `<th>${symbol}</th>`).join("")}</tr></thead><tbody>${states.map((item) => `<tr><td class="mono">${item.id}</td>${alphabet.map((symbol) => `<td class="${transitions[item.id][symbol] === "M3" ? "accept-cell" : ""}">${transitions[item.id][symbol]}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  $$("#automaton-graph .graph-edge").forEach((edge) => {
    const symbols = alphabet.filter((symbol) => transitions[edge.dataset.from][symbol] === edge.dataset.to);
    const label = edge.querySelector("text");
    if (label) label.textContent = symbols.join(", ");
    edge.dataset.symbols = symbols.join(",");
  });
  $("#metrics-list").innerHTML = `<div><span>Verdaderos positivos</span><strong>${state.summary.metrics.vp}</strong></div><div><span>Falsos positivos</span><strong>${state.summary.metrics.fp}</strong></div><div><span>Falsos negativos</span><strong>${state.summary.metrics.fn}</strong></div><div><span>Precisión</span><strong>${state.summary.metrics.precision}%</strong></div><div><span>Recall</span><strong>${state.summary.metrics.recall}%</strong></div>`;
  $("#afnd-count").textContent = models.afnd == null ? "No verificado" : `${models.afnd} estados`;
  $("#afd-count").textContent = models.afd == null ? "No verificado" : `${models.afd} estados`;
  $("#minimal-count").textContent = `${models.minimal ?? states.length} estados`;
  resetGraphSimulation();
}

function renderSummary() {
  const { validation, test, updated } = state.summary;
  $("#stat-sessions").textContent = validation.sessions + test.sessions;
  $("#stat-anomalies").textContent = validation.anomalies + test.anomalies;
  $("#stat-events").textContent = (validation.events + test.events).toLocaleString("es-ES");
  $("#updated").textContent = updated;
}

async function analyze() {
  const sequence = $("#sequence-input").value.trim().toUpperCase();
  const error = $("#form-error");
  error.textContent = "";
  if (!sequence) { error.textContent = "Ingresa una secuencia para analizar."; return; }
  try {
    const response = await fetch("/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sequence }) });
    const result = await response.json();
    if (!response.ok) { error.textContent = result.error; return; }
    $("#result-empty").classList.add("hidden");
    $("#result-content").classList.remove("hidden");
    const status = result.status === "Anómala" ? "anomala" : "normal";
    $("#result-status").className = `status-chip ${status}`;
    $("#result-status").textContent = result.status;
    $("#result-sequence").textContent = result.sequence;
    $("#result-patterns").innerHTML = result.patterns.length ? `<div class="result-alert">Se reconocieron ${result.patterns.length} patrón(es): ${result.patterns.map((item) => `${item.id} · ${item.rule}`).join(", ")}.</div>` : '<div class="result-ok">La cadena no pertenece a ninguno de los cuatro lenguajes anómalos.</div>';
    $("#result-facts").innerHTML = `<div><span>Estado final</span><strong>${result.final_state}</strong></div><div><span>Eventos recorridos</span><strong>${result.events.length}</strong></div>`;
    $("#result-trace").innerHTML = `<div class="trace-heading">Traza del AFD mínimo · clasificación global</div>${result.trace.slice(1).map((step) => `<div class="trace-item"><b>${step.from}</b><span>—${step.symbol}→</span><strong>${step.to}</strong></div>`).join("")}`;
    if (result.pattern_evidence.length) {
      $("#result-trace").innerHTML += `<div class="evidence-heading">Verificadores específicos · patrones individuales</div>${result.pattern_evidence.map((item) => `<div class="evidence-row"><strong>${item.id}</strong><span>${item.rule}</span><b>${item.detail}</b></div>`).join("")}`;
    }
    $("#result-explanation").textContent = result.explanation;
  } catch (requestError) { error.textContent = "No fue posible conectar con el monitor."; }
}

async function init() {
  try {
    [state.summary, state.patterns, state.validationSessions, state.testSessions, state.automaton] = await Promise.all([getJSON("/api/summary"), getJSON("/api/patterns"), getJSON("/api/sessions?dataset=validation"), getJSON("/api/sessions?dataset=test"), getJSON("/api/automaton")]);
    state.sessions = state.validationSessions;
    renderSummary(); renderPatterns(); renderSessions(); renderEvents(await getJSON("/api/events")); renderAutomaton();
  } catch (error) {
    $("#updated").textContent = "sin conexión";
    console.error(error);
  }
}

$$(".nav-item").forEach((item) => item.addEventListener("click", () => showSection(item.dataset.section)));
$$("[data-section-target]").forEach((item) => item.addEventListener("click", () => showSection(item.dataset.sectionTarget)));
$("#analyze-button").addEventListener("click", analyze);
$("#sequence-input").addEventListener("keydown", (event) => { if (event.key === "Enter") analyze(); });
$$(".quick-sequences button").forEach((button) => button.addEventListener("click", () => { $("#sequence-input").value = button.dataset.sequence; analyze(); }));
$("#session-search").addEventListener("input", renderSessions);
$("#status-filter").addEventListener("change", renderSessions);
$("#dataset-filter").addEventListener("change", (event) => {
  state.activeDataset = event.target.value;
  state.sessions = state.activeDataset === "test" ? state.testSessions : state.validationSessions;
  $("#session-search").value = "";
  $("#status-filter").value = "all";
  renderSessions();
});
$("#graph-start").addEventListener("click", startGraphSimulation);
$("#graph-next").addEventListener("click", nextGraphStep);
$("#graph-reset").addEventListener("click", resetGraphSimulation);
init();
