/* Simulador de desercion - interfaz.
 *
 * JavaScript propio, sin frameworks ni librerias externas: las graficas se
 * construyen como SVG en linea, asi que la pagina funciona sin internet.
 *
 * Flujo:
 *   POST /api/simulaciones  -> corre y guarda una simulacion
 *   GET  /api/simulaciones/<id>/estudiantes?... -> tabla con filtros
 *   GET  /api/estudiantes/<id> -> panel de detalle
 *   GET  /api/simulaciones -> historial
 */
"use strict";

const DIMENSIONES = ["academica", "financiera", "laboral", "personal"];
const NOMBRE_DIM = {
  academica: "Académica",
  financiera: "Financiera",
  laboral: "Laboral",
  personal: "Personal"
};
const COLOR_DIM = {
  academica: "#1f6feb",
  financiera: "#d97706",
  laboral: "#7c3aed",
  personal: "#0f9b8e"
};
const COLOR_NIVEL = { bajo: "#2e7d58", medio: "#b8860b", alto: "#b3332c" };

// Etiquetas legibles de los campos de la entrada E, por dimension.
const CAMPOS_DIM = {
  academica: [
    ["promedio", "Promedio"],
    ["materias_perdidas", "Materias perdidas"],
    ["asistencia_pct", "Asistencia (%)"],
    ["semestre", "Semestre"]
  ],
  financiera: [
    ["saldo_pendiente_cop", "Saldo pendiente (COP)"],
    ["ingreso_hogar_smmlv", "Ingreso hogar (SMMLV)"],
    ["estrato", "Estrato"],
    ["tiene_apoyo_financiero", "Tiene apoyo financiero"]
  ],
  laboral: [
    ["horas_trabajo_semana", "Horas de trabajo / semana"],
    ["trabaja_en_area_de_estudio", "Trabaja en su área"]
  ],
  personal: [
    ["tiempo_desplazamiento_min", "Desplazamiento (min)"],
    ["personas_a_cargo", "Personas a cargo"],
    ["apoyo_familiar", "Apoyo familiar (1–5)"],
    ["primera_generacion_universitaria", "Primera generación"]
  ]
};

// Estado de la pagina: la simulacion que se esta mirando.
let simulacionActual = null;
let estudianteSeleccionado = null;
let estudiantesCargados = [];

/* ------------------------------------------------------------ utiles -- */
const $ = (sel) => document.querySelector(sel);

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto == null ? "" : String(texto);
  return div.innerHTML;
}

const pct = (x, dec = 1) => (100 * x).toFixed(dec) + "%";
const num = (x, dec = 3) => Number(x).toFixed(dec);

function cop(valor) {
  return "$ " + Math.round(valor).toLocaleString("es-CO");
}

function valorLegible(campo, valor) {
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (valor === null || valor === undefined) return "(vacío)";
  if (campo === "saldo_pendiente_cop") return cop(valor);
  return String(valor);
}

async function pedir(url, opciones) {
  const respuesta = await fetch(url, opciones);
  let cuerpo = null;
  try {
    cuerpo = await respuesta.json();
  } catch (e) {
    throw new Error("El servidor respondió algo que no es JSON (HTTP " +
                    respuesta.status + ")");
  }
  if (!respuesta.ok) {
    throw new Error(cuerpo && cuerpo.error ? cuerpo.error :
                    "Error HTTP " + respuesta.status);
  }
  return cuerpo;
}

function estado(mensaje, clase) {
  const el = $("#estado");
  el.textContent = mensaje;
  el.className = "estado" + (clase ? " " + clase : "");
}

/* ======================================================== 1. SIMULAR == */
const MODOS_SIMULACION = {
  referencia: { origen: "sintetica", n: 500, semilla: 42, tasa_base: 0.09, k_montecarlo: 1000 },
  spadies:    { origen: "sintetica", n: 500, semilla: 42, tasa_base: 0.0442, k_montecarlo: 1000 },
  uci_500:    { origen: "uci", n: 500, semilla: 42, tasa_base: 0.0442, k_montecarlo: 300 },
  uci_full:   { origen: "uci", n: 3630, semilla: 42, tasa_base: 0.3915, k_montecarlo: 200 }
};

function sincronizarVistaFuente(origen, n, tasa) {
  const esReal = origen === "uci";
  const fichaReal = $("#ficha-dataset-real");
  const acordeon = $("#acordeon-parametros");
  const summary = $("#summary-parametros");
  const campoSemilla = $("#campo-semilla");
  const ayudaN = $("#ayuda-n");

  if (fichaReal) fichaReal.hidden = !esReal;
  if (campoSemilla) campoSemilla.style.display = esReal ? "none" : "";
  if (ayudaN) {
    ayudaN.textContent = esReal
      ? "Filas a leer del CSV real (máx. 3.630 cerrados)"
      : "Tamaño de la cohorte sintética a generar";
  }
  if (esReal) {
    if (acordeon) acordeon.open = false;
    if (summary) summary.textContent = "Opciones avanzadas de evaluación del dataset (umbrales y K)";
    if ($("#ficha-real-n")) {
      $("#ficha-real-n").textContent = n >= 3630
        ? "3.630 estudiantes reales con desenlace cerrado (1.421 Dropout · 2.209 Graduate)"
        : n + " primeros registros reales del archivo CSV de UCI";
    }
    if ($("#ficha-real-tasa")) {
      $("#ficha-real-tasa").textContent = Math.abs(tasa - 0.3915) < 0.005
        ? "39,15% (tasa real observada en el dataset UCI)"
        : Math.abs(tasa - 0.0442) < 0.002
          ? "4,42% (tasa oficial semestral SPADIES 3.0 Colombia)"
          : pct(tasa, 2);
    }
  } else {
    if (acordeon) acordeon.open = true;
    if (summary) summary.textContent = "Parámetros de generación de la cohorte sintética (personalizar)";
  }

  // Marcar cuál de las 4 tarjetas superiores coincide
  document.querySelectorAll("[data-modo-sim]").forEach((btn) => {
    const cfg = MODOS_SIMULACION[btn.dataset.modoSim];
    const coincide = cfg &&
      cfg.origen === (origen || "sintetica") &&
      Number(n) === cfg.n &&
      Math.abs(Number(tasa) - cfg.tasa_base) < 0.001;
    btn.classList.toggle("activa", Boolean(coincide));
  });
}

if ($("#origen")) {
  $("#origen").addEventListener("change", () => {
    sincronizarVistaFuente(
      $("#origen").value,
      Number($("#n").value),
      Number($("#tasa_base").value)
    );
  });
}

if ($("#btn-ejecutar-real")) {
  $("#btn-ejecutar-real").addEventListener("click", () => {
    $("#form-simular").requestSubmit();
  });
}

document.querySelectorAll("[data-modo-sim]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const cfg = MODOS_SIMULACION[btn.dataset.modoSim];
    if (!cfg) return;
    if ($("#origen")) $("#origen").value = cfg.origen;
    $("#n").value = cfg.n;
    $("#semilla").value = cfg.semilla;
    $("#tasa_base").value = cfg.tasa_base;
    $("#k_montecarlo").value = cfg.k_montecarlo;
    sincronizarVistaFuente(cfg.origen, cfg.n, cfg.tasa_base);
    $("#form-simular").requestSubmit();
  });
});

$("#form-simular").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const boton = $("#btn-simular");
  boton.disabled = true;
  estado("Simulando…");

  const cuerpo = {
    n: Number($("#n").value),
    semilla: Number($("#semilla").value),
    tasa_base: Number($("#tasa_base").value),
    umbral_medio: Number($("#umbral_medio").value),
    umbral_alto: Number($("#umbral_alto").value),
    k_montecarlo: Number($("#k_montecarlo").value)
  };
  if ($("#origen") && $("#origen").value === "uci") {
    cuerpo.origen = "uci";
  }

  try {
    const simulacion = await pedir("/api/simulaciones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo)
    });
    simulacionActual = simulacion;
    pintarSimulacion(simulacion);
    await cargarEstudiantes();
    await cargarHistorial();
    estado("Simulación #" + simulacion.id + " guardada.", "listo");
  } catch (error) {
    estado(error.message, "error");
  } finally {
    boton.disabled = false;
  }
});

/* ======================================================= 2. PESTAÑAS == */
document.querySelectorAll(".pestana").forEach((pestana) => {
  pestana.addEventListener("click", () => {
    document.querySelectorAll(".pestana").forEach((p) => {
      p.classList.remove("activa");
      p.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("activo"));
    pestana.classList.add("activa");
    pestana.setAttribute("aria-selected", "true");
    $("#" + pestana.dataset.panel).classList.add("activo");
  });
});

/* ==================================================== 3. INDICADORES == */
function pintarBannerContexto(sim) {
  const banner = $("#banner-contexto");
  if (!banner) return;
  const p = sim.parametros;
  const r = sim.resumen;
  const esReal = p.origen === "uci";
  const esSpadies = !esReal && Math.abs(p.tasa_base - 0.0442) < 0.001;

  banner.className = "banner-contexto" +
    (esReal ? " es-real" : esSpadies ? " es-spadies" : "");

  if (esReal) {
    const aucTxt = r.evaluacion_real
      ? ` · <strong>AUC–ROC real = ${num(r.evaluacion_real.auc_roc, 4)}</strong>`
      : "";
    banner.innerHTML = `
      <div>
        <span class="insignia-fuente real">Viendo Dataset Real · Corrida #${sim.id}</span>
        <div class="titulo-banner">Dataset: UCI — Predict Students' Dropout and Academic Success (Realinho et al., 2022)</div>
        <div class="sub-banner">
          Archivo: <code>data.csv</code> · <strong>${r.n_validos} estudiantes reales</strong> evaluados
          (códigos <code>UCI-0001</code> a <code>UCI-${String(r.n_total).padStart(4, "0")}</code>) ·
          Tasa de calibración: <strong>${pct(p.tasa_base, 2)}</strong>${aucTxt} ·
          Tutorías académicas activadas: <strong>${r.problemas_por_dimension.academica}</strong>
        </div>
      </div>`;
  } else if (esSpadies) {
    banner.innerHTML = `
      <div>
        <span class="insignia-fuente spadies">Viendo Datos Simulados · Calibración Oficial MEN · Corrida #${sim.id}</span>
        <div class="titulo-banner">Cohorte Sintética Calibrada con SPADIES 3.0 (MEN Colombia, 2024)</div>
        <div class="sub-banner">
          <strong>${r.n_total} estudiantes simulados</strong> (semilla ${p.semilla}, códigos <code>UNA-0001</code>…) ·
          Calibrada a la Tasa de Deserción Anual universitaria oficial (8,65% anual → <strong>4,42% semestral</strong>)
        </div>
      </div>`;
  } else {
    banner.innerHTML = `
      <div>
        <span class="insignia-fuente sintetica">Viendo Datos Simulados · Referencia · Corrida #${sim.id}</span>
        <div class="titulo-banner">Cohorte Sintética Generada por Montecarlo (Universidad Católica de Colombia)</div>
        <div class="sub-banner">
          <strong>${r.n_total} estudiantes simulados</strong> (semilla ${p.semilla}, códigos <code>UNA-0001</code>…) ·
          Tasa base semestral: <strong>${pct(p.tasa_base, 2)}</strong> ·
          <strong>${r.n_validos} válidos</strong> y <strong>${r.n_revision_humana} con errores inyectados</strong> para probar el Paso 1
        </div>
      </div>`;
  }
}

function pintarSimulacion(sim) {
  const r = sim.resumen;
  const p = sim.parametros;

  sincronizarVistaFuente(p.origen || "sintetica", p.n, p.tasa_base);
  pintarBannerContexto(sim);

  $("#indicadores").innerHTML = `
    <div class="indicador">
      <span class="etiqueta">Índice de riesgo general</span>
      <span class="valor">${pct(r.indice_general, 2)}</span>
      <span class="detalle-ind">Probabilidad media de la cohorte ·
        tasa base ${pct(p.tasa_base, 1)} · b₀ = ${num(p.b0_calibrado, 4)}</span>
    </div>
    <div class="indicador bajo">
      <span class="etiqueta">Riesgo bajo</span>
      <span class="valor">${pct(r.pct_bajo / 100, 1)}</span>
      <span class="detalle-ind">${r.conteo_nivel.bajo} estudiantes · p &lt; ${num(p.umbral_medio, 2)}</span>
    </div>
    <div class="indicador medio">
      <span class="etiqueta">Riesgo medio</span>
      <span class="valor">${pct(r.pct_medio / 100, 1)}</span>
      <span class="detalle-ind">${r.conteo_nivel.medio} estudiantes · ${num(p.umbral_medio, 2)} ≤ p &lt; ${num(p.umbral_alto, 2)}</span>
    </div>
    <div class="indicador alto">
      <span class="etiqueta">Riesgo alto</span>
      <span class="valor">${pct(r.pct_alto / 100, 1)}</span>
      <span class="detalle-ind">${r.conteo_nivel.alto} estudiantes · p ≥ ${num(p.umbral_alto, 2)}</span>
    </div>
    <div class="indicador">
      <span class="etiqueta">Requieren intervención</span>
      <span class="valor">${pct(r.pct_intervencion / 100, 1)}</span>
      <span class="detalle-ind">${r.n_intervencion} de ${r.n_validos} estudiantes válidos</span>
    </div>
    <div class="indicador revision">
      <span class="etiqueta">Revisión humana</span>
      <span class="valor">${r.n_revision_humana}</span>
      <span class="detalle-ind">No reciben probabilidad: el Paso 1 los rechazó</span>
    </div>`;

  dibujarHistograma(r.probabilidades || [], p);
  dibujarContribucion(r.contribucion_promedio, r.subpuntaje_promedio, p);
  pintarValidacion(sim);
  evaluarWhatIf();
}

/* ================================================= 4. GRÁFICA: HISTO == */
function dibujarHistograma(probabilidades, params) {
  const destino = $("#grafica-histograma");
  if (!probabilidades.length) {
    destino.innerHTML = '<p class="vacio">Sin datos.</p>';
    return;
  }

  const ancho = 560, alto = 280;
  const margen = { arriba: 16, derecha: 14, abajo: 48, izquierda: 48 };
  const anchoUtil = ancho - margen.izquierda - margen.derecha;
  const altoUtil = alto - margen.arriba - margen.abajo;

  const maxP = Math.max(...probabilidades);
  const limite = Math.min(1, Math.max(0.4, Math.ceil(maxP * 11) / 10));
  const nBins = 22;
  const anchoBin = limite / nBins;

  const bins = new Array(nBins).fill(0);
  probabilidades.forEach((p) => {
    let i = Math.floor(p / anchoBin);
    if (i >= nBins) i = nBins - 1;
    if (i < 0) i = 0;
    bins[i] += 1;
  });
  const maxBin = Math.max(...bins);

  const x = (valor) => margen.izquierda + (valor / limite) * anchoUtil;
  const y = (conteo) => margen.arriba + altoUtil - (conteo / maxBin) * altoUtil;

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img"
      aria-label="Histograma de probabilidades de deserción">`;

  // Rejilla horizontal y eje Y
  const pasosY = 4;
  for (let i = 0; i <= pasosY; i++) {
    const conteo = (maxBin / pasosY) * i;
    const py = y(conteo);
    svg += `<line x1="${margen.izquierda}" y1="${py}" x2="${ancho - margen.derecha}" y2="${py}"
             stroke="#e8edf4" stroke-width="1"/>`;
    svg += `<text x="${margen.izquierda - 8}" y="${py + 4}" font-size="11" fill="#5b6879"
             text-anchor="end">${Math.round(conteo)}</text>`;
  }

  // Barras, coloreadas por el nivel al que pertenece el centro del bin
  bins.forEach((conteo, i) => {
    if (!conteo) return;
    const centro = (i + 0.5) * anchoBin;
    const nivel = centro >= params.umbral_alto ? "alto"
                : centro >= params.umbral_medio ? "medio" : "bajo";
    const bx = x(i * anchoBin);
    const bw = Math.max(1, x((i + 1) * anchoBin) - bx - 1.5);
    const by = y(conteo);
    svg += `<rect x="${bx}" y="${by}" width="${bw}" height="${margen.arriba + altoUtil - by}"
             fill="${COLOR_NIVEL[nivel]}" opacity="0.85">
             <title>${conteo} estudiante(s) con p entre ${num(i * anchoBin, 3)} y ${num((i + 1) * anchoBin, 3)}</title>
            </rect>`;
  });

  // Líneas de umbral
  [["umbral_medio", params.umbral_medio, "medio"],
   ["umbral_alto", params.umbral_alto, "alto"]].forEach(([clave, valor, etq]) => {
    if (valor > limite) return;
    const px = x(valor);
    svg += `<line x1="${px}" y1="${margen.arriba}" x2="${px}" y2="${margen.arriba + altoUtil}"
             stroke="${COLOR_NIVEL[etq]}" stroke-width="1.5" stroke-dasharray="5 3"/>`;
    svg += `<text x="${px + 4}" y="${margen.arriba + 12}" font-size="10.5"
             fill="${COLOR_NIVEL[etq]}" font-weight="600">${etq} ${num(valor, 2)}</text>`;
  });

  // Eje X
  svg += `<line x1="${margen.izquierda}" y1="${margen.arriba + altoUtil}"
           x2="${ancho - margen.derecha}" y2="${margen.arriba + altoUtil}"
           stroke="#aab4c2" stroke-width="1"/>`;
  const pasosX = 5;
  for (let i = 0; i <= pasosX; i++) {
    const valor = (limite / pasosX) * i;
    const px = x(valor);
    svg += `<text x="${px}" y="${margen.arriba + altoUtil + 17}" font-size="11"
             fill="#5b6879" text-anchor="middle">${num(valor, 2)}</text>`;
  }
  svg += `<text x="${margen.izquierda + anchoUtil / 2}" y="${alto - 8}" font-size="11.5"
           fill="#1b2430" text-anchor="middle">Probabilidad de deserción semestral (p)</text>`;
  svg += `<text x="12" y="${margen.arriba + altoUtil / 2}" font-size="11.5" fill="#1b2430"
           text-anchor="middle" transform="rotate(-90 12 ${margen.arriba + altoUtil / 2})">Estudiantes</text>`;
  svg += "</svg>";

  destino.innerHTML = svg;
}

/* ========================================== 5. GRÁFICA: CONTRIBUCIÓN == */
function dibujarContribucion(contribuciones, subpuntajes, params) {
  const destino = $("#grafica-contribucion");
  if (!contribuciones) {
    destino.innerHTML = '<p class="vacio">Sin datos.</p>';
    return;
  }

  const ancho = 560, alto = 280;
  const margen = { arriba: 18, derecha: 120, abajo: 48, izquierda: 96 };
  const anchoUtil = ancho - margen.izquierda - margen.derecha;
  const altoUtil = alto - margen.arriba - margen.abajo;

  const orden = DIMENSIONES.slice().sort(
    (a, b) => contribuciones[b] - contribuciones[a]);
  const maxContrib = Math.max(...DIMENSIONES.map((d) => contribuciones[d]), 0.01);
  const altoBarra = Math.min(38, altoUtil / orden.length - 12);
  const paso = altoUtil / orden.length;

  let svg = `<svg viewBox="0 0 ${ancho} ${alto}" role="img"
      aria-label="Contribución promedio de cada dimensión al riesgo">`;

  // Rejilla vertical
  const pasosX = 4;
  for (let i = 0; i <= pasosX; i++) {
    const valor = (maxContrib / pasosX) * i;
    const px = margen.izquierda + (valor / maxContrib) * anchoUtil;
    svg += `<line x1="${px}" y1="${margen.arriba}" x2="${px}" y2="${margen.arriba + altoUtil}"
             stroke="#e8edf4" stroke-width="1"/>`;
    svg += `<text x="${px}" y="${margen.arriba + altoUtil + 17}" font-size="11"
             fill="#5b6879" text-anchor="middle">${num(valor, 2)}</text>`;
  }

  orden.forEach((dim, i) => {
    const valor = contribuciones[dim];
    const by = margen.arriba + i * paso + (paso - altoBarra) / 2;
    const bw = Math.max(1, (valor / maxContrib) * anchoUtil);

    svg += `<text x="${margen.izquierda - 10}" y="${by + altoBarra / 2 + 4}" font-size="12"
             fill="#1b2430" text-anchor="end" font-weight="600">${NOMBRE_DIM[dim]}</text>`;
    svg += `<rect x="${margen.izquierda}" y="${by}" width="${bw}" height="${altoBarra}"
             fill="${COLOR_DIM[dim]}" opacity="0.88" rx="3">
             <title>${NOMBRE_DIM[dim]}: contribución media ${num(valor, 4)} = b=${num(params.coeficientes[dim], 2)} × s̄=${num(subpuntajes[dim], 4)}</title>
            </rect>`;
    svg += `<text x="${margen.izquierda + bw + 8}" y="${by + altoBarra / 2 + 4}" font-size="11.5"
             fill="#1b2430">${num(valor, 3)}
             <tspan fill="#5b6879" font-size="10.5"> (b=${num(params.coeficientes[dim], 1)} · s̄=${num(subpuntajes[dim], 2)})</tspan></text>`;
  });

  svg += `<line x1="${margen.izquierda}" y1="${margen.arriba}" x2="${margen.izquierda}"
           y2="${margen.arriba + altoUtil}" stroke="#aab4c2" stroke-width="1"/>`;
  svg += `<text x="${margen.izquierda + anchoUtil / 2}" y="${alto - 8}" font-size="11.5"
           fill="#1b2430" text-anchor="middle">Contribución media al logit (b_d · s_d)</text>`;
  svg += "</svg>";

  destino.innerHTML = svg;
}

/* ================================================ 6. TABLA ESTUDIANTES */
["#f-nivel", "#f-intervencion", "#f-dimension", "#f-orden", "#f-revision"]
  .forEach((sel) => $(sel).addEventListener("change", () => cargarEstudiantes()));

if ($("#f-buscar")) {
  $("#f-buscar").addEventListener("input", () => aplicarFiltroBusqueda());
}
if ($("#btn-exportar-csv")) {
  $("#btn-exportar-csv").addEventListener("click", () => exportarCSV());
}

async function cargarEstudiantes() {
  if (!simulacionActual) return;

  const [orden, sentido] = $("#f-orden").value.split("|");
  const parametros = new URLSearchParams();
  if ($("#f-nivel").value) parametros.set("nivel", $("#f-nivel").value);
  if ($("#f-intervencion").value) parametros.set("intervencion", $("#f-intervencion").value);
  if ($("#f-dimension").value) parametros.set("dimension", $("#f-dimension").value);
  if ($("#f-revision").checked) parametros.set("revision", "true");
  parametros.set("orden", orden);
  parametros.set("sentido", sentido);

  try {
    const datos = await pedir("/api/simulaciones/" + simulacionActual.id +
                              "/estudiantes?" + parametros.toString());
    estudiantesCargados = datos.estudiantes || [];
    aplicarFiltroBusqueda();
  } catch (error) {
    estado(error.message, "error");
  }
}

function obtenerEstudiantesFiltrados() {
  const q = ($("#f-buscar") ? $("#f-buscar").value : "").trim().toLowerCase();
  if (!q) return estudiantesCargados;
  return estudiantesCargados.filter((e) =>
    String(e.codigo || "").toLowerCase().includes(q)
  );
}

function aplicarFiltroBusqueda() {
  const filtrados = obtenerEstudiantesFiltrados();
  pintarTabla(filtrados, filtrados.length);
}

function escaparCSV(valor) {
  const texto = valor == null ? "" : String(valor);
  if (texto.includes(",") || texto.includes('"') || texto.includes("\n")) {
    return '"' + texto.replace(/"/g, '""') + '"';
  }
  return texto;
}

function exportarCSV() {
  const lista = obtenerEstudiantesFiltrados();
  if (!lista.length) {
    estado("No hay estudiantes en la vista actual para exportar.", "error");
    return;
  }
  const cabeceras = [
    "codigo", "valido", "motivo_revision", "campo_revision",
    "p", "p5", "p95", "nivel", "s_academico", "s_financiero",
    "s_laboral", "s_personal", "factor_principal", "problemas",
    "requiere_intervencion"
  ];
  const filas = [cabeceras.join(",")];
  lista.forEach((e) => {
    const r = e.resultado;
    const fila = [
      e.codigo,
      e.valido ? "1" : "0",
      e.motivo_revision || "",
      e.campo_revision || "",
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
    ];
    filas.push(fila.map(escaparCSV).join(","));
  });

  const contenido = "\uFEFF" + filas.join("\r\n");
  const blob = new Blob([contenido], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  const idSim = simulacionActual ? simulacionActual.id : "ref";
  enlace.href = url;
  enlace.download = "simulacion_" + idSim + "_estudiantes.csv";
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
  estado("CSV exportado (" + lista.length + " estudiantes).", "listo");
}

function pintarTabla(estudiantes, total) {
  const esReal = simulacionActual && simulacionActual.parametros.origen === "uci";
  const prefijo = esReal
    ? "Mostrando registros del Dataset Real UCI (códigos UCI-xxxx)"
    : "Mostrando estudiantes de la Cohorte Sintética (códigos UNA-xxxx)";
  $("#caption-tabla").textContent =
    prefijo + " · " + total + " estudiante(s) · pulsa una fila para ver el detalle";
  if ($("#f-buscar")) {
    $("#f-buscar").placeholder = esReal ? "Ej. UCI-0015" : "Ej. UNA-0025";
  }

  if (!estudiantes.length) {
    $("#cuerpo-tabla").innerHTML =
      '<tr><td colspan="10" class="vacio">Ningún estudiante cumple los filtros.</td></tr>';
    return;
  }

  $("#cuerpo-tabla").innerHTML = estudiantes.map((est) => {
    if (!est.resultado) {
      return `<tr data-id="${est.id}">
        <td>${escapar(est.codigo)}</td>
        <td colspan="7" class="vacio">Sin probabilidad · ${escapar(est.motivo_revision)}
            (${escapar(est.campo_revision)})</td>
        <td><span class="insignia revision">Revisión</span></td>
        <td class="no">Humana</td>
      </tr>`;
    }
    const r = est.resultado;
    const problemas = r.problemas.length
      ? r.problemas.map((d) =>
          `<span class="etiqueta-dim dim-${d}">${NOMBRE_DIM[d]}</span>`).join("")
      : '<span class="no">—</span>';
    return `<tr data-id="${est.id}">
      <td>${escapar(est.codigo)}</td>
      <td class="num">${num(r.p, 3)}
          <small style="color:#5b6879">(${num(r.p5, 3)}–${num(r.p95, 3)})</small></td>
      <td><span class="insignia ${r.nivel}">${r.nivel}</span></td>
      <td class="num">${num(r.subpuntajes.academica, 2)}</td>
      <td class="num">${num(r.subpuntajes.financiera, 2)}</td>
      <td class="num">${num(r.subpuntajes.laboral, 2)}</td>
      <td class="num">${num(r.subpuntajes.personal, 2)}</td>
      <td><span class="etiqueta-dim dim-${r.factor_principal}">${NOMBRE_DIM[r.factor_principal]}</span></td>
      <td>${problemas}</td>
      <td>${r.requiere_intervencion
            ? '<span class="si">Sí</span>'
            : '<span class="no">No</span>'}</td>
    </tr>`;
  }).join("");

  $("#cuerpo-tabla").querySelectorAll("tr[data-id]").forEach((fila) => {
    fila.addEventListener("click", () => verDetalle(Number(fila.dataset.id)));
  });
}

/* ====================================================== 7. DETALLE === */
async function verDetalle(estudianteId) {
  try {
    const est = await pedir("/api/estudiantes/" + estudianteId);
    estudianteSeleccionado = estudianteId;
    document.querySelectorAll("#cuerpo-tabla tr").forEach((f) =>
      f.classList.toggle("seleccionada", Number(f.dataset.id) === estudianteId));
    pintarDetalle(est);
    $("#detalle").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    estado(error.message, "error");
  }
}

function pintarDetalle(est) {
  const panel = $("#detalle");
  panel.hidden = false;

  const datosPorDim = DIMENSIONES.map((dim) => `
    <div class="bloque-detalle">
      <h4 style="color:${COLOR_DIM[dim]}">${NOMBRE_DIM[dim]}</h4>
      <ul class="lista-plana">
        ${CAMPOS_DIM[dim].map(([campo, etiqueta]) => `
          <li><span class="clave">${etiqueta}</span>
              <span class="valor-dato">${escapar(valorLegible(campo, est.datos[campo]))}</span></li>`).join("")}
      </ul>
    </div>`).join("");

  if (!est.resultado) {
    panel.innerHTML = `
      <div class="detalle-cabecera">
        <div>
          <h3>${escapar(est.codigo)}</h3>
          <p class="nota">Paso 1: el registro no pasó la validación.</p>
        </div>
        <span class="insignia revision">Revisión humana</span>
      </div>
      <div class="aviso-revision">
        <strong>No se calcula probabilidad.</strong>
        Motivo: <code>${escapar(est.motivo_revision)}</code> en el campo
        <code>${escapar(est.campo_revision)}</code>.
        ${est.error_inyectado
          ? "Este registro trae un error <em>inyectado a propósito</em> (" +
            escapar(est.error_inyectado) + ") para demostrar que el Paso 1 funciona."
          : ""}
        El caso se remite a un asesor humano del comité de apoyo: el modelo
        nunca inventa los datos que faltan.
      </div>
      <div class="rejilla-detalle">${datosPorDim}</div>`;
    return;
  }

  const r = est.resultado;
  const barras = DIMENSIONES.map((dim) => {
    const s = r.subpuntajes[dim];
    const esProblema = r.problemas.includes(dim);
    return `
      <div class="barra-dim ${esProblema ? "problema" : ""}">
        <div class="fila-barra">
          <span>${NOMBRE_DIM[dim]}${esProblema ? " ⚠" : ""}</span>
          <span>s = ${num(s, 3)} · aporte ${num(r.contribuciones[dim], 3)}</span>
        </div>
        <div class="pista">
          <div class="relleno" style="width:${(100 * s).toFixed(1)}%;
               background:${COLOR_DIM[dim]}"></div>
        </div>
      </div>`;
  }).join("");

  const intervenciones = r.requiere_intervencion
    ? r.intervenciones.map((i) => `
        <div class="intervencion-item">
          <span class="prioridad">Prioridad ${i.prioridad}</span>
          <strong>${escapar(i.nombre)}</strong>
          <div style="font-size:12px;color:#5b6879">
            Dimensión ${NOMBRE_DIM[i.dimension]} · <code>${escapar(i.tipo)}</code></div>
          <ul>${i.acciones.map((a) => `<li>${escapar(a)}</li>`).join("")}</ul>
        </div>`).join("")
    : `<p class="nota">No requiere intervención: nivel
       <strong>${r.nivel}</strong>${r.problemas.length
         ? " y, aunque tiene dimensiones problemáticas, el nivel no alcanza el criterio."
         : " sin dimensiones problemáticas."}</p>`;

  // Barra visual del intervalo P5-P95
  const escala = Math.max(0.2, Math.min(1, r.p95 * 1.2));
  const aPct = (v) => Math.max(0, Math.min(100, (v / escala) * 100));

  panel.innerHTML = `
    <div class="detalle-cabecera">
      <div>
        <h3>${escapar(est.codigo)}</h3>
        <p class="nota">Factor principal:
          <span class="etiqueta-dim dim-${r.factor_principal}">${NOMBRE_DIM[r.factor_principal]}</span>
          · ${r.problemas.length} dimensión(es) problemática(s) (s ≥ 0,60)</p>
      </div>
      <div style="text-align:right">
        <div style="font-size:30px;font-weight:700;color:${COLOR_NIVEL[r.nivel]}">${pct(r.p, 1)}</div>
        <span class="insignia ${r.nivel}">Riesgo ${r.nivel}</span>
      </div>
    </div>

    <div style="margin-top:14px">
      <div style="font-size:12.5px;color:#5b6879;margin-bottom:5px">
        Intervalo de incertidumbre P5–P95 (Montecarlo sobre los coeficientes,
        K repeticiones): <strong>${pct(r.p5, 1)} – ${pct(r.p95, 1)}</strong>.
        La estimación puntual es ${pct(r.p, 1)}; el modelo no se vende como exacto.
      </div>
      <div style="position:relative;height:22px;background:#e8edf4;border-radius:999px">
        <div style="position:absolute;left:${aPct(r.p5)}%;width:${aPct(r.p95) - aPct(r.p5)}%;
             top:0;height:100%;background:${COLOR_NIVEL[r.nivel]};opacity:.28;border-radius:999px"></div>
        <div style="position:absolute;left:${aPct(r.p)}%;top:-3px;width:3px;height:28px;
             background:${COLOR_NIVEL[r.nivel]};border-radius:2px"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#5b6879">
        <span>0%</span><span>${pct(escala, 0)}</span>
      </div>
    </div>

    <div class="rejilla-detalle">
      <div class="bloque-detalle">
        <h4>Riesgo por dimensión</h4>
        ${barras}
      </div>
      <div class="bloque-detalle">
        <h4>Paso 3 · Intervención propuesta</h4>
        ${intervenciones}
      </div>
    </div>

    <div class="rejilla-detalle">${datosPorDim}</div>`;
}

/* ================================================== 8. VALIDACIÓN ==== */

/* Convierte el {nivel, requiere_intervencion, problemas, ...} de un perfil de
 * referencia en algo que se pueda leer de un vistazo en la sustentación, en
 * vez de un JSON crudo. */
function resumenPerfil(datos) {
  if (!datos) return '<span class="no">—</span>';
  const lineas = [];

  if (datos.nivel) {
    lineas.push(`<span class="insignia ${datos.nivel}">${datos.nivel}</span>`);
  }
  if (datos.requiere_intervencion !== undefined) {
    lineas.push(datos.requiere_intervencion
      ? '<span class="si">requiere intervención</span>'
      : '<span class="no">sin intervención</span>');
  }
  if (datos.problemas) {
    lineas.push(datos.problemas.length
      ? "problemas: " + datos.problemas.map((d) =>
          `<span class="etiqueta-dim dim-${d}">${NOMBRE_DIM[d]}</span>`).join("")
      : '<span class="no">sin problemas</span>');
  }
  if (datos.intervencion_principal) {
    lineas.push('<code style="font-size:11.5px">' +
                escapar(datos.intervencion_principal) + "</code>");
  }
  return lineas.map((l) => `<div style="padding:1px 0">${l}</div>`).join("");
}

function pintarValidacion(sim) {
  const v = sim.validacion_modelo;
  const p = sim.parametros;
  const veredicto = (ok) =>
    `<span class="veredicto ${ok ? "pasa" : "falla"}">${ok ? "pasa" : "falla"}</span>`;

  const cal = v.calibracion;
  const sens = v.sensibilidad;
  const cara = v.validez_de_cara;
  const mono = v.monotonia;
  const real = sim.resumen && sim.resumen.evaluacion_real;

  const bloqueReal = real ? `
    <div class="tarjeta" style="border-left:4px solid var(--bajo)">
      <h3>Validación empírica contra desenlace real (Dataset UCI) ${veredicto(real.auc_roc >= 0.75)}</h3>
      <p class="nota">Evaluación predictiva comparando las probabilidades calculadas por el
        modelo contra el desenlace real observado (<code>Target = Dropout / Graduate</code>)
        en <strong>${escapar(real.fuente)}</strong>.</p>
      <ul class="lista-plana">
        <li><span class="clave">Estudiantes reales evaluados (con desenlace cerrado)</span>
            <span class="valor-dato">${real.n_evaluados} (${real.n_desertores_reales} desertores · ${real.n_graduados_reales} graduados)</span></li>
        <li><span class="clave">Tasa de deserción acumulada observada en el dataset</span>
            <span class="valor-dato">${pct(real.tasa_desercion_observada, 2)}</span></li>
        <li><span class="clave">Área bajo la curva ROC (AUC–ROC, Mann-Whitney U)</span>
            <span class="valor-dato"><strong>${num(real.auc_roc, 4)}</strong></span></li>
        <li><span class="clave">Probabilidad media asignada a desertores reales</span>
            <span class="valor-dato">${pct(real.p_media_desertores, 2)}</span></li>
        <li><span class="clave">Probabilidad media asignada a graduados reales</span>
            <span class="valor-dato">${pct(real.p_media_graduados, 2)}</span></li>
        <li><span class="clave">Sensibilidad / Especificidad (al criterio de intervención)</span>
            <span class="valor-dato">${pct(real.matriz_confusion.sensibilidad, 1)} / ${pct(real.matriz_confusion.especificidad, 1)} (Exactitud: ${pct(real.matriz_confusion.exactitud, 1)})</span></li>
        <li><span class="clave">Tutorías académicas activadas (sA ≥ 0,60)</span>
            <span class="valor-dato"><strong>${sim.resumen.problemas_por_dimension.academica}</strong> estudiantes</span></li>
      </ul>
    </div>` : "";

  $("#validacion").innerHTML = `
    ${bloqueReal}
    <div class="tarjeta">
      <h3>Calibración ${veredicto(cal.ok)}</h3>
      <p class="nota">b₀ no se inventa: se despeja por bisección para que la
        probabilidad media de la cohorte sea igual a la tasa base.</p>
      <ul class="lista-plana">
        <li><span class="clave">Tasa base (objetivo)</span>
            <span class="valor-dato">${num(cal.tasa_base, 5)}</span></li>
        <li><span class="clave">Probabilidad media obtenida</span>
            <span class="valor-dato">${num(cal.media_obtenida, 5)}</span></li>
        <li><span class="clave">Diferencia</span>
            <span class="valor-dato">${num(cal.diferencia, 6)}</span></li>
        <li><span class="clave">Margen aceptado</span>
            <span class="valor-dato">± ${num(cal.margen, 3)}</span></li>
        <li><span class="clave">b₀ calibrado</span>
            <span class="valor-dato">${num(cal.b0_calibrado, 5)}</span></li>
      </ul>
      <p class="formula">p = 1 / (1 + exp(-(b₀ + ${num(p.coeficientes.academica, 1)}·sA + ${num(p.coeficientes.financiera, 1)}·sF + ${num(p.coeficientes.laboral, 1)}·sL + ${num(p.coeficientes.personal, 1)}·sP)))
b₀ = ${num(cal.b0_calibrado, 5)}  (calibrado, no supuesto)</p>
    </div>

    <div class="tarjeta">
      <h3>Sensibilidad a los coeficientes</h3>
      <p class="nota">Cada coeficiente se mueve ±${pct(sens.variacion, 0)} y se mide
        cuánto cambia el índice general (b₀ se deja fijo: si se recalibrara, el
        índice volvería por construcción a la tasa base).
        El supuesto más influyente es
        <strong>${NOMBRE_DIM[sens.mas_influyente]}</strong>.</p>
      <div class="envoltorio-tabla">
        <table>
          <thead><tr>
            <th scope="col">Dimensión</th><th scope="col">b base</th>
            <th scope="col">−50% → índice</th><th scope="col">Índice base</th>
            <th scope="col">+50% → índice</th><th scope="col">Amplitud</th>
          </tr></thead>
          <tbody>
            ${sens.filas.map((f) => `
              <tr>
                <td><span class="etiqueta-dim dim-${f.dimension}">${NOMBRE_DIM[f.dimension]}</span></td>
                <td class="num">${num(f.coeficiente_base, 2)}</td>
                <td class="num">${pct(f.indice_bajo, 2)}</td>
                <td class="num">${pct(f.indice_base, 2)}</td>
                <td class="num">${pct(f.indice_alto, 2)}</td>
                <td class="num"><strong>${num(f.amplitud_pp, 2)} pp</strong></td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>

    <div class="tarjeta">
      <h3>Validez de cara ${veredicto(cara.ok)}</h3>
      <p class="nota">Tres perfiles de referencia con el resultado esperado escrito
        de antemano. Si un estudiante sin problemas saliera "alto", el modelo
        estaría mal por mucho que calibre.</p>
      <div class="envoltorio-tabla">
        <table>
          <thead><tr>
            <th scope="col">Perfil</th>
            <th scope="col">sA&nbsp;/&nbsp;sF&nbsp;/&nbsp;sL&nbsp;/&nbsp;sP</th>
            <th scope="col">p</th><th scope="col">Esperado</th>
            <th scope="col">Obtenido</th><th scope="col">¿Coincide?</th>
          </tr></thead>
          <tbody>
            ${cara.perfiles.map((perfil) => `
              <tr>
                <td><strong>${escapar(perfil.nombre)}</strong>
                    <div style="font-size:11.5px;color:#5b6879">${escapar(perfil.descripcion)}</div></td>
                <td class="num" style="white-space:nowrap">${DIMENSIONES.map((d) => num(perfil.subpuntajes[d], 2)).join(" / ")}</td>
                <td class="num">${num(perfil.p, 4)}</td>
                <td>${resumenPerfil(perfil.esperado)}</td>
                <td>${resumenPerfil(perfil.obtenido)}</td>
                <td>${veredicto(perfil.coincide)}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>

    <div class="tarjeta">
      <h3>Monotonía ${veredicto(mono.ok)}</h3>
      <p class="nota">Empeorar una variable de riesgo nunca debe bajar p.
        Se comprobaron ${mono.n_variables} variables recorriendo sus valores de
        mejor a peor.</p>
      <div class="envoltorio-tabla">
        <table>
          <thead><tr>
            <th scope="col">Variable</th><th scope="col">p en el mejor valor</th>
            <th scope="col">p en el peor valor</th><th scope="col">Pasos</th>
            <th scope="col">¿Monótona?</th>
          </tr></thead>
          <tbody>
            ${mono.variables.map((f) => `
              <tr>
                <td><code>${escapar(f.variable)}</code></td>
                <td class="num">${num(f.p_mejor, 4)}</td>
                <td class="num">${num(f.p_peor, 4)}</td>
                <td class="num">${f.pasos.length}</td>
                <td>${veredicto(f.ok)}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>`;
}

/* =================================================== 9. HISTORIAL ==== */
async function cargarHistorial() {
  try {
    const datos = await pedir("/api/simulaciones?limite=50");
    const filas = datos.simulaciones;

    if (!filas.length) {
      $("#cuerpo-historial").innerHTML =
        '<tr><td colspan="11" class="vacio">Todavía no hay simulaciones guardadas.</td></tr>';
      return;
    }

    $("#cuerpo-historial").innerHTML = filas.map((s) => {
      const esUci = s.origen === "uci";
      const esSpadies = !esUci && Math.abs(s.tasa_base - 0.0442) < 0.001;
      const etqOrigen = esUci
        ? '<span class="insignia-fuente real">Dataset Real UCI</span>'
        : esSpadies
          ? '<span class="insignia-fuente spadies">Simulada · SPADIES</span>'
          : '<span class="insignia-fuente sintetica">Simulada · Montecarlo</span>';
      return `
      <tr data-id="${s.id}">
        <td><strong>#${s.id}</strong></td>
        <td>${etqOrigen}</td>
        <td>${escapar(s.fecha.replace("T", " "))}</td>
        <td class="num">${s.n}</td>
        <td class="num">${esUci ? "—" : s.semilla}</td>
        <td class="num">${pct(s.tasa_base, 2)}</td>
        <td class="num">${num(s.b0_calibrado, 3)}</td>
        <td class="num"><strong>${pct(s.indice_general, 2)}</strong></td>
        <td class="num">${num(s.pct_alto, 1)}%</td>
        <td class="num">${num(s.pct_intervencion, 1)}%</td>
        <td class="num">${s.n_revision_humana}</td>
      </tr>`;
    }).join("");

    $("#cuerpo-historial").querySelectorAll("tr[data-id]").forEach((fila) => {
      fila.addEventListener("click", () => abrirSimulacion(Number(fila.dataset.id)));
    });
  } catch (error) {
    estado(error.message, "error");
  }
}

async function abrirSimulacion(simulacionId) {
  try {
    const sim = await pedir("/api/simulaciones/" + simulacionId);
    simulacionActual = sim;
    if ($("#origen")) $("#origen").value = sim.parametros.origen || "sintetica";
    $("#n").value = sim.parametros.n;
    $("#semilla").value = sim.parametros.semilla;
    $("#tasa_base").value = sim.parametros.tasa_base;
    $("#umbral_medio").value = sim.parametros.umbral_medio;
    $("#umbral_alto").value = sim.parametros.umbral_alto;
    $("#k_montecarlo").value = sim.parametros.k_montecarlo;
    $("#detalle").hidden = true;
    pintarSimulacion(sim);
    await cargarEstudiantes();
    estado("Simulación #" + sim.id + " cargada desde la base de datos.", "listo");

    document.querySelector('.pestana[data-panel="panel-resultados"]').click();
  } catch (error) {
    estado(error.message, "error");
  }
}

/* ============================================= 9b. EVALUADOR WHAT-IF = */
const CATALOGO_INTERVENCIONES = {
  academica: {
    tipo: "tutoria_academica",
    nombre: "Tutoria academica",
    acciones: [
      "tutoria par en las materias perdidas",
      "plan de recuperacion con el docente guia"
    ]
  },
  financiera: {
    tipo: "apoyo_financiero",
    nombre: "Plan de apoyo financiero",
    acciones: [
      "reestructuracion de matricula en 4 cuotas sin intereses",
      "beca de alimentacion",
      "bono de transporte mensual"
    ]
  },
  laboral: {
    tipo: "flexibilidad_laboral",
    nombre: "Flexibilidad horaria / jornada nocturna",
    acciones: [
      "reubicacion de horario de clases",
      "oferta de asignaturas en jornada nocturna"
    ]
  },
  personal: {
    tipo: "bienestar_universitario",
    nombre: "Acompanamiento de bienestar universitario",
    acciones: [
      "cita con bienestar universitario",
      "red de apoyo entre pares"
    ]
  }
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

const RANGOS_WHATIF = {
  promedio: [0.0, 5.0, false],
  materias_perdidas: [0, 8, true],
  asistencia_pct: [0.0, 100.0, false],
  semestre: [1, 12, true],
  saldo_pendiente_cop: [0, 20000000, true],
  ingreso_hogar_smmlv: [0.0, 20.0, false],
  estrato: [1, 6, true],
  horas_trabajo_semana: [0.0, 60.0, false],
  tiempo_desplazamiento_min: [0, 240, true],
  personas_a_cargo: [0, 6, true],
  apoyo_familiar: [1, 5, true]
};

function leerRegistroWhatIf() {
  const r = {};
  Object.keys(RANGOS_WHATIF).forEach((campo) => {
    const el = $("#wi-" + campo);
    if (!el || el.value.trim() === "") {
      r[campo] = null;
      return;
    }
    const v = Number(el.value);
    r[campo] = v;
  });
  ["tiene_apoyo_financiero", "trabaja_en_area_de_estudio", "primera_generacion_universitaria"]
    .forEach((campo) => {
      const el = $("#wi-" + campo);
      r[campo] = el ? el.value === "true" : false;
    });
  return r;
}

function validarRegistroCliente(r) {
  // 1. Campo faltante
  for (const campo of Object.keys(RANGOS_WHATIF)) {
    if (r[campo] === null || r[campo] === undefined) {
      return { valido: false, motivo: "campo_faltante", campo };
    }
  }
  // 2. Tipo invalido (NaN, infinito o decimal en campo entero)
  for (const [campo, [, , esEntero]] of Object.entries(RANGOS_WHATIF)) {
    const v = r[campo];
    if (typeof v !== "number" || !Number.isFinite(v)) {
      return { valido: false, motivo: "tipo_invalido", campo };
    }
    if (esEntero && !Number.isInteger(v)) {
      return { valido: false, motivo: "tipo_invalido", campo };
    }
  }
  // 3. Fuera de rango
  for (const [campo, [min, max]] of Object.entries(RANGOS_WHATIF)) {
    const v = r[campo];
    if (v < min || v > max) {
      return { valido: false, motivo: "fuera_de_rango", campo };
    }
  }
  // 4. Datos contradictorios
  if (r.estrato >= 5 && r.ingreso_hogar_smmlv < 1.0) {
    return { valido: false, motivo: "datos_contradictorios", campo: "estrato_ingreso" };
  }
  if (r.estrato <= 2 && r.ingreso_hogar_smmlv > 10.0) {
    return { valido: false, motivo: "datos_contradictorios", campo: "estrato_ingreso" };
  }
  if (r.materias_perdidas > 0 && r.promedio === 5.0) {
    return { valido: false, motivo: "datos_contradictorios", campo: "promedio_materias_perdidas" };
  }
  return { valido: true, motivo: null, campo: null };
}

function recorte(v, min = 0.0, max = 1.0) {
  return Math.max(min, Math.min(max, v));
}

function evaluarWhatIf() {
  const panel = $("#resultado-whatif");
  if (!panel) return;

  const r = leerRegistroWhatIf();
  const veredicto = validarRegistroCliente(r);

  if (!veredicto.valido) {
    panel.innerHTML = `
      <div class="detalle-cabecera">
        <div>
          <h3>Veredicto Paso 1: Rechazado</h3>
          <p class="nota">El registro no supera las reglas del contrato.</p>
        </div>
        <span class="insignia revision">Revisión humana</span>
      </div>
      <div class="aviso-revision" style="margin-top:10px">
        <strong>No se calcula probabilidad.</strong>
        Motivo: <code>${escapar(veredicto.motivo)}</code> en
        <code>${escapar(veredicto.campo)}</code>.
        El caso se remite a un asesor humano del comité de apoyo.
      </div>`;
    return;
  }

  const params = simulacionActual ? simulacionActual.parametros : {
    b0_calibrado: -4.94753435254097,
    umbral_medio: 0.15,
    umbral_alto: 0.35,
    umbral_problema: 0.60,
    coeficientes: { academica: 3.0, financiera: 2.5, laboral: 1.5, personal: 1.2 }
  };

  const sA = recorte(
    0.40 * (1 - r.promedio / 5.0) +
    0.30 * Math.min(r.materias_perdidas / 3.0, 1.0) +
    0.30 * (1 - r.asistencia_pct / 100.0)
  );
  const sF = recorte(
    0.35 * Math.min(r.saldo_pendiente_cop / 8000000.0, 1.0) +
    0.30 * (1 - Math.min(r.ingreso_hogar_smmlv / 4.0, 1.0)) +
    0.20 * ((6 - r.estrato) / 5.0) +
    0.15 * (r.tiene_apoyo_financiero ? 0.0 : 1.0)
  );
  const intensidad = Math.min(r.horas_trabajo_semana / 40.0, 1.0);
  const desalineado = r.trabaja_en_area_de_estudio ? 0.0 : 1.0;
  const sL = recorte(0.70 * intensidad + 0.30 * intensidad * desalineado);
  const sP = recorte(
    0.30 * Math.min(r.tiempo_desplazamiento_min / 120.0, 1.0) +
    0.25 * Math.min(r.personas_a_cargo / 3.0, 1.0) +
    0.30 * ((5 - r.apoyo_familiar) / 4.0) +
    0.15 * (r.primera_generacion_universitaria ? 1.0 : 0.0)
  );

  const subpuntajes = { academica: sA, financiera: sF, laboral: sL, personal: sP };
  const coef = params.coeficientes;
  const contribuciones = {};
  let z = params.b0_calibrado;
  DIMENSIONES.forEach((d) => {
    contribuciones[d] = coef[d] * subpuntajes[d];
    z += contribuciones[d];
  });
  const p = z >= 0 ? 1.0 / (1.0 + Math.exp(-z)) : Math.exp(z) / (1.0 + Math.exp(z));

  const nivel = p >= params.umbral_alto ? "alto"
              : p >= params.umbral_medio ? "medio" : "bajo";

  let factorPrincipal = DIMENSIONES[0];
  DIMENSIONES.forEach((d) => {
    if (contribuciones[d] > contribuciones[factorPrincipal]) factorPrincipal = d;
  });

  const umbralProb = params.umbral_problema || 0.60;
  const problemas = DIMENSIONES
    .filter((d) => subpuntajes[d] >= umbralProb)
    .sort((a, b) => subpuntajes[b] - subpuntajes[a]);

  const requiereIntervencion = nivel === "alto" || (nivel === "medio" && problemas.length > 0);
  let ordenadas = problemas.filter((d) => d !== factorPrincipal);
  if (problemas.includes(factorPrincipal)) {
    ordenadas.unshift(factorPrincipal);
  } else if (requiereIntervencion && !ordenadas.length) {
    ordenadas = [factorPrincipal];
  }

  const barras = DIMENSIONES.map((dim) => {
    const s = subpuntajes[dim];
    const esProblema = problemas.includes(dim);
    return `
      <div class="barra-dim ${esProblema ? "problema" : ""}">
        <div class="fila-barra">
          <span>${NOMBRE_DIM[dim]}${esProblema ? " ⚠" : ""}</span>
          <span>s = ${num(s, 3)} · aporte b·s = ${num(contribuciones[dim], 3)}</span>
        </div>
        <div class="pista">
          <div class="relleno" style="width:${(100 * s).toFixed(1)}%;
               background:${COLOR_DIM[dim]}"></div>
        </div>
      </div>`;
  }).join("");

  const htmlIntervenciones = requiereIntervencion
    ? ordenadas.map((dim, idx) => {
        const ficha = CATALOGO_INTERVENCIONES[dim];
        return `
          <div class="intervencion-item">
            <span class="prioridad">Prioridad ${idx + 1}</span>
            <strong>${escapar(ficha.nombre)}</strong>
            <div style="font-size:12px;color:#5b6879">
              Dimensión ${NOMBRE_DIM[dim]} · <code>${escapar(ficha.tipo)}</code></div>
            <ul>${ficha.acciones.map((a) => `<li>${escapar(a)}</li>`).join("")}</ul>
          </div>`;
      }).join("")
    : `<p class="nota">No requiere intervención: nivel
       <strong>${nivel}</strong>${problemas.length
         ? " (aunque tiene dimensión problemática, el nivel global es bajo)."
         : " sin dimensiones problemáticas."}</p>`;

  panel.innerHTML = `
    <div class="detalle-cabecera">
      <div>
        <h3>Resultado en vivo · Paso 1 ✔ → Paso 2 → Paso 3</h3>
        <p class="nota">Factor principal:
          <span class="etiqueta-dim dim-${factorPrincipal}">${NOMBRE_DIM[factorPrincipal]}</span>
          · logit z = ${num(z, 3)} (con b₀ = ${num(params.b0_calibrado, 4)})
          · ${problemas.length} problema(s) (s ≥ 0,60)</p>
      </div>
      <div style="text-align:right">
        <div style="font-size:30px;font-weight:700;color:${COLOR_NIVEL[nivel]}">${pct(p, 1)}</div>
        <span class="insignia ${nivel}">Riesgo ${nivel}</span>
      </div>
    </div>
    <div class="rejilla-detalle">
      <div class="bloque-detalle">
        <h4>Paso 2 · Subpuntajes y aportes</h4>
        ${barras}
      </div>
      <div class="bloque-detalle">
        <h4>Paso 3 · Plan de intervención</h4>
        ${htmlIntervenciones}
      </div>
    </div>`;
}

if ($("#form-whatif")) {
  $("#form-whatif").querySelectorAll("input, select").forEach((el) => {
    el.addEventListener("input", () => evaluarWhatIf());
    el.addEventListener("change", () => evaluarWhatIf());
  });
  document.querySelectorAll("[data-preset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const preset = PRESETS_WHATIF[btn.dataset.preset];
      if (!preset) return;
      Object.entries(preset).forEach(([campo, valor]) => {
        const el = $("#wi-" + campo);
        if (el) el.value = String(valor);
      });
      evaluarWhatIf();
    });
  });
  evaluarWhatIf();
}

/* ============================================= 10. ARRANQUE ========== */
(async function inicio() {
  await cargarHistorial();
  // Si ya hay simulaciones guardadas, se abre la más reciente para que la
  // página no arranque vacía al reiniciar el servidor.
  try {
    const datos = await pedir("/api/simulaciones?limite=1");
    if (datos.simulaciones.length) {
      await abrirSimulacion(datos.simulaciones[0].id);
      estado("Se cargó la última simulación guardada (#" +
             datos.simulaciones[0].id + ").");
    }
  } catch (error) {
    /* la página funciona igual sin historial previo */
  }
})();
