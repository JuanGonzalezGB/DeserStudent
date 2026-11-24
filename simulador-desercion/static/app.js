/* ==========================================================================
 * Simulador de probabilidad de deserción — Frontend Analítico
 *
 * Arquitectura limpia:
 *   - Cero duplicación de fórmulas: el What-If consulta POST /api/evaluar
 *     y los metadatos vienen de GET /api/config.
 *   - Tabla paginada con delegación de eventos única (soporta 5.000 filas sin lag).
 *   - Inspector lateral (Master-Detail) con navegación ↑/↓/Esc, Radar 4D y
 *     Cascada del Logit en SVG.
 *   - Validación visual con Curva ROC empírica, Matriz de Confusión 2×2,
 *     Diagrama de Tornado (±50%) y Sparklines de Monotonía.
 * ========================================================================== */
"use strict";

const DIMENSIONES = ["academica", "financiera", "laboral", "personal"];
const NOMBRE_DIM = {
  academica: "Académica",
  financiera: "Financiera",
  laboral: "Laboral",
  personal: "Personal"
};
const COLOR_DIM = {
  academica: "#2563eb",
  financiera: "#d97706",
  laboral: "#7c3aed",
  personal: "#0d9488"
};
const COLOR_NIVEL = {
  bajo: "#059669",
  medio: "#d97706",
  alto: "#dc2626",
  revision: "#64748b"
};

const CAMPOS_DIM = {
  academica: [
    ["promedio", "Promedio (0–5)"],
    ["materias_perdidas", "Materias perdidas"],
    ["asistencia_pct", "Asistencia (%)"],
    ["semestre", "Semestre"]
  ],
  financiera: [
    ["saldo_pendiente_cop", "Saldo pendiente"],
    ["ingreso_hogar_smmlv", "Ingreso (SMMLV)"],
    ["estrato", "Estrato"],
    ["tiene_apoyo_financiero", "Apoyo financiero"]
  ],
  laboral: [
    ["horas_trabajo_semana", "Horas trabajo/sem."],
    ["trabaja_en_area_de_estudio", "Trabaja en su área"]
  ],
  personal: [
    ["tiempo_desplazamiento_min", "Desplazamiento (min)"],
    ["personas_a_cargo", "Personas a cargo"],
    ["apoyo_familiar", "Apoyo familiar (1–5)"],
    ["primera_generacion_universitaria", "Primera generación"]
  ]
};

const MODOS_SIMULACION = {
  referencia: { origen: "sintetica", n: 500, semilla: 42, tasa_base: 0.09, k_montecarlo: 1000 },
  spadies:    { origen: "sintetica", n: 500, semilla: 42, tasa_base: 0.0442, k_montecarlo: 1000 },
  uci_full:   { origen: "uci", n: 3630, semilla: 42, tasa_base: 0.3915, k_montecarlo: 200 },
  uci_500:    { origen: "uci", n: 500, semilla: 42, tasa_base: 0.0442, k_montecarlo: 300 }
};

const PRESETS_WHATIF = {
  intermedio: {
    promedio: 3.0, materias_perdidas: 2, asistencia_pct: 80, semestre: 4,
    saldo_pendiente_cop: 4000000, ingreso_hogar_smmlv: 2.0, estrato: 2,
    tiene_apoyo_financiero: false, horas_trabajo_semana: 30,
    trabaja_en_area_de_estudio: false, tiempo_desplazamiento_min: 60,
    personas_a_cargo: 1, apoyo_familiar: 3, primera_generacion_universitaria: true
  },
  sin_riesgo: {
    promedio: 4.8, materias_perdidas: 0, asistencia_pct: 98, semestre: 3,
    saldo_pendiente_cop: 0, ingreso_hogar_smmlv: 8.0, estrato: 5,
    tiene_apoyo_financiero: true, horas_trabajo_semana: 0,
    trabaja_en_area_de_estudio: false, tiempo_desplazamiento_min: 15,
    personas_a_cargo: 0, apoyo_familiar: 5, primera_generacion_universitaria: false
  },
  financiero: {
    promedio: 3.8, materias_perdidas: 1, asistencia_pct: 85, semestre: 4,
    saldo_pendiente_cop: 8000000, ingreso_hogar_smmlv: 1.0, estrato: 1,
    tiene_apoyo_financiero: false, horas_trabajo_semana: 15,
    trabaja_en_area_de_estudio: false, tiempo_desplazamiento_min: 45,
    personas_a_cargo: 0, apoyo_familiar: 4, primera_generacion_universitaria: true
  },
  todo_alto: {
    promedio: 1.5, materias_perdidas: 4, asistencia_pct: 55, semestre: 2,
    saldo_pendiente_cop: 9000000, ingreso_hogar_smmlv: 0.5, estrato: 1,
    tiene_apoyo_financiero: false, horas_trabajo_semana: 45,
    trabaja_en_area_de_estudio: false, tiempo_desplazamiento_min: 140,
    personas_a_cargo: 3, apoyo_familiar: 1, primera_generacion_universitaria: true
  },
  a03: {
    promedio: 3.5, materias_perdidas: 0, asistencia_pct: 88, semestre: 3,
    saldo_pendiente_cop: 2000000, ingreso_hogar_smmlv: 14.0, estrato: 1,
    tiene_apoyo_financiero: false, horas_trabajo_semana: 10,
    trabaja_en_area_de_estudio: true, tiempo_desplazamiento_min: 40,
    personas_a_cargo: 0, apoyo_familiar: 4, primera_generacion_universitaria: false
  },
  perdidas_5: {
    promedio: 5.0, materias_perdidas: 2, asistencia_pct: 95, semestre: 5,
    saldo_pendiente_cop: 0, ingreso_hogar_smmlv: 4.0, estrato: 3,
    tiene_apoyo_financiero: false, horas_trabajo_semana: 0,
    trabaja_en_area_de_estudio: false, tiempo_desplazamiento_min: 30,
    personas_a_cargo: 0, apoyo_familiar: 4, primera_generacion_universitaria: false
  }
};

/* ======================================================== ESTADO GLOBAL == */
let configContrato = null;
let simulacionActual = null;
let cohorteCompleta = [];        // Todos los estudiantes de la corrida activa (cache local)
let estudiantesFiltrados = [];   // Resultado tras aplicar filtros y orden
let paginaActual = 1;
let tamanoPagina = 25;
let chipActivo = "todos";
let estudianteInspectorId = null;

// Estado de comparación en What-If
let baseWhatIf = null;           // { codigo, datos } cuando se carga un alumno real/sintético
let timerWhatIf = null;
let timerBusqueda = null;

/* ============================================================ UTILIDADES == */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto == null ? "" : String(texto);
  return div.innerHTML;
}

const pct = (x, dec = 1) => (100 * Number(x || 0)).toFixed(dec) + "%";
const num = (x, dec = 3) => Number(x || 0).toFixed(dec);
const cop = (valor) => "$ " + Math.round(Number(valor || 0)).toLocaleString("es-CO");

function valorLegible(campo, valor) {
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (valor === null || valor === undefined || valor === "") return "(vacío)";
  if (campo === "saldo_pendiente_cop") return cop(valor);
  if (campo === "asistencia_pct") return Number(valor).toFixed(1) + "%";
  if (campo === "ingreso_hogar_smmlv") return Number(valor).toFixed(2) + " SMMLV";
  return String(valor);
}

async function pedir(url, opciones) {
  const respuesta = await fetch(url, opciones);
  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
  } catch (_err) {
    throw new Error("Respuesta no válida del servidor (HTTP " + respuesta.status + ")");
  }
  if (!respuesta.ok) {
    throw new Error(cuerpo && cuerpo.error ? cuerpo.error : "Error HTTP " + respuesta.status);
  }
  return cuerpo;
}

function informarEstado(mensaje, tipo = "") {
  const el = $("#estado-global");
  if (!el) return;
  el.textContent = mensaje;
  el.className = "estado-global" + (tipo ? " " + tipo : "");
}

/* =================================================== TEMA Y NAVEGACIÓN == */
function inicializarTema() {
  const guardado = localStorage.getItem("simulador_tema");
  if (guardado === "oscuro" || guardado === "claro") {
    document.documentElement.setAttribute("data-tema", guardado);
  }
  actualizarIconoTema();

  $("#btn-tema").addEventListener("click", () => {
    const actual = document.documentElement.getAttribute("data-tema") || "claro";
    const nuevo = actual === "oscuro" ? "claro" : "oscuro";
    document.documentElement.setAttribute("data-tema", nuevo);
    localStorage.setItem("simulador_tema", nuevo);
    actualizarIconoTema();
  });
}

function actualizarIconoTema() {
  const oscuro = document.documentElement.getAttribute("data-tema") === "oscuro";
  $("#icono-tema").textContent = oscuro ? "☀" : "☾";
}

function activarPestana(idPanel) {
  $$(".pestana").forEach((p) => {
    const es = p.dataset.panel === idPanel;
    p.classList.toggle("activa", es);
    p.setAttribute("aria-selected", es ? "true" : "false");
  });
  $$(".panel-vista").forEach((panel) => {
    panel.classList.toggle("activo", panel.id === idPanel);
  });
}

$$(".pestana").forEach((btn) => {
  btn.addEventListener("click", () => activarPestana(btn.dataset.panel));
});

function toggleConfig(forzar) {
  const gaveta = $("#gaveta-config");
  const btn = $("#btn-toggle-config");
  const abrir = typeof forzar === "boolean" ? forzar : gaveta.hidden;
  gaveta.hidden = !abrir;
  btn.setAttribute("aria-expanded", abrir ? "true" : "false");
}

$("#btn-toggle-config").addEventListener("click", () => toggleConfig());
$("#btn-cerrar-config").addEventListener("click", () => toggleConfig(false));

/* =============================================== 1. CORRER SIMULACIONES == */
function sincronizarPildorasEscenario(origen, n, tasa) {
  const esReal = origen === "uci";
  $("#ayuda-n").textContent = esReal
    ? "Muestra del CSV real UCI (máx. 3.630 cerrados)"
    : "Tamaño de la cohorte sintética (1 – 5.000)";
  $("#ayuda-semilla").textContent = esReal
    ? "Controla submuestreo aleatorio (si n < 3.630) e intervalos"
    : "Misma semilla = misma cohorte e intervalos";

  $$("[data-modo-sim]").forEach((btn) => {
    const cfg = MODOS_SIMULACION[btn.dataset.modoSim];
    const coincide = cfg &&
      cfg.origen === (origen || "sintetica") &&
      Number(n) === cfg.n &&
      Math.abs(Number(tasa) - cfg.tasa_base) < 0.001;
    btn.classList.toggle("activa", Boolean(coincide));
  });
}

$("#origen").addEventListener("change", () => {
  sincronizarPildorasEscenario(
    $("#origen").value,
    Number($("#n").value),
    Number($("#tasa_base").value)
  );
});

$$("[data-modo-sim]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const cfg = MODOS_SIMULACION[btn.dataset.modoSim];
    if (!cfg) return;
    $("#origen").value = cfg.origen;
    $("#n").value = cfg.n;
    $("#semilla").value = cfg.semilla;
    $("#tasa_base").value = cfg.tasa_base;
    $("#k_montecarlo").value = cfg.k_montecarlo;
    sincronizarPildorasEscenario(cfg.origen, cfg.n, cfg.tasa_base);
    ejecutarFormularioSimulacion();
  });
});

$("#form-simular").addEventListener("submit", (ev) => {
  ev.preventDefault();
  ejecutarFormularioSimulacion();
});

async function ejecutarFormularioSimulacion() {
  const btn = $("#btn-simular");
  const pildoras = $$("[data-modo-sim]");
  btn.disabled = true;
  pildoras.forEach((p) => { p.disabled = true; });
  informarEstado("Ejecutando simulación y calibrando b₀…", "cargando");

  const cuerpo = {
    n: Number($("#n").value),
    semilla: Number($("#semilla").value),
    tasa_base: Number($("#tasa_base").value),
    umbral_medio: Number($("#umbral_medio").value),
    umbral_alto: Number($("#umbral_alto").value),
    k_montecarlo: Number($("#k_montecarlo").value)
  };
  if ($("#origen").value === "uci") {
    cuerpo.origen = "uci";
  }

  try {
    const sim = await pedir("/api/simulaciones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo)
    });
    toggleConfig(false);
    cerrarInspector();
    await activarSimulacion(sim);
    await cargarHistorial();
    informarEstado("Corrida #" + sim.id + " guardada en SQLite", "listo");
  } catch (err) {
    informarEstado(err.message, "error");
  } finally {
    btn.disabled = false;
    pildoras.forEach((p) => { p.disabled = false; });
  }
}

async function activarSimulacion(sim) {
  simulacionActual = sim;
  const p = sim.parametros;

  $("#origen").value = p.origen || "sintetica";
  $("#n").value = p.n;
  $("#semilla").value = p.semilla;
  $("#tasa_base").value = p.tasa_base;
  $("#umbral_medio").value = p.umbral_medio;
  $("#umbral_alto").value = p.umbral_alto;
  $("#k_montecarlo").value = p.k_montecarlo;
  sincronizarPildorasEscenario(p.origen || "sintetica", p.n, p.tasa_base);

  // Descargamos la cohorte completa de la corrida una sola vez para filtrado,
  // histograma desglosado UCI e inspección lateral instantáneos en cliente.
  const respuestaEst = await pedir("/api/simulaciones/" + sim.id + "/estudiantes?orden=p&sentido=desc");
  cohorteCompleta = respuestaEst.estudiantes || [];

  resetearControlesFiltro(false);
  pintarTodo(sim);
}

/* ============================================= 2. PANORAMA Y GRÁFICAS == */
function pintarTodo(sim) {
  const r = sim.resumen;
  const p = sim.parametros;
  const esUci = p.origen === "uci";

  // Badges de pestañas
  $("#badge-tab-estudiantes").textContent = String(r.n_total);
  const vOk = sim.validacion_modelo && sim.validacion_modelo.ok;
  const badgeVal = $("#badge-tab-validacion");
  badgeVal.textContent = esUci && r.evaluacion_real
    ? "AUC " + num(r.evaluacion_real.auc_roc, 2)
    : (vOk ? "4/4 Pasa" : "Revisar");
  badgeVal.className = "badge-pestana " + (vOk ? "exito" : "alerta");

  pintarCintaContexto(sim);
  pintarKPIs(sim);
  pintarBarraProporcion(sim);

  // Mostrar/ocultar controles exclusivos de UCI
  $("#controles-histograma").hidden = !esUci;
  $("#bloque-filtro-desenlace").hidden = !esUci;
  $$("#cabecera-tabla-estudiantes .col-desenlace").forEach((th) => { th.hidden = !esUci; });

  dibujarHistograma(sim);
  dibujarContribucion(sim);
  construirChipsRapidos(sim);
  recalcularTablaFiltrada();
  pintarValidacion(sim);
  programarEvaluacionWhatIf(0);
}

function pintarCintaContexto(sim) {
  const p = sim.parametros;
  const r = sim.resumen;
  const esUci = p.origen === "uci";
  const esSpadies = !esUci && Math.abs(p.tasa_base - 0.0442) < 0.001;
  const cinta = $("#banner-contexto");

  cinta.className = "cinta-contexto" + (esUci ? " es-real" : esSpadies ? " es-spadies" : "");

  const etiquetaFuente = esUci
    ? '<span class="insignia-fuente real">Dataset Real UCI</span>'
    : esSpadies
      ? '<span class="insignia-fuente spadies">Simulada · SPADIES 3.0</span>'
      : '<span class="insignia-fuente sintetica">Simulada · Montecarlo</span>';

  const titulo = esUci
    ? "Predict Students' Dropout and Academic Success (Realinho et al., 2022)"
    : esSpadies
      ? "Cohorte sintética calibrada a tasa universitaria oficial MEN (2024)"
      : "Cohorte sintética de referencia (alerta temprana universitaria)";

  const extraUci = esUci && r.evaluacion_real
    ? `<span>AUC–ROC: <strong>${num(r.evaluacion_real.auc_roc, 4)}</strong></span>`
    : `<span>Semilla: <strong>${p.semilla}</strong></span>`;

  cinta.innerHTML = `
    <div class="cinta-principal">
      ${etiquetaFuente}
      <strong>Corrida #${sim.id}</strong>
      <span class="texto-suave">· ${escapar(titulo)}</span>
    </div>
    <div class="cinta-metricas">
      <span>Cohorte: <strong>${r.n_validos}</strong>/${r.n_total} válidos</span>
      <span>Tasa base: <strong>${pct(p.tasa_base, 2)}</strong></span>
      <span>b₀: <strong>${num(p.b0_calibrado, 4)}</strong></span>
      ${extraUci}
    </div>`;
}

function pintarKPIs(sim) {
  const r = sim.resumen;
  const p = sim.parametros;
  const esUci = p.origen === "uci" && r.evaluacion_real;

  const sextaTarjeta = esUci
    ? `<div class="kpi-card bajo filtrable" data-kpi-chip="dropout" title="Filtrar desertores reales del dataset UCI">
         <span class="kpi-etiqueta">AUC–ROC Empírico <span>↗</span></span>
         <span class="kpi-valor">${num(r.evaluacion_real.auc_roc, 4)}</span>
         <span class="kpi-detalle">${r.evaluacion_real.n_desertores_reales} desertores · ${r.evaluacion_real.n_graduados_reales} graduados</span>
       </div>`
    : `<div class="kpi-card revision filtrable" data-kpi-chip="revision" title="Ver registros rechazados por el Paso 1">
         <span class="kpi-etiqueta">Revisión humana <span>↗</span></span>
         <span class="kpi-valor">${r.n_revision_humana}</span>
         <span class="kpi-detalle">Rechazados en Paso 1 (sin p inventada)</span>
       </div>`;

  $("#indicadores").innerHTML = `
    <div class="kpi-card filtrable" data-kpi-chip="todos" title="Mostrar toda la cohorte">
      <span class="kpi-etiqueta">Índice de riesgo general</span>
      <span class="kpi-valor">${pct(r.indice_general, 2)}</span>
      <span class="kpi-detalle">Objetivo ${pct(p.tasa_base, 2)} · b₀ = ${num(p.b0_calibrado, 3)}</span>
    </div>
    <div class="kpi-card alto filtrable" data-kpi-chip="alto" title="Filtrar estudiantes en riesgo alto">
      <span class="kpi-etiqueta">Riesgo alto <span>↗</span></span>
      <span class="kpi-valor" style="color:var(--alto)">${pct(r.pct_alto / 100, 1)}</span>
      <span class="kpi-detalle">${r.conteo_nivel.alto} alumnos · p ≥ ${num(p.umbral_alto, 2)}</span>
    </div>
    <div class="kpi-card medio filtrable" data-kpi-chip="medio" title="Filtrar estudiantes en riesgo medio">
      <span class="kpi-etiqueta">Riesgo medio <span>↗</span></span>
      <span class="kpi-valor" style="color:var(--medio)">${pct(r.pct_medio / 100, 1)}</span>
      <span class="kpi-detalle">${r.conteo_nivel.medio} alumnos · ${num(p.umbral_medio, 2)} ≤ p &lt; ${num(p.umbral_alto, 2)}</span>
    </div>
    <div class="kpi-card bajo filtrable" data-kpi-chip="bajo" title="Filtrar estudiantes en riesgo bajo">
      <span class="kpi-etiqueta">Riesgo bajo <span>↗</span></span>
      <span class="kpi-valor" style="color:var(--bajo)">${pct(r.pct_bajo / 100, 1)}</span>
      <span class="kpi-detalle">${r.conteo_nivel.bajo} alumnos · p &lt; ${num(p.umbral_medio, 2)}</span>
    </div>
    <div class="kpi-card filtrable" data-kpi-chip="intervencion" title="Filtrar estudiantes que requieren acompañamiento">
      <span class="kpi-etiqueta">Requieren apoyo <span>↗</span></span>
      <span class="kpi-valor">${pct(r.pct_intervencion / 100, 1)}</span>
      <span class="kpi-detalle">${r.n_intervencion} de ${r.n_validos} estudiantes válidos</span>
    </div>
    ${sextaTarjeta}`;

  $$("#indicadores [data-kpi-chip]").forEach((card) => {
    card.addEventListener("click", () => {
      aplicarChipRapido(card.dataset.kpiChip);
      $(".seccion-tabla").scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

function pintarBarraProporcion(sim) {
  const cont = $("#barra-proporcion-cohorte");
  const r = sim.resumen;
  if (!r.n_total) {
    cont.hidden = true;
    return;
  }
  cont.hidden = false;
  const total = r.n_total;
  const wBajo = (100 * r.conteo_nivel.bajo) / total;
  const wMedio = (100 * r.conteo_nivel.medio) / total;
  const wAlto = (100 * r.conteo_nivel.alto) / total;
  const wRev = (100 * r.n_revision_humana) / total;

  cont.innerHTML = `
    <div class="fila-proporcion">
      <div class="pista-apilada" role="img" aria-label="Composición de la cohorte por nivel de riesgo">
        <div class="seg-apilado" style="width:${wBajo.toFixed(2)}%;background:var(--bajo)" title="Bajo: ${r.conteo_nivel.bajo}"></div>
        <div class="seg-apilado" style="width:${wMedio.toFixed(2)}%;background:var(--medio)" title="Medio: ${r.conteo_nivel.medio}"></div>
        <div class="seg-apilado" style="width:${wAlto.toFixed(2)}%;background:var(--alto)" title="Alto: ${r.conteo_nivel.alto}"></div>
        ${wRev > 0 ? `<div class="seg-apilado" style="width:${wRev.toFixed(2)}%;background:var(--revision)" title="Revisión humana: ${r.n_revision_humana}"></div>` : ""}
      </div>
      <div class="leyenda-apilada">
        <span class="item-leyenda"><i class="cuadro-color" style="background:var(--bajo)"></i>Bajo: <strong>${r.conteo_nivel.bajo}</strong> (${wBajo.toFixed(1)}%)</span>
        <span class="item-leyenda"><i class="cuadro-color" style="background:var(--medio)"></i>Medio: <strong>${r.conteo_nivel.medio}</strong> (${wMedio.toFixed(1)}%)</span>
        <span class="item-leyenda"><i class="cuadro-color" style="background:var(--alto)"></i>Alto: <strong>${r.conteo_nivel.alto}</strong> (${wAlto.toFixed(1)}%)</span>
        <span class="item-leyenda"><i class="cuadro-color" style="background:var(--revision)"></i>Revisión Paso 1: <strong>${r.n_revision_humana}</strong> (${wRev.toFixed(1)}%)</span>
      </div>
    </div>`;
}

$("#chk-desglose-real").addEventListener("change", () => {
  if (simulacionActual) dibujarHistograma(simulacionActual);
});

function dibujarHistograma(sim) {
  const destino = $("#grafica-histograma");
  const probs = (sim.resumen && sim.resumen.probabilidades) || [];
  const params = sim.parametros;
  if (!probs.length) {
    destino.innerHTML = '<p class="vacio">Sin probabilidades válidas para graficar.</p>';
    return;
  }

  const esUci = params.origen === "uci" && $("#chk-desglose-real").checked;
  const ancho = 580, alto = 275;
  const m = { arriba: 22, derecha: 18, abajo: 46, izquierda: 46 };
  const anchoU = ancho - m.izquierda - m.derecha;
  const altoU = alto - m.arriba - m.abajo;

  const maxP = Math.max(...probs);
  const limite = Math.min(1, Math.max(0.45, Math.ceil(maxP * 10.5) / 10));
  const nBins = 24;
  const anchoBin = limite / nBins;

  const binsTotal = new Array(nBins).fill(0);
  const binsDrop = new Array(nBins).fill(0);
  const binsGrad = new Array(nBins).fill(0);

  if (esUci && cohorteCompleta.length) {
    cohorteCompleta.forEach((e) => {
      if (!e.resultado) return;
      let idx = Math.floor(e.resultado.p / anchoBin);
      if (idx >= nBins) idx = nBins - 1;
      if (idx < 0) idx = 0;
      binsTotal[idx] += 1;
      if (e.desenlace_real === "Dropout") binsDrop[idx] += 1;
      else binsGrad[idx] += 1;
    });
  } else {
    probs.forEach((p) => {
      let idx = Math.floor(p / anchoBin);
      if (idx >= nBins) idx = nBins - 1;
      if (idx < 0) idx = 0;
      binsTotal[idx] += 1;
    });
  }

  const maxBin = Math.max(...binsTotal, 1);
  const x = (v) => m.izquierda + (v / limite) * anchoU;
  const y = (c) => m.arriba + altoU - (c / maxBin) * altoU;

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Histograma de probabilidades">`;

  for (let i = 0; i <= 4; i++) {
    const c = (maxBin / 4) * i;
    const py = y(c);
    svg += `<line x1="${m.izquierda}" y1="${py}" x2="${ancho - m.derecha}" y2="${py}" stroke="var(--svg-rejilla)" stroke-width="1"/>`;
    svg += `<text x="${m.izquierda - 7}" y="${py + 4}" font-size="11" fill="var(--svg-texto)" text-anchor="end">${Math.round(c)}</text>`;
  }

  binsTotal.forEach((total, i) => {
    if (!total) return;
    const ini = i * anchoBin;
    const fin = (i + 1) * anchoBin;
    const bx = x(ini);
    const bw = Math.max(2, x(fin) - bx - 1.8);

    if (esUci) {
      const cGrad = binsGrad[i];
      const cDrop = binsDrop[i];
      const yTotal = y(total);
      const yDrop = y(cDrop);
      const hDrop = m.arriba + altoU - yDrop;
      const hGrad = yDrop - yTotal;

      if (cGrad > 0) {
        svg += `<rect x="${bx}" y="${yTotal}" width="${bw}" height="${hGrad}" fill="${COLOR_NIVEL.bajo}" opacity="0.78" rx="1.5">
          <title>[${num(ini, 2)} – ${num(fin, 2)}] Graduados reales: ${cGrad} · Desertores reales: ${cDrop}</title></rect>`;
      }
      if (cDrop > 0) {
        svg += `<rect x="${bx}" y="${yDrop}" width="${bw}" height="${hDrop}" fill="${COLOR_NIVEL.alto}" opacity="0.86" rx="1.5">
          <title>[${num(ini, 2)} – ${num(fin, 2)}] Desertores reales: ${cDrop} · Graduados reales: ${cGrad}</title></rect>`;
      }
    } else {
      const centro = (i + 0.5) * anchoBin;
      const niv = centro >= params.umbral_alto ? "alto" : centro >= params.umbral_medio ? "medio" : "bajo";
      const by = y(total);
      svg += `<rect x="${bx}" y="${by}" width="${bw}" height="${m.arriba + altoU - by}" fill="${COLOR_NIVEL[niv]}" opacity="0.85" rx="2">
        <title>${total} estudiante(s) con p entre ${pct(ini, 1)} y ${pct(fin, 1)}</title></rect>`;
    }
  });

  // Umbrales y media
  [
    [params.umbral_medio, "Medio " + pct(params.umbral_medio, 0), COLOR_NIVEL.medio],
    [params.umbral_alto, "Alto " + pct(params.umbral_alto, 0), COLOR_NIVEL.alto]
  ].forEach(([valor, etq, col]) => {
    if (valor > limite) return;
    const px = x(valor);
    svg += `<line x1="${px}" y1="${m.arriba}" x2="${px}" y2="${m.arriba + altoU}" stroke="${col}" stroke-width="1.6" stroke-dasharray="5 3"/>`;
    svg += `<text x="${px + 4}" y="${m.arriba + 11}" font-size="10.5" font-weight="700" fill="${col}">${etq}</text>`;
  });

  if (esUci) {
    svg += `<g transform="translate(${ancho - 195}, ${m.arriba + 4})">
      <rect x="0" y="0" width="9" height="9" rx="2" fill="${COLOR_NIVEL.alto}" opacity="0.86"/>
      <text x="13" y="8" font-size="10.5" fill="var(--svg-titulo)">Desertó real</text>
      <rect x="88" y="0" width="9" height="9" rx="2" fill="${COLOR_NIVEL.bajo}" opacity="0.78"/>
      <text x="101" y="8" font-size="10.5" fill="var(--svg-titulo)">Graduado real</text>
    </g>`;
  }

  svg += `<line x1="${m.izquierda}" y1="${m.arriba + altoU}" x2="${ancho - m.derecha}" y2="${m.arriba + altoU}" stroke="var(--svg-eje)" stroke-width="1"/>`;
  for (let i = 0; i <= 5; i++) {
    const v = (limite / 5) * i;
    const px = x(v);
    svg += `<text x="${px}" y="${m.arriba + altoU + 16}" font-size="11" fill="var(--svg-texto)" text-anchor="middle">${pct(v, 0)}</text>`;
  }
  svg += `<text x="${m.izquierda + anchoU / 2}" y="${alto - 7}" font-size="11.5" fill="var(--svg-titulo)" text-anchor="middle">Probabilidad estimada de deserción (p)</text>`;
  svg += `</svg>`;

  destino.innerHTML = svg;
}

function dibujarContribucion(sim) {
  const destino = $("#grafica-contribucion");
  const contribs = sim.resumen.contribucion_promedio;
  const subs = sim.resumen.subpuntaje_promedio;
  const probsDim = sim.resumen.problemas_por_dimension || {};
  const coefs = sim.parametros.coeficientes;

  const ancho = 580, alto = 275;
  const m = { arriba: 18, derecha: 155, abajo: 46, izquierda: 94 };
  const anchoU = ancho - m.izquierda - m.derecha;
  const altoU = alto - m.arriba - m.abajo;

  const orden = DIMENSIONES.slice().sort((a, b) => contribs[b] - contribs[a]);
  const maxC = Math.max(...DIMENSIONES.map((d) => contribs[d]), 0.05);
  const paso = altoU / orden.length;
  const altoBarra = Math.min(34, paso - 14);

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Contribución promedio al logit por dimensión">`;

  for (let i = 0; i <= 4; i++) {
    const v = (maxC / 4) * i;
    const px = m.izquierda + (v / maxC) * anchoU;
    svg += `<line x1="${px}" y1="${m.arriba}" x2="${px}" y2="${m.arriba + altoU}" stroke="var(--svg-rejilla)" stroke-width="1"/>`;
    svg += `<text x="${px}" y="${m.arriba + altoU + 16}" font-size="11" fill="var(--svg-texto)" text-anchor="middle">${num(v, 2)}</text>`;
  }

  orden.forEach((dim, i) => {
    const val = contribs[dim];
    const by = m.arriba + i * paso + (paso - altoBarra) / 2;
    const bw = Math.max(3, (val / maxC) * anchoU);
    const nCrit = probsDim[dim] || 0;

    svg += `<g class="barra-clicable" data-dim-click="${dim}">
      <text x="${m.izquierda - 10}" y="${by + altoBarra / 2 + 4}" font-size="12" font-weight="700" fill="var(--svg-titulo)" text-anchor="end">${NOMBRE_DIM[dim]}</text>
      <rect x="${m.izquierda}" y="${by}" width="${bw}" height="${altoBarra}" fill="${COLOR_DIM[dim]}" opacity="0.88" rx="4">
        <title>Clic para filtrar problemas en ${NOMBRE_DIM[dim]} (${nCrit} estudiantes con s ≥ 0,60)</title>
      </rect>
      <text x="${m.izquierda + bw + 8}" y="${by + altoBarra / 2 - 2}" font-size="11.5" font-weight="700" fill="var(--svg-titulo)">
        ${num(val, 3)} <tspan font-weight="400" fill="var(--svg-texto)" font-size="10.5">(b=${num(coefs[dim], 1)} · s̄=${num(subs[dim], 2)})</tspan>
      </text>
      <text x="${m.izquierda + bw + 8}" y="${by + altoBarra / 2 + 12}" font-size="10.5" fill="${nCrit > 0 ? COLOR_DIM[dim] : "var(--svg-texto)"}" font-weight="600">
        ${nCrit} con problema (s ≥ 0,60)
      </text>
    </g>`;
  });

  svg += `<line x1="${m.izquierda}" y1="${m.arriba}" x2="${m.izquierda}" y2="${m.arriba + altoU}" stroke="var(--svg-eje)" stroke-width="1"/>`;
  svg += `<text x="${m.izquierda + anchoU / 2}" y="${alto - 7}" font-size="11.5" fill="var(--svg-titulo)" text-anchor="middle">Aporte medio al logit (b_d · s̄_d)</text>`;
  svg += `</svg>`;

  destino.innerHTML = svg;

  destino.querySelectorAll("[data-dim-click]").forEach((g) => {
    g.addEventListener("click", () => {
      const dim = g.getAttribute("data-dim-click");
      $("#f-dimension").value = $("#f-dimension").value === dim ? "" : dim;
      chipActivo = "personalizado";
      actualizarEstadoChips();
      recalcularTablaFiltrada();
      $(".seccion-tabla").scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

/* ========================================== 3. EXPLORADOR Y PAGINACIÓN == */
function construirChipsRapidos(sim) {
  const r = sim.resumen;
  const esUci = sim.parametros.origen === "uci" && r.evaluacion_real;
  const items = [
    ["todos", "Todos", r.n_total],
    ["alto", "Riesgo Alto", r.conteo_nivel.alto],
    ["medio", "Riesgo Medio", r.conteo_nivel.medio],
    ["intervencion", "Requieren Apoyo", r.n_intervencion]
  ];
  if (r.n_revision_humana > 0 || !esUci) {
    items.push(["revision", "Revisión Humana", r.n_revision_humana]);
  }
  if (esUci) {
    items.push(["dropout", "Desertó Real (UCI)", r.evaluacion_real.n_desertores_reales]);
    items.push(["graduate", "Graduado Real (UCI)", r.evaluacion_real.n_graduados_reales]);
  }

  $("#chips-rapidos").innerHTML = items.map(([clave, texto, conteo]) => `
    <button type="button" class="chip-filtro ${chipActivo === clave ? "activo" : ""}" data-chip="${clave}">
      <span>${escapar(texto)}</span>
      <span class="conteo-chip">(${conteo})</span>
    </button>
  `).join("");

  $$("#chips-rapidos [data-chip]").forEach((btn) => {
    btn.addEventListener("click", () => aplicarChipRapido(btn.dataset.chip));
  });
}

function aplicarChipRapido(clave) {
  resetearControlesFiltro(false);
  chipActivo = clave;

  if (clave === "alto" || clave === "medio" || clave === "bajo") {
    $("#f-nivel").value = clave;
  } else if (clave === "intervencion") {
    $("#f-intervencion").value = "true";
  } else if (clave === "revision") {
    $("#f-revision").checked = true;
  } else if (clave === "dropout") {
    $("#f-desenlace").value = "Dropout";
  } else if (clave === "graduate") {
    $("#f-desenlace").value = "Graduate";
  }
  actualizarEstadoChips();
  recalcularTablaFiltrada();
}

function actualizarEstadoChips() {
  $$("#chips-rapidos [data-chip]").forEach((b) => {
    b.classList.toggle("activo", b.dataset.chip === chipActivo);
  });
  const hayAlgunFiltro = Boolean(
    $("#f-buscar").value.trim() ||
    $("#f-nivel").value ||
    $("#f-intervencion").value ||
    $("#f-dimension").value ||
    $("#f-desenlace").value ||
    $("#f-revision").checked
  );
  $("#btn-limpiar-filtros").hidden = !hayAlgunFiltro;
}

function resetearControlesFiltro(recalcular = true) {
  $("#f-buscar").value = "";
  $("#f-nivel").value = "";
  $("#f-intervencion").value = "";
  $("#f-dimension").value = "";
  $("#f-desenlace").value = "";
  $("#f-revision").checked = false;
  chipActivo = "todos";
  actualizarEstadoChips();
  if (recalcular) recalcularTablaFiltrada();
}

$("#btn-limpiar-filtros").addEventListener("click", () => resetearControlesFiltro(true));

["#f-nivel", "#f-intervencion", "#f-dimension", "#f-desenlace", "#f-orden", "#f-revision"].forEach((sel) => {
  $(sel).addEventListener("change", () => {
    chipActivo = "personalizado";
    actualizarEstadoChips();
    recalcularTablaFiltrada();
  });
});

$("#f-buscar").addEventListener("input", () => {
  clearTimeout(timerBusqueda);
  timerBusqueda = setTimeout(() => {
    chipActivo = "personalizado";
    actualizarEstadoChips();
    recalcularTablaFiltrada();
  }, 90);
});

$("#tamano-pagina").addEventListener("change", () => {
  tamanoPagina = Number($("#tamano-pagina").value) || 25;
  paginaActual = 1;
  renderizarPaginaTabla();
});

$("#btn-pag-ant").addEventListener("click", () => {
  if (paginaActual > 1) {
    paginaActual -= 1;
    renderizarPaginaTabla();
  }
});

$("#btn-pag-sig").addEventListener("click", () => {
  const totalPags = Math.max(1, Math.ceil(estudiantesFiltrados.length / tamanoPagina));
  if (paginaActual < totalPags) {
    paginaActual += 1;
    renderizarPaginaTabla();
  }
});

function recalcularTablaFiltrada() {
  const q = $("#f-buscar").value.trim().toLowerCase();
  const fNivel = $("#f-nivel").value;
  const fInterv = $("#f-intervencion").value;
  const fDim = $("#f-dimension").value;
  const fDes = $("#f-desenlace").value;
  const soloRev = $("#f-revision").checked;
  const [campoOrden, sentido] = $("#f-orden").value.split("|");
  const desc = sentido !== "asc";

  estudiantesFiltrados = cohorteCompleta.filter((e) => {
    if (soloRev && e.valido) return false;
    if (q && !String(e.codigo || "").toLowerCase().includes(q)) return false;
    if (fDes && e.desenlace_real !== fDes) return false;

    if (fNivel || fInterv || fDim) {
      if (!e.resultado) return false;
      if (fNivel && e.resultado.nivel !== fNivel) return false;
      if (fInterv === "true" && !e.resultado.requiere_intervencion) return false;
      if (fInterv === "false" && e.resultado.requiere_intervencion) return false;
      if (fDim && !e.resultado.problemas.includes(fDim)) return false;
    }
    return true;
  });

  const pesoNivel = { alto: 3, medio: 2, bajo: 1 };
  const claveSub = {
    s_academico: "academica",
    s_financiero: "financiera",
    s_laboral: "laboral",
    s_personal: "personal"
  };

  estudiantesFiltrados.sort((a, b) => {
    if (campoOrden === "codigo") {
      const cmp = a.codigo.localeCompare(b.codigo);
      return desc ? -cmp : cmp;
    }
    // Los registros inválidos (sin probabilidad) siempre quedan al final
    const aNulo = a.resultado == null;
    const bNulo = b.resultado == null;
    if (aNulo && bNulo) return a.id - b.id;
    if (aNulo) return 1;
    if (bNulo) return -1;

    let va = 0, vb = 0;
    if (campoOrden === "p") {
      va = a.resultado.p; vb = b.resultado.p;
    } else if (campoOrden === "nivel") {
      va = pesoNivel[a.resultado.nivel] || 0;
      vb = pesoNivel[b.resultado.nivel] || 0;
      if (va === vb) { va = a.resultado.p; vb = b.resultado.p; }
    } else if (claveSub[campoOrden]) {
      const d = claveSub[campoOrden];
      va = a.resultado.subpuntajes[d];
      vb = b.resultado.subpuntajes[d];
    }
    if (va === vb) return a.id - b.id;
    return desc ? (vb - va) : (va - vb);
  });

  paginaActual = 1;
  renderizarPaginaTabla();
}

function sparkbarHTML(valor, color, umbralProblema) {
  const critico = valor >= umbralProblema;
  const ancho = Math.max(0, Math.min(100, valor * 100)).toFixed(1);
  return `
    <td class="spark-celda">
      <div class="spark-sup ${critico ? "critico" : ""}">
        <span>${num(valor, 2)}</span>
        ${critico ? '<span title="Supera el umbral de problema (0,60)">⚠</span>' : ""}
      </div>
      <div class="spark-pista">
        <div class="spark-relleno" style="width:${ancho}%;background:${critico ? COLOR_NIVEL.alto : color}"></div>
      </div>
    </td>`;
}

function renderizarPaginaTabla() {
  const esUci = Boolean(simulacionActual && simulacionActual.parametros.origen === "uci");
  const umbralProb = (simulacionActual && simulacionActual.parametros.umbral_problema) || 0.60;
  const total = estudiantesFiltrados.length;
  const totalPags = Math.max(1, Math.ceil(total / tamanoPagina));
  if (paginaActual > totalPags) paginaActual = totalPags;

  const inicio = (paginaActual - 1) * tamanoPagina;
  const fin = Math.min(inicio + tamanoPagina, total);
  const pagina = estudiantesFiltrados.slice(inicio, fin);

  $("#f-buscar").placeholder = esUci ? "Ej. UCI-0015" : "Ej. UNA-0042";
  $("#caption-tabla").textContent =
    (esUci ? "Dataset Real UCI" : "Cohorte Sintética") +
    " · " + total + " estudiante(s) coinciden · clic en una fila para diagnóstico completo";

  $("#info-paginacion").textContent = total
    ? `Mostrando ${inicio + 1}–${fin} de ${total} estudiantes`
    : "0 estudiantes";
  $("#indicador-pagina").textContent = `${paginaActual} / ${totalPags}`;
  $("#btn-pag-ant").disabled = paginaActual <= 1;
  $("#btn-pag-sig").disabled = paginaActual >= totalPags;

  const colSpan = esUci ? 10 : 9;
  if (!pagina.length) {
    $("#cuerpo-tabla").innerHTML =
      `<tr><td colspan="${colSpan}" class="vacio" style="padding:20px;text-align:center">Ningún estudiante cumple los filtros activos.</td></tr>`;
    return;
  }

  $("#cuerpo-tabla").innerHTML = pagina.map((est) => {
    const sel = est.id === estudianteInspectorId ? " seleccionada" : "";
    const celdaDesenlace = esUci
      ? `<td>${est.desenlace_real === "Dropout"
          ? '<span class="badge-desenlace dropout">Desertó</span>'
          : '<span class="badge-desenlace graduate">Graduado</span>'}</td>`
      : "";

    if (!est.resultado) {
      const detalleMotivo = est.mensaje_revision ||
        `${est.motivo_revision || "invalido"} (${est.campo_revision || "registro"})`;
      return `<tr data-id="${est.id}" class="${sel.trim()}">
        <td><strong>${escapar(est.codigo)}</strong></td>
        ${celdaDesenlace}
        <td colspan="6" class="texto-suave">
          Sin probabilidad · <code>${escapar(est.motivo_revision)}</code> — ${escapar(detalleMotivo)}
        </td>
        <td><span class="insignia revision">Paso 1</span></td>
        <td><span class="texto-no">Revisión humana</span></td>
      </tr>`;
    }

    const r = est.resultado;
    const colNivel = COLOR_NIVEL[r.nivel] || COLOR_NIVEL.bajo;
    const izq = Math.max(0, Math.min(100, r.p5 * 100)).toFixed(1);
    const anchoBanda = Math.max(2, Math.min(100 - Number(izq), (r.p95 - r.p5) * 100)).toFixed(1);
    const posP = Math.max(0, Math.min(99, r.p * 100)).toFixed(1);

    return `<tr data-id="${est.id}" class="${sel.trim()}">
      <td><strong>${escapar(est.codigo)}</strong></td>
      ${celdaDesenlace}
      <td class="celda-prob">
        <div class="prob-fila-sup">
          <span class="prob-principal" style="color:${colNivel}">${pct(r.p, 1)}</span>
          <span class="prob-rango">${pct(r.p5, 0)}–${pct(r.p95, 0)}</span>
        </div>
        <div class="mini-intervalo">
          <div class="mini-intervalo-banda" style="left:${izq}%;width:${anchoBanda}%;background:${colNivel}"></div>
          <div class="mini-intervalo-punto" style="left:${posP}%;background:${colNivel}"></div>
        </div>
      </td>
      <td><span class="insignia ${escapar(r.nivel)}">${escapar(r.nivel)}</span></td>
      ${sparkbarHTML(r.subpuntajes.academica, COLOR_DIM.academica, umbralProb)}
      ${sparkbarHTML(r.subpuntajes.financiera, COLOR_DIM.financiera, umbralProb)}
      ${sparkbarHTML(r.subpuntajes.laboral, COLOR_DIM.laboral, umbralProb)}
      ${sparkbarHTML(r.subpuntajes.personal, COLOR_DIM.personal, umbralProb)}
      <td><span class="etiqueta-dim dim-${escapar(r.factor_principal)}">${escapar(NOMBRE_DIM[r.factor_principal])}</span></td>
      <td>${r.requiere_intervencion
        ? `<span class="pill-intervencion">Sí (${r.intervenciones.length})</span>`
        : '<span class="texto-no">No</span>'}</td>
    </tr>`;
  }).join("");
}

// Delegación única de clics en la tabla (sin miles de listeners)
$("#cuerpo-tabla").addEventListener("click", (ev) => {
  const fila = ev.target.closest("tr[data-id]");
  if (!fila) return;
  abrirInspectorEstudiante(Number(fila.dataset.id));
});

/* Exportación CSV enriquecida */
$("#btn-exportar-csv").addEventListener("click", () => {
  if (!estudiantesFiltrados.length) {
    informarEstado("No hay estudiantes filtrados para exportar.", "error");
    return;
  }
  const escaparCelda = (v) => {
    const t = v == null ? "" : String(v);
    return (t.includes(",") || t.includes('"') || t.includes("\n"))
      ? '"' + t.replace(/"/g, '""') + '"'
      : t;
  };
  const cabeceras = [
    "codigo", "desenlace_real", "valido", "motivo_revision", "campo_revision",
    "mensaje_revision", "p", "p5", "p95", "nivel", "s_academico", "s_financiero",
    "s_laboral", "s_personal", "factor_principal", "problemas", "requiere_intervencion"
  ];
  const lineas = [cabeceras.join(",")];
  estudiantesFiltrados.forEach((e) => {
    const r = e.resultado;
    lineas.push([
      e.codigo,
      e.desenlace_real || "",
      e.valido ? "1" : "0",
      e.motivo_revision || "",
      e.campo_revision || "",
      e.mensaje_revision || "",
      r ? num(r.p, 4) : "",
      r ? num(r.p5, 4) : "",
      r ? num(r.p95, 4) : "",
      r ? r.nivel : "",
      r ? num(r.subpuntajes.academica, 4) : "",
      r ? num(r.subpuntajes.financiera, 4) : "",
      r ? num(r.subpuntajes.laboral, 4) : "",
      r ? num(r.subpuntajes.personal, 4) : "",
      r ? r.factor_principal : "",
      r ? r.problemas.join(";") : "",
      r ? (r.requiere_intervencion ? "1" : "0") : ""
    ].map(escaparCelda).join(","));
  });

  const blob = new Blob(["\uFEFF" + lineas.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `simulacion_${simulacionActual ? simulacionActual.id : "cohorte"}_estudiantes.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  informarEstado(`CSV exportado (${estudiantesFiltrados.length} registros).`, "listo");
});

/* ====================================== 4. INSPECTOR LATERAL + RADAR/WF == */
function abrirInspectorEstudiante(estudianteId) {
  const idx = estudiantesFiltrados.findIndex((e) => e.id === estudianteId);
  const est = idx >= 0
    ? estudiantesFiltrados[idx]
    : cohorteCompleta.find((e) => e.id === estudianteId);
  if (!est) return;

  estudianteInspectorId = est.id;
  $$("#cuerpo-tabla tr[data-id]").forEach((tr) => {
    tr.classList.toggle("seleccionada", Number(tr.dataset.id) === est.id);
  });

  $("#velo-inspector").hidden = false;
  $("#inspector-estudiante").hidden = false;

  if (idx >= 0) {
    $("#posicion-inspector").textContent = `${idx + 1} de ${estudiantesFiltrados.length}`;
    $("#btn-est-ant").disabled = idx <= 0;
    $("#btn-est-sig").disabled = idx >= estudiantesFiltrados.length - 1;
  } else {
    $("#posicion-inspector").textContent = "";
    $("#btn-est-ant").disabled = true;
    $("#btn-est-sig").disabled = true;
  }

  pintarContenidoInspector(est);
}

function cerrarInspector() {
  estudianteInspectorId = null;
  $("#velo-inspector").hidden = true;
  $("#inspector-estudiante").hidden = true;
  $$("#cuerpo-tabla tr.seleccionada").forEach((tr) => tr.classList.remove("seleccionada"));
}

function navegarInspector(delta) {
  if (estudianteInspectorId == null) return;
  const idx = estudiantesFiltrados.findIndex((e) => e.id === estudianteInspectorId);
  if (idx < 0) return;
  const nuevoIdx = idx + delta;
  if (nuevoIdx < 0 || nuevoIdx >= estudiantesFiltrados.length) return;

  const nuevaPag = Math.floor(nuevoIdx / tamanoPagina) + 1;
  if (nuevaPag !== paginaActual) {
    paginaActual = nuevaPag;
    renderizarPaginaTabla();
  }
  abrirInspectorEstudiante(estudiantesFiltrados[nuevoIdx].id);
}

$("#btn-cerrar-inspector").addEventListener("click", cerrarInspector);
$("#velo-inspector").addEventListener("click", cerrarInspector);
$("#btn-est-ant").addEventListener("click", () => navegarInspector(-1));
$("#btn-est-sig").addEventListener("click", () => navegarInspector(1));

document.addEventListener("keydown", (ev) => {
  if ($("#inspector-estudiante").hidden) return;
  if (ev.key === "Escape") {
    cerrarInspector();
  } else if (ev.key === "ArrowDown") {
    ev.preventDefault();
    navegarInspector(1);
  } else if (ev.key === "ArrowUp") {
    ev.preventDefault();
    navegarInspector(-1);
  }
});

function svgRadar4D(subpuntajes, subpuntajesBase = null, umbral = 0.60) {
  const tam = 210, cx = 105, cy = 105, radio = 68;
  // Arriba: Académica, Derecha: Financiera, Abajo: Laboral, Izquierda: Personal
  const dirs = [
    ["academica", 0, -1, "middle", cx, cy - radio - 12],
    ["financiera", 1, 0, "start", cx + radio + 8, cy + 4],
    ["laboral", 0, 1, "middle", cx, cy + radio + 16],
    ["personal", -1, 0, "end", cx - radio - 8, cy + 4]
  ];

  const pts = (s) => dirs.map(([d, dx, dy]) => {
    const v = Math.max(0, Math.min(1, s[d] || 0));
    return `${(cx + dx * radio * v).toFixed(1)},${(cy + dy * radio * v).toFixed(1)}`;
  }).join(" ");

  const rUmbral = radio * umbral;
  let svg = `<svg viewBox="0 0 ${tam} ${tam}" role="img" aria-label="Perfil radar de las 4 dimensiones">`;

  [0.5, 1.0].forEach((esc) => {
    const rr = radio * esc;
    svg += `<polygon points="${cx},${cy - rr} ${cx + rr},${cy} ${cx},${cy + rr} ${cx - rr},${cy}"
             fill="none" stroke="var(--svg-rejilla)" stroke-width="1"/>`;
  });
  // Anillo de problema (0.60)
  svg += `<polygon points="${cx},${cy - rUmbral} ${cx + rUmbral},${cy} ${cx},${cy + rUmbral} ${cx - rUmbral},${cy}"
           fill="none" stroke="${COLOR_NIVEL.alto}" stroke-width="1" stroke-dasharray="3 2" opacity="0.65"/>`;

  dirs.forEach(([d, dx, dy, anchor, tx, ty]) => {
    svg += `<line x1="${cx}" y1="${cy}" x2="${cx + dx * radio}" y2="${cy + dy * radio}" stroke="var(--svg-rejilla)" stroke-width="1"/>`;
    svg += `<text x="${tx}" y="${ty}" font-size="10" font-weight="700" fill="${COLOR_DIM[d]}" text-anchor="${anchor}">${NOMBRE_DIM[d].slice(0, 5)}.</text>`;
  });

  if (subpuntajesBase) {
    svg += `<polygon points="${pts(subpuntajesBase)}" fill="none" stroke="var(--svg-texto)" stroke-width="1.5" stroke-dasharray="4 2"/>`;
  }

  svg += `<polygon points="${pts(subpuntajes)}" fill="var(--primario)" fill-opacity="0.22" stroke="var(--primario)" stroke-width="2"/>`;
  dirs.forEach(([d, dx, dy]) => {
    const v = Math.max(0, Math.min(1, subpuntajes[d] || 0));
    svg += `<circle cx="${cx + dx * radio * v}" cy="${cy + dy * radio * v}" r="3.5" fill="${COLOR_DIM[d]}"/>`;
  });
  svg += `</svg>`;
  return svg;
}

function svgWaterfallLogit(b0, contribuciones, pFinal) {
  const ancho = 260, alto = 210;
  const m = { arriba: 18, derecha: 14, abajo: 36, izquierda: 38 };
  const anchoU = ancho - m.izquierda - m.derecha;
  const altoU = alto - m.arriba - m.abajo;

  const pasos = [
    { etq: "b₀", ini: 0, fin: b0, col: "#64748b" }
  ];
  let acum = b0;
  DIMENSIONES.forEach((d) => {
    const c = contribuciones[d] || 0;
    pasos.push({ etq: NOMBRE_DIM[d].slice(0, 4), ini: acum, fin: acum + c, col: COLOR_DIM[d] });
    acum += c;
  });
  pasos.push({ etq: "z total", ini: 0, fin: acum, col: "#0f172a", esTotal: true });

  const vals = pasos.flatMap((x) => [x.ini, x.fin, 0]);
  const minV = Math.min(...vals) - 0.4;
  const maxV = Math.max(...vals) + 0.6;
  const y = (v) => m.arriba + altoU - ((v - minV) / (maxV - minV)) * altoU;
  const y0 = y(0);
  const pasoX = anchoU / pasos.length;
  const bw = Math.min(24, pasoX - 8);

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Cascada aditiva del logit">`;
  svg += `<line x1="${m.izquierda}" y1="${y0}" x2="${ancho - m.derecha}" y2="${y0}" stroke="var(--svg-eje)" stroke-width="1" stroke-dasharray="3 2"/>`;
  svg += `<text x="${m.izquierda - 5}" y="${y0 + 3}" font-size="9.5" fill="var(--svg-texto)" text-anchor="end">0</text>`;

  pasos.forEach((item, i) => {
    const px = m.izquierda + i * pasoX + (pasoX - bw) / 2;
    const yA = y(item.ini);
    const yB = y(item.fin);
    const top = Math.min(yA, yB);
    const h = Math.max(2, Math.abs(yB - yA));
    const relleno = item.esTotal ? "var(--primario)" : item.col;
    const delta = item.esTotal ? item.fin : (item.fin - item.ini);

    svg += `<rect x="${px}" y="${top}" width="${bw}" height="${h}" fill="${relleno}" rx="2.5" opacity="0.9">
      <title>${item.etq}: ${delta >= 0 ? "+" : ""}${num(delta, 2)} (logit acum: ${num(item.fin, 2)})</title>
    </rect>`;
    svg += `<text x="${px + bw / 2}" y="${alto - 20}" font-size="9.5" fill="var(--svg-texto)" text-anchor="middle">${item.etq}</text>`;
  });

  svg += `<text x="${ancho / 2}" y="${alto - 5}" font-size="10" font-weight="700" fill="var(--svg-titulo)" text-anchor="middle">z = ${num(acum, 2)} → p = ${pct(pFinal, 1)}</text>`;
  svg += `</svg>`;
  return svg;
}

function renderizarBloqueVariablesE(datos, campoConError = null) {
  const coincideError = (campo) => {
    if (!campoConError) return false;
    if (campoConError === campo) return true;
    if (campoConError === "estrato_ingreso" && (campo === "estrato" || campo === "ingreso_hogar_smmlv")) return true;
    if (campoConError === "promedio_materias_perdidas" && (campo === "promedio" || campo === "materias_perdidas")) return true;
    return false;
  };

  return `<div class="rejilla-variables-e">
    ${DIMENSIONES.map((dim) => `
      <div class="grupo-vars">
        <h5 style="color:${COLOR_DIM[dim]}">${NOMBRE_DIM[dim]}</h5>
        <ul class="lista-vars">
          ${CAMPOS_DIM[dim].map(([campo, etq]) => `
            <li class="${coincideError(campo) ? "campo-con-error" : ""}">
              <span class="texto-suave">${escapar(etq)}</span>
              <strong>${escapar(valorLegible(campo, datos[campo]))}</strong>
            </li>`).join("")}
        </ul>
      </div>`).join("")}
  </div>`;
}

function pintarContenidoInspector(est) {
  const contenedor = $("#contenido-inspector");
  const params = simulacionActual ? simulacionActual.parametros : {};
  const badgeReal = est.desenlace_real
    ? (est.desenlace_real === "Dropout"
        ? '<span class="badge-desenlace dropout">Desenlace real: Desertó</span>'
        : '<span class="badge-desenlace graduate">Desenlace real: Graduado</span>')
    : "";

  if (!est.resultado) {
    contenedor.innerHTML = `
      <div class="ficha-cabecera">
        <div>
          <h3 class="ficha-codigo">${escapar(est.codigo)}</h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
            <span class="insignia revision">Revisión humana · Paso 1</span>
            ${badgeReal}
          </div>
        </div>
        <button type="button" class="btn-primario btn-chico" id="btn-cargar-en-whatif">
          Corregir y probar en What-If →
        </button>
      </div>

      <div class="aviso-revision">
        <strong>Por contrato no se asigna probabilidad de deserción.</strong><br>
        Motivo detectado: <code>${escapar(est.motivo_revision)}</code> en <code>${escapar(est.campo_revision)}</code>.
        ${est.mensaje_revision ? `<div style="margin-top:5px">Detalle: <em>${escapar(est.mensaje_revision)}</em>.</div>` : ""}
        ${est.error_inyectado ? `<div style="margin-top:5px;font-size:12px">Nota: registro con error inyectado a propósito (<code>${escapar(est.error_inyectado)}</code>) para ejercitar el Paso 1.</div>` : ""}
      </div>

      <div class="bloque-seccion-ficha">
        <h4>Variables del perfil recibido (E)</h4>
        ${renderizarBloqueVariablesE(est.datos, est.campo_revision)}
      </div>`;

    $("#btn-cargar-en-whatif").addEventListener("click", () => enviarEstudianteAWhatIf(est));
    return;
  }

  const r = est.resultado;
  const colNivel = COLOR_NIVEL[r.nivel];
  const escala = Math.max(0.4, Math.min(1, Math.max(r.p95 * 1.18, (params.umbral_alto || 0.35) * 1.25)));
  const posPct = (v) => Math.max(0, Math.min(100, (v / escala) * 100));

  const htmlIntervenciones = r.requiere_intervencion
    ? r.intervenciones.map((i) => `
        <div class="intervencion-card">
          <span class="prioridad-badge">Prioridad ${i.prioridad}</span>
          <strong>${escapar(i.nombre)}</strong>
          <div class="texto-suave" style="font-size:11.5px">
            Dimensión ${escapar(NOMBRE_DIM[i.dimension])} · <code>${escapar(i.tipo)}</code>
          </div>
          <ul>${i.acciones.map((a) => `<li>${escapar(a)}</li>`).join("")}</ul>
        </div>`).join("")
    : `<p class="texto-suave">No requiere intervención activa: nivel <strong>${escapar(r.nivel)}</strong>${
        r.problemas.length ? " (sin cruzar el criterio global de acompañamiento)." : " sin dimensiones críticas."
      }</p>`;

  const barrasDim = DIMENSIONES.map((dim) => {
    const s = r.subpuntajes[dim];
    const crit = r.problemas.includes(dim);
    return `
      <div class="barra-dim ${crit ? "problema" : ""}">
        <div class="fila-barra">
          <span>${NOMBRE_DIM[dim]}${crit ? " ⚠" : ""}</span>
          <span>s = ${num(s, 3)} · aporte b·s = +${num(r.contribuciones[dim], 2)}</span>
        </div>
        <div class="pista">
          <div class="relleno" style="width:${(s * 100).toFixed(1)}%;background:${COLOR_DIM[dim]}"></div>
        </div>
      </div>`;
  }).join("");

  contenedor.innerHTML = `
    <div class="ficha-cabecera">
      <div>
        <h3 class="ficha-codigo">${escapar(est.codigo)}</h3>
        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
          <span class="insignia ${escapar(r.nivel)}">Riesgo ${escapar(r.nivel)}</span>
          <span class="etiqueta-dim dim-${escapar(r.factor_principal)}">Factor: ${escapar(NOMBRE_DIM[r.factor_principal])}</span>
          ${badgeReal}
        </div>
      </div>
      <div>
        <div class="ficha-prob-grande" style="color:${colNivel}">${pct(r.p, 1)}</div>
        <div style="margin-top:6px;text-align:right">
          <button type="button" class="btn-primario btn-chico" id="btn-cargar-en-whatif">
            Simular acompañamiento →
          </button>
        </div>
      </div>
    </div>

    <div class="medidor-incertidumbre">
      <div style="display:flex;justify-content:space-between;font-size:12px">
        <span>Intervalo P5–P95 (Montecarlo 2): <strong>${pct(r.p5, 1)} – ${pct(r.p95, 1)}</strong></span>
        <span class="texto-suave">Escala 0%–${pct(escala, 0)}</span>
      </div>
      <div class="pista-incertidumbre">
        ${params.umbral_medio && params.umbral_medio <= escala
          ? `<div class="marca-umbral-barra" style="left:${posPct(params.umbral_medio)}%" title="Umbral medio ${pct(params.umbral_medio, 0)}"></div>` : ""}
        ${params.umbral_alto && params.umbral_alto <= escala
          ? `<div class="marca-umbral-barra" style="left:${posPct(params.umbral_alto)}%" title="Umbral alto ${pct(params.umbral_alto, 0)}"></div>` : ""}
        <div class="banda-p5-p95" style="left:${posPct(r.p5)}%;width:${Math.max(1.5, posPct(r.p95) - posPct(r.p5))}%;background:${colNivel}"></div>
        <div class="aguja-p" style="left:${posPct(r.p)}%;background:${colNivel}"></div>
      </div>
    </div>

    <div class="rejilla-visual-inspector">
      <div class="caja-mini-svg">
        <h4>Perfil 4D (anillo rojo = 0,60)</h4>
        ${svgRadar4D(r.subpuntajes)}
      </div>
      <div class="caja-mini-svg">
        <h4>Cascada del Logit</h4>
        ${svgWaterfallLogit(params.b0_calibrado || -4.95, r.contribuciones, r.p)}
      </div>
    </div>

    <div class="bloque-seccion-ficha">
      <h4>Subpuntajes y contribución al riesgo</h4>
      ${barrasDim}
    </div>

    <div class="bloque-seccion-ficha">
      <h4>Paso 3 · Plan de acompañamiento recomendado</h4>
      ${htmlIntervenciones}
    </div>

    <div class="bloque-seccion-ficha">
      <h4>Variables de entrada (E)</h4>
      ${renderizarBloqueVariablesE(est.datos)}
    </div>`;

  $("#btn-cargar-en-whatif").addEventListener("click", () => enviarEstudianteAWhatIf(est));
}

/* ====================================== 5. WHAT-IF CON /api/evaluar ==== */
function poblarInputsWhatIf(datos) {
  Object.entries(datos).forEach(([campo, valor]) => {
    const input = $("#wi-" + campo);
    if (!input) return;
    input.value = valor === null || valor === undefined ? "" : String(valor);
    const slider = document.querySelector(`input[type="range"][data-sync="wi-${campo}"]`);
    if (slider && typeof valor === "number" && Number.isFinite(valor)) {
      slider.value = String(valor);
    }
  });
}

function enviarEstudianteAWhatIf(est) {
  cerrarInspector();
  if (est.valido) {
    baseWhatIf = { codigo: est.codigo, datos: JSON.parse(JSON.stringify(est.datos)) };
    $("#barra-base-whatif").hidden = false;
    $("#etiqueta-base-whatif").textContent = `${est.codigo} (p = ${pct(est.resultado.p, 1)} · ${est.resultado.nivel})`;
    $("#badge-tab-whatif").textContent = est.codigo;
  } else {
    baseWhatIf = null;
    $("#barra-base-whatif").hidden = true;
    $("#badge-tab-whatif").textContent = "En vivo";
  }
  poblarInputsWhatIf(est.datos);
  activarPestana("panel-whatif");
  programarEvaluacionWhatIf(0);
}

$("#btn-restaurar-base-wi").addEventListener("click", () => {
  if (!baseWhatIf) return;
  poblarInputsWhatIf(baseWhatIf.datos);
  programarEvaluacionWhatIf(0);
});

$("#btn-quitar-base-wi").addEventListener("click", () => {
  baseWhatIf = null;
  $("#barra-base-whatif").hidden = true;
  $("#badge-tab-whatif").textContent = "En vivo";
  programarEvaluacionWhatIf(0);
});

$("#btn-aplicar-intervencion-wi").addEventListener("click", () => {
  // Simula el impacto concreto de otorgar el plan institucional del portal:
  // beca/apoyo financiero + reestructuración de deuda + flexibilidad laboral + tutoría
  const actual = leerRegistroWhatIf();
  const acompañado = Object.assign({}, actual, {
    tiene_apoyo_financiero: true,
    saldo_pendiente_cop: Math.min(Number(actual.saldo_pendiente_cop || 0), 1000000),
    asistencia_pct: Math.min(100, Math.max(Number(actual.asistencia_pct || 0), 90)),
    promedio: Math.min(5.0, Math.round((Number(actual.promedio || 0) + 0.5) * 10) / 10),
    materias_perdidas: Math.max(0, Number(actual.materias_perdidas || 0) - 1),
    apoyo_familiar: Math.min(5, Math.max(Number(actual.apoyo_familiar || 3), 4))
  });
  poblarInputsWhatIf(acompañado);
  programarEvaluacionWhatIf(0);
});

// Sincronización bidireccional entre sliders y cajas numéricas
$$('#form-whatif input[type="range"][data-sync]').forEach((slider) => {
  const idNum = slider.dataset.sync;
  const caja = $("#" + idNum);
  if (!caja) return;
  slider.addEventListener("input", () => {
    caja.value = slider.value;
    programarEvaluacionWhatIf(80);
  });
  caja.addEventListener("input", () => {
    const v = Number(caja.value);
    if (Number.isFinite(v)) slider.value = String(v);
    programarEvaluacionWhatIf(120);
  });
});

$$("#form-whatif select").forEach((sel) => {
  sel.addEventListener("change", () => programarEvaluacionWhatIf(0));
});

$$("[data-preset]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const preset = PRESETS_WHATIF[btn.dataset.preset];
    if (!preset) return;
    baseWhatIf = null;
    $("#barra-base-whatif").hidden = true;
    $("#badge-tab-whatif").textContent = "En vivo";
    poblarInputsWhatIf(preset);
    programarEvaluacionWhatIf(0);
  });
});

function leerRegistroWhatIf() {
  const enteros = new Set(
    configContrato
      ? configContrato.campos_enteros
      : ["materias_perdidas", "semestre", "saldo_pendiente_cop", "estrato",
         "tiempo_desplazamiento_min", "personas_a_cargo", "apoyo_familiar"]
  );
  const numericos = [
    "promedio", "materias_perdidas", "asistencia_pct", "semestre",
    "saldo_pendiente_cop", "ingreso_hogar_smmlv", "estrato",
    "horas_trabajo_semana", "tiempo_desplazamiento_min",
    "personas_a_cargo", "apoyo_familiar"
  ];
  const r = {};
  numericos.forEach((campo) => {
    const el = $("#wi-" + campo);
    if (!el || el.value.trim() === "") {
      r[campo] = null;
      return;
    }
    const v = Number(el.value);
    if (!Number.isFinite(v)) {
      r[campo] = el.value;
      return;
    }
    r[campo] = enteros.has(campo) && Number.isInteger(v) ? Math.trunc(v) : v;
  });

  ["tiene_apoyo_financiero", "trabaja_en_area_de_estudio", "primera_generacion_universitaria"].forEach((c) => {
    const el = $("#wi-" + c);
    r[c] = el ? el.value === "true" : false;
  });
  return r;
}

function programarEvaluacionWhatIf(esperaMs = 90) {
  clearTimeout(timerWhatIf);
  timerWhatIf = setTimeout(() => ejecutarEvaluacionWhatIf(), esperaMs);
}

async function ejecutarEvaluacionWhatIf() {
  const panel = $("#resultado-whatif");
  if (!panel) return;

  const cuerpo = {
    datos: leerRegistroWhatIf(),
    k_montecarlo: 250
  };
  if (simulacionActual) {
    cuerpo.simulacion_id = simulacionActual.id;
  }
  if (baseWhatIf) {
    cuerpo.datos_base = baseWhatIf.datos;
  }

  try {
    const ev = await pedir("/api/evaluar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo)
    });
    pintarResultadoWhatIf(ev);
  } catch (err) {
    panel.innerHTML = `<div class="aviso-revision">${escapar(err.message)}</div>`;
  }
}

function pintarResultadoWhatIf(ev) {
  const panel = $("#resultado-whatif");
  if (!ev.valido) {
    panel.innerHTML = `
      <div class="ficha-cabecera">
        <div>
          <h3 style="margin:0">Veredicto Paso 1: Rechazado</h3>
          <p class="nota-tarjeta">El registro incumple el contrato de entrada.</p>
        </div>
        <span class="insignia revision">Revisión humana</span>
      </div>
      <div class="aviso-revision">
        <strong>No se calcula probabilidad.</strong><br>
        Motivo: <code>${escapar(ev.motivo_revision)}</code> en el campo <code>${escapar(ev.campo_revision)}</code>.<br>
        ${ev.mensaje_revision ? `Detalle del motor: <em>${escapar(ev.mensaje_revision)}</em>.` : ""}
      </div>`;
    return;
  }

  const r = ev.resultado;
  const p = ev.parametros;
  const colNivel = COLOR_NIVEL[r.nivel];
  const baseRes = ev.comparacion_base && ev.comparacion_base.resultado;

  let htmlComparador = "";
  if (baseRes && baseWhatIf) {
    const deltaPP = 100 * (r.p - baseRes.p);
    const mejora = deltaPP <= 0;
    htmlComparador = `
      <div class="comparador-antes-despues">
        <div>
          <div class="texto-suave" style="font-size:11px">ANTES (${escapar(baseWhatIf.codigo)})</div>
          <strong style="font-size:20px;color:${COLOR_NIVEL[baseRes.nivel]}">${pct(baseRes.p, 1)}</strong>
          <div><span class="insignia ${escapar(baseRes.nivel)}">${escapar(baseRes.nivel)}</span></div>
        </div>
        <div>
          <div class="delta-pill ${mejora ? "mejora" : "empeora"}">
            ${deltaPP > 0 ? "+" : ""}${deltaPP.toFixed(1)} pp
          </div>
          <div class="texto-suave" style="font-size:11px;margin-top:3px">efecto neto</div>
        </div>
        <div>
          <div class="texto-suave" style="font-size:11px">SIMULADO AHORA</div>
          <strong style="font-size:20px;color:${colNivel}">${pct(r.p, 1)}</strong>
          <div><span class="insignia ${escapar(r.nivel)}">${escapar(r.nivel)}</span></div>
        </div>
      </div>`;
  }

  const barras = DIMENSIONES.map((dim) => {
    const s = r.subpuntajes[dim];
    const crit = r.problemas.includes(dim);
    return `
      <div class="barra-dim ${crit ? "problema" : ""}">
        <div class="fila-barra">
          <span>${NOMBRE_DIM[dim]}${crit ? " ⚠" : ""}</span>
          <span>s = ${num(s, 3)} · b·s = +${num(r.contribuciones[dim], 2)}</span>
        </div>
        <div class="pista">
          <div class="relleno" style="width:${(s * 100).toFixed(1)}%;background:${COLOR_DIM[dim]}"></div>
        </div>
      </div>`;
  }).join("");

  const intervenciones = r.requiere_intervencion
    ? r.intervenciones.map((i) => `
        <div class="intervencion-card">
          <span class="prioridad-badge">Prioridad ${i.prioridad}</span>
          <strong>${escapar(i.nombre)}</strong>
          <div class="texto-suave" style="font-size:11.5px">Dimensión ${escapar(NOMBRE_DIM[i.dimension])} · <code>${escapar(i.tipo)}</code></div>
          <ul>${i.acciones.map((a) => `<li>${escapar(a)}</li>`).join("")}</ul>
        </div>`).join("")
    : `<p class="texto-suave">No requiere intervención: nivel <strong>${escapar(r.nivel)}</strong>.</p>`;

  panel.innerHTML = `
    ${htmlComparador}
    <div class="ficha-cabecera">
      <div>
        <h3 style="margin:0 0 4px">Paso 1 ✔ → Paso 2 → Paso 3</h3>
        <p class="nota-tarjeta">
          Intervalo P5–P95: <strong>${pct(r.p5, 1)} – ${pct(r.p95, 1)}</strong> ·
          logit z = <code>${num(r.logit, 2)}</code> (b₀ = ${num(p.b0_calibrado, 3)})
        </p>
      </div>
      <div style="text-align:right">
        <div class="ficha-prob-grande" style="color:${colNivel}">${pct(r.p, 1)}</div>
        <span class="insignia ${escapar(r.nivel)}" style="margin-top:4px">Riesgo ${escapar(r.nivel)}</span>
      </div>
    </div>

    <div class="rejilla-visual-inspector">
      <div class="caja-mini-svg">
        <h4>Radar 4D ${baseRes ? "(gris = base)" : ""}</h4>
        ${svgRadar4D(r.subpuntajes, baseRes ? baseRes.subpuntajes : null)}
      </div>
      <div class="caja-mini-svg">
        <h4>Cascada del Logit</h4>
        ${svgWaterfallLogit(p.b0_calibrado, r.contribuciones, r.p)}
      </div>
    </div>

    <div class="bloque-seccion-ficha">
      <h4>Subpuntajes por dimensión</h4>
      ${barras}
    </div>

    <div class="bloque-seccion-ficha">
      <h4>Paso 3 · Plan de acompañamiento</h4>
      ${intervenciones}
    </div>`;
}

/* ========================================== 6. VALIDACIÓN DEL MODELO === */
function svgCurvaROC(puntos, auc) {
  if (!puntos || puntos.length < 2) return "";
  const tam = 250, m = 34;
  const u = tam - m * 2;
  const x = (fpr) => m + fpr * u;
  const y = (tpr) => m + u - tpr * u;

  const poly = puntos.map(([fpr, tpr]) => `${x(fpr).toFixed(1)},${y(tpr).toFixed(1)}`).join(" ");
  const area = `${x(0)},${y(0)} ${poly} ${x(1)},${y(0)}`;

  return `
    <svg viewBox="0 0 ${tam} ${tam}" role="img" aria-label="Curva ROC empírica">
      <rect x="${m}" y="${m}" width="${u}" height="${u}" fill="none" stroke="var(--svg-rejilla)" stroke-width="1"/>
      <polygon points="${area}" fill="${COLOR_NIVEL.bajo}" fill-opacity="0.14"/>
      <line x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}" stroke="var(--svg-eje)" stroke-width="1.2" stroke-dasharray="4 3"/>
      <polyline points="${poly}" fill="none" stroke="${COLOR_NIVEL.bajo}" stroke-width="2.5"/>
      <text x="${m + u * 0.58}" y="${m + u * 0.72}" font-size="11.5" font-weight="800" fill="${COLOR_NIVEL.bajo}">AUC = ${num(auc, 4)}</text>
      <text x="${m + u / 2}" y="${tam - 7}" font-size="10.5" fill="var(--svg-texto)" text-anchor="middle">1 − Especificidad (FPR)</text>
      <text x="11" y="${m + u / 2}" font-size="10.5" fill="var(--svg-texto)" text-anchor="middle" transform="rotate(-90 11 ${m + u / 2})">Sensibilidad (TPR)</text>
    </svg>`;
}

function svgTornadoSensibilidad(sens) {
  const filas = sens.filas || [];
  if (!filas.length) return "";
  const ancho = 520, alto = 195;
  const m = { arriba: 18, derecha: 78, abajo: 30, izquierda: 92 };
  const anchoU = ancho - m.izquierda - m.derecha;
  const altoU = alto - m.arriba - m.abajo;

  const base = sens.indice_base;
  const vals = filas.flatMap((f) => [f.indice_bajo, f.indice_alto, base]);
  const minV = Math.max(0, Math.min(...vals) * 0.88);
  const maxV = Math.min(1, Math.max(...vals) * 1.10);
  const x = (v) => m.izquierda + ((v - minV) / Math.max(1e-6, maxV - minV)) * anchoU;
  const xBase = x(base);
  const paso = altoU / filas.length;
  const bh = Math.min(24, paso - 10);

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Diagrama de tornado de sensibilidad">`;
  filas.forEach((f, i) => {
    const py = m.arriba + i * paso + (paso - bh) / 2;
    const xIzq = x(f.indice_bajo);
    const xDer = x(f.indice_alto);

    svg += `<text x="${m.izquierda - 8}" y="${py + bh / 2 + 4}" font-size="11.5" font-weight="700" fill="var(--svg-titulo)" text-anchor="end">${NOMBRE_DIM[f.dimension]}</text>`;
    svg += `<rect x="${xIzq}" y="${py}" width="${Math.max(2, xBase - xIzq)}" height="${bh}" fill="#64748b" opacity="0.65" rx="3">
      <title>−50% en b_${f.dimension}: índice ${pct(f.indice_bajo, 2)}</title></rect>`;
    svg += `<rect x="${xBase}" y="${py}" width="${Math.max(2, xDer - xBase)}" height="${bh}" fill="${COLOR_DIM[f.dimension]}" opacity="0.9" rx="3">
      <title>+50% en b_${f.dimension}: índice ${pct(f.indice_alto, 2)}</title></rect>`;
    svg += `<text x="${xDer + 6}" y="${py + bh / 2 + 4}" font-size="11" font-weight="700" fill="var(--svg-titulo)">${num(f.amplitud_pp, 2)} pp</text>`;
  });

  svg += `<line x1="${xBase}" y1="${m.arriba - 4}" x2="${xBase}" y2="${m.arriba + altoU}" stroke="var(--svg-titulo)" stroke-width="1.5"/>`;
  svg += `<text x="${xBase}" y="${alto - 6}" font-size="10.5" font-weight="700" fill="var(--svg-titulo)" text-anchor="middle">Base ${pct(base, 2)}</text>`;
  svg += `</svg>`;
  return svg;
}

function svgSparklineMonotonia(pasos) {
  if (!pasos || pasos.length < 2) return "";
  const w = 96, h = 24, pad = 3;
  const ps = pasos.map((x) => x.p);
  const minP = Math.min(...ps);
  const maxP = Math.max(...ps);
  const pts = ps.map((p, i) => {
    const px = pad + (i / (ps.length - 1)) * (w - pad * 2);
    const py = h - pad - ((p - minP) / Math.max(1e-6, maxP - minP)) * (h - pad * 2);
    return `${px.toFixed(1)},${py.toFixed(1)}`;
  }).join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">
    <polyline points="${pts}" fill="none" stroke="${COLOR_NIVEL.bajo}" stroke-width="2"/>
  </svg>`;
}

function resumenPerfilCara(datos) {
  if (!datos) return '<span class="texto-no">—</span>';
  const partes = [];
  if (datos.nivel) partes.push(`<span class="insignia ${escapar(datos.nivel)}">${escapar(datos.nivel)}</span>`);
  if (datos.requiere_intervencion !== undefined) {
    partes.push(datos.requiere_intervencion ? '<strong>con apoyo</strong>' : '<span class="texto-no">sin apoyo</span>');
  }
  if (datos.problemas && datos.problemas.length) {
    partes.push(datos.problemas.map((d) => `<span class="etiqueta-dim dim-${escapar(d)}">${escapar(NOMBRE_DIM[d])}</span>`).join(""));
  }
  if (datos.intervencion_principal) {
    partes.push(`<code>${escapar(datos.intervencion_principal)}</code>`);
  }
  return partes.join(" · ");
}

function pintarValidacion(sim) {
  const v = sim.validacion_modelo;
  const p = sim.parametros;
  const real = sim.resumen && sim.resumen.evaluacion_real;
  const badge = (ok) => `<span class="veredicto ${ok ? "pasa" : "falla"}">${ok ? "Pasa" : "Falla"}</span>`;

  const cal = v.calibracion;
  const sens = v.sensibilidad;
  const cara = v.validez_de_cara;
  const mono = v.monotonia;

  const bloqueEmpiricoUCI = real ? `
    <article class="tarjeta" style="border-left:4px solid var(--bajo)">
      <div class="cabecera-tarjeta">
        <div>
          <h3>Validación empírica contra desenlace real · Dataset UCI ${badge(real.auc_roc >= 0.75)}</h3>
          <p class="nota-tarjeta">
            Comparación directa de las probabilidades calculadas (sin reentrenar coeficientes expertos) contra <code>Target = Dropout / Graduate</code> en <strong>${escapar(real.fuente)}</strong>.
          </p>
        </div>
      </div>
      <div class="rejilla-dos-columnas" style="align-items:center;margin-top:8px">
        <div style="max-width:270px;margin:0 auto">
          ${svgCurvaROC(real.curva_roc, real.auc_roc)}
        </div>
        <div>
          <div class="matriz-confusion-grid">
            <div class="celda-mc acierto">
              <strong>${real.matriz_confusion.vp}</strong>
              <span>Verdaderos Positivos (Desertó + Recibe apoyo)</span>
            </div>
            <div class="celda-mc error-mc">
              <strong>${real.matriz_confusion.fp}</strong>
              <span>Falsos Positivos (Graduado + Recibe apoyo)</span>
            </div>
            <div class="celda-mc error-mc">
              <strong>${real.matriz_confusion.fn}</strong>
              <span>Falsos Negativos (Desertó sin alerta)</span>
            </div>
            <div class="celda-mc acierto">
              <strong>${real.matriz_confusion.vn}</strong>
              <span>Verdaderos Negativos (Graduado sin alerta)</span>
            </div>
          </div>
          <ul class="lista-vars" style="margin-top:12px;font-size:12.5px">
            <li><span>Probabilidad media asignada a desertores reales</span><strong>${pct(real.p_media_desertores, 2)}</strong></li>
            <li><span>Probabilidad media asignada a graduados reales</span><strong>${pct(real.p_media_graduados, 2)}</strong></li>
            <li><span>Sensibilidad / Especificidad operativa</span><strong>${pct(real.matriz_confusion.sensibilidad, 1)} / ${pct(real.matriz_confusion.especificidad, 1)}</strong></li>
            <li><span>Tutorías académicas activadas (sA ≥ 0,60)</span><strong>${sim.resumen.problemas_por_dimension.academica} estudiantes</strong></li>
          </ul>
        </div>
      </div>
    </article>` : "";

  $("#validacion").innerHTML = `
    ${bloqueEmpiricoUCI}

    <div class="rejilla-validacion-sup">
      <article class="tarjeta">
        <div class="cabecera-tarjeta">
          <h3>1. Calibración exacta por bisección ${badge(cal.ok)}</h3>
        </div>
        <p class="nota-tarjeta">
          <code>b₀</code> se despeja numéricamente para que la probabilidad media de la cohorte iguale la tasa base semestral.
        </p>
        <ul class="lista-vars" style="margin-top:10px;font-size:13px">
          <li><span>Tasa base semestral (objetivo)</span><strong>${num(cal.tasa_base, 5)} (${pct(cal.tasa_base, 2)})</strong></li>
          <li><span>Probabilidad media obtenida</span><strong>${num(cal.media_obtenida, 5)}</strong></li>
          <li><span>Error absoluto de calibración</span><strong>${Math.abs(cal.diferencia).toExponential(2)} (máx ±${cal.margen})</strong></li>
          <li><span>Intercepto b₀ calibrado</span><strong>${num(cal.b0_calibrado, 6)}</strong></li>
        </ul>
        <pre class="formula">p = 1 / (1 + exp(-(${num(cal.b0_calibrado, 4)} + ${num(p.coeficientes.academica, 1)}·sA + ${num(p.coeficientes.financiera, 1)}·sF + ${num(p.coeficientes.laboral, 1)}·sL + ${num(p.coeficientes.personal, 1)}·sP)))</pre>
      </article>

      <article class="tarjeta">
        <div class="cabecera-tarjeta">
          <h3>2. Sensibilidad a los coeficientes (±${pct(sens.variacion, 0)})</h3>
        </div>
        <p class="nota-tarjeta">
          Diagrama de Tornado dejando <code>b₀</code> fijo. El supuesto más influyente sobre la cohorte es <strong>${escapar(NOMBRE_DIM[sens.mas_influyente])}</strong>.
        </p>
        <div class="lienzo-svg" style="margin-top:8px">
          ${svgTornadoSensibilidad(sens)}
        </div>
      </article>
    </div>

    <article class="tarjeta">
      <div class="cabecera-tarjeta">
        <div>
          <h3>3. Validez de cara sobre perfiles testigo ${badge(cara.ok)}</h3>
          <p class="nota-tarjeta">Tres arquetipos definidos de antemano cuyo diagnóstico debe coincidir con el criterio experto.</p>
        </div>
      </div>
      <div class="envoltorio-tabla">
        <table class="tabla-datos">
          <thead>
            <tr>
              <th>Perfil testigo</th>
              <th>sA / sF / sL / sP</th>
              <th>p estimada</th>
              <th>Esperado</th>
              <th>Obtenido</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            ${cara.perfiles.map((pf) => `
              <tr>
                <td>
                  <strong>${escapar(pf.nombre)}</strong>
                  <div class="texto-suave" style="font-size:11.5px">${escapar(pf.descripcion)}</div>
                </td>
                <td><code>${DIMENSIONES.map((d) => num(pf.subpuntajes[d], 2)).join(" / ")}</code></td>
                <td><strong>${pct(pf.p, 2)}</strong></td>
                <td>${resumenPerfilCara(pf.esperado)}</td>
                <td>${resumenPerfilCara(pf.obtenido)}</td>
                <td>${badge(pf.coincide)}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </article>

    <article class="tarjeta">
      <div class="cabecera-tarjeta">
        <div>
          <h3>4. Prueba de monotonía en ${mono.n_variables} variables ${badge(mono.ok)}</h3>
          <p class="nota-tarjeta">Empeorar cualquier factor de riesgo de su mejor a su peor valor nunca disminuye <code>p</code>.</p>
        </div>
      </div>
      <div class="envoltorio-tabla">
        <table class="tabla-datos">
          <thead>
            <tr>
              <th>Variable del contrato</th>
              <th>p (mejor valor)</th>
              <th>Curva mejor → peor</th>
              <th>p (peor valor)</th>
              <th>Veredicto</th>
            </tr>
          </thead>
          <tbody>
            ${mono.variables.map((f) => `
              <tr>
                <td><code>${escapar(f.variable)}</code></td>
                <td>${pct(f.p_mejor, 2)}</td>
                <td>${svgSparklineMonotonia(f.pasos)}</td>
                <td><strong>${pct(f.p_peor, 2)}</strong></td>
                <td>${badge(f.ok)}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </article>`;
}

/* =================================================== 7. HISTORIAL DB === */
async function cargarHistorial() {
  try {
    const datos = await pedir("/api/simulaciones?limite=50");
    const filas = datos.simulaciones || [];
    $("#badge-tab-historial").textContent = String(filas.length);

    if (!filas.length) {
      $("#cuerpo-historial").innerHTML =
        '<tr><td colspan="11" class="vacio">Todavía no hay simulaciones guardadas.</td></tr>';
      return;
    }

    $("#cuerpo-historial").innerHTML = filas.map((s) => {
      const esUci = s.origen === "uci";
      const esSpadies = !esUci && Math.abs(s.tasa_base - 0.0442) < 0.001;
      const badgeOrigen = esUci
        ? '<span class="insignia-fuente real">Dataset Real UCI</span>'
        : esSpadies
          ? '<span class="insignia-fuente spadies">Simulada · SPADIES</span>'
          : '<span class="insignia-fuente sintetica">Simulada · Montecarlo</span>';
      const activa = simulacionActual && simulacionActual.id === s.id ? "seleccionada" : "";

      return `<tr data-sim-id="${s.id}" class="${activa}">
        <td><strong>#${s.id}</strong></td>
        <td>${badgeOrigen}</td>
        <td>${escapar(String(s.fecha || "").replace("T", " "))}</td>
        <td>${s.n}</td>
        <td>${esUci && s.n >= 3630 ? "—" : s.semilla}</td>
        <td>${pct(s.tasa_base, 2)}</td>
        <td><code>${num(s.b0_calibrado, 3)}</code></td>
        <td><strong>${pct(s.indice_general, 2)}</strong></td>
        <td>${num(s.pct_alto, 1)}%</td>
        <td>${num(s.pct_intervencion, 1)}%</td>
        <td>${s.n_revision_humana}</td>
      </tr>`;
    }).join("");
  } catch (err) {
    informarEstado(err.message, "error");
  }
}

$("#cuerpo-historial").addEventListener("click", async (ev) => {
  const fila = ev.target.closest("tr[data-sim-id]");
  if (!fila) return;
  const id = Number(fila.dataset.simId);
  try {
    informarEstado("Cargando simulación #" + id + "…", "cargando");
    const sim = await pedir("/api/simulaciones/" + id);
    cerrarInspector();
    await activarSimulacion(sim);
    await cargarHistorial();
    activarPestana("panel-resultados");
    informarEstado("Mostrando simulación #" + id, "listo");
  } catch (err) {
    informarEstado(err.message, "error");
  }
});

/* ========================================================= ARRANQUE ==== */
(async function iniciarApp() {
  inicializarTema();
  try {
    configContrato = await pedir("/api/config");
  } catch (_e) {
    configContrato = null;
  }

  await cargarHistorial();
  try {
    const rec = await pedir("/api/simulaciones?limite=1");
    if (rec.simulaciones && rec.simulaciones.length) {
      const sim = await pedir("/api/simulaciones/" + rec.simulaciones[0].id);
      await activarSimulacion(sim);
      await cargarHistorial();
      informarEstado("Simulación #" + sim.id + " lista", "listo");
    } else {
      informarEstado("Pulsa un escenario para iniciar.");
      programarEvaluacionWhatIf(0);
    }
  } catch (err) {
    informarEstado(err.message, "error");
  }
})();
