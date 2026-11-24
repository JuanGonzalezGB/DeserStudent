"""
Paquete del modelo de simulacion y orquestador de la cadena de pasos.

La cadena es la misma de la entrega anterior, un paso por modulo:

    E ──> [ Paso 1: validar ] ──> [ Paso 2: riesgo ] ──> [ Paso 3: intervencion ]
              validacion.py           riesgo.py              intervencion.py
                                    incertidumbre.py

Alrededor de la cadena:
    generador.py    muestrea la cohorte sintetica (Montecarlo)
    sensibilidad.py valida el modelo (calibracion, sensibilidad, cara, monotonia)

simular() corre todo de punta a punta y devuelve un dict serializable a JSON,
sin tocar la base de datos: quien persiste es db.py y quien expone es app.py.
"""

import random

import config

from modelo import validacion          # noqa: F401  (orden: antes de sensibilidad)
from modelo import riesgo              # noqa: F401
from modelo import incertidumbre       # noqa: F401
from modelo import intervencion        # noqa: F401
from modelo import generador           # noqa: F401
from modelo import sensibilidad        # noqa: F401
from modelo import datos_reales        # noqa: F401

# Desfase de la semilla del Montecarlo de incertidumbre respecto a la semilla
# de la simulacion, para que los dos muestreos no compartan el mismo flujo de
# numeros aleatorios pero sigan siendo reproducibles.
DESFASE_SEMILLA_INCERTIDUMBRE = 10_000


def simular(n=None, semilla=None, tasa_base=None, umbral_medio=None,
            umbral_alto=None, k_montecarlo=None, origen=None):
    """Corre una simulacion completa.

    origen:
      - None o 'sintetica': genera la cohorte sintetica con Montecarlo 1.
      - 'uci': carga los registros reales del dataset UCI (Realinho et al.) y
               calcula ademas la validacion empirica (AUC-ROC y matriz de
               confusion) contra el desenlace real observado ('Target').

    Devuelve {"parametros", "resumen", "estudiantes", "validacion_modelo"}.
    """
    n = config.N_POR_DEFECTO if n is None else n
    semilla = config.SEMILLA_POR_DEFECTO if semilla is None else semilla
    tasa_base = config.TASA_BASE_SEMESTRAL if tasa_base is None else tasa_base
    umbral_medio = config.UMBRAL_MEDIO if umbral_medio is None else umbral_medio
    umbral_alto = config.UMBRAL_ALTO if umbral_alto is None else umbral_alto
    k = config.K_MONTECARLO if k_montecarlo is None else k_montecarlo

    # --- Origen de la cohorte: sintetica (Montecarlo 1) o real (UCI) ---
    if origen == "uci":
        cohorte = datos_reales.cargar_cohorte_uci(
            n=n, solo_cerrados=True, semilla=semilla)
        n = len(cohorte)
    else:
        cohorte = generador.generar_cohorte(n=n, semilla=semilla)

    # --- Paso 1: validar cada registro --------------------------------
    estudiantes = []
    for item in cohorte:
        veredicto = validacion.validar(item["datos"])
        est = {
            "codigo": item["codigo"],
            "datos": item["datos"],
            "error_inyectado": item["error_inyectado"],
            "valido": veredicto["decision"] == "valido",
            "motivo_revision": veredicto["motivo"],
            "campo_revision": veredicto["campo"],
            "mensaje_revision": veredicto["mensaje"],
            "resultado": None,
        }
        if "desenlace_real" in item:
            est["desenlace_real"] = item["desenlace_real"]
        estudiantes.append(est)

    validos = [e for e in estudiantes if e["valido"]]

    # --- Paso 2a: subpuntajes de los validos --------------------------
    for e in validos:
        e["_s"] = riesgo.subpuntajes(e["datos"])
    lista_s = [e["_s"] for e in validos]

    # --- Paso 2b: calibrar b0 contra la tasa base ---------------------
    b0 = riesgo.calibrar_b0(lista_s, tasa_base)

    # --- Montecarlo 2: incertidumbre de los coeficientes --------------
    rng_mc = random.Random(semilla + DESFASE_SEMILLA_INCERTIDUMBRE)
    muestras = incertidumbre.muestrear_coeficientes(rng_mc, k)

    # --- Paso 2c-2d y Paso 3 ------------------------------------------
    for e in validos:
        s = e.pop("_s")
        contribs = riesgo.contribuciones(s)
        p = riesgo.probabilidad(s, b0)
        nivel = riesgo.nivel(p, umbral_medio, umbral_alto)
        problemas = riesgo.problemas(s)
        factor = riesgo.factor_principal(contribs)
        p5, p95 = incertidumbre.intervalo(s, b0, muestras)
        plan = intervencion.decidir(nivel, problemas, factor)

        e["resultado"] = {
            "subpuntajes": s,
            "contribuciones": contribs,
            "p": p,
            "p5": p5,
            "p95": p95,
            "nivel": nivel,
            "factor_principal": factor,
            "problemas": problemas,
            "requiere_intervencion": plan["requiere_intervencion"],
            "intervenciones": plan["intervenciones"],
        }

    # --- Indice general y porcentajes ---------------------------------
    resumen = _resumir(estudiantes, validos)
    if origen == "uci":
        eval_real = datos_reales.evaluar_contra_desenlace_real(estudiantes)
        if eval_real is not None:
            resumen["evaluacion_real"] = eval_real

    # --- Validacion del modelo ----------------------------------------
    val_modelo = sensibilidad.validar_modelo(
        lista_s, b0, tasa_base, umbral_medio, umbral_alto)

    parametros_salida = {
        "n": n,
        "semilla": semilla,
        "tasa_base": tasa_base,
        "umbral_medio": umbral_medio,
        "umbral_alto": umbral_alto,
        "k_montecarlo": k,
        "coeficientes": dict(config.COEFICIENTES),
        "umbral_problema": config.UMBRAL_PROBLEMA,
        "b0_calibrado": b0,
    }
    if origen is not None:
        parametros_salida["origen"] = origen

    return {
        "parametros": parametros_salida,
        "resumen": resumen,
        "estudiantes": estudiantes,
        "validacion_modelo": val_modelo,
    }


def _resumir(estudiantes, validos):
    """Indice de riesgo general y reparto por nivel."""
    total_validos = len(validos)
    n_revision = len(estudiantes) - total_validos

    if total_validos == 0:
        return {
            "n_total": len(estudiantes),
            "n_validos": 0,
            "n_revision_humana": n_revision,
            "indice_general": 0.0,
            "pct_bajo": 0.0, "pct_medio": 0.0, "pct_alto": 0.0,
            "pct_intervencion": 0.0,
            "conteo_nivel": {"bajo": 0, "medio": 0, "alto": 0},
            "n_intervencion": 0,
            "contribucion_promedio": {d: 0.0 for d in config.DIMENSIONES},
            "subpuntaje_promedio": {d: 0.0 for d in config.DIMENSIONES},
            "problemas_por_dimension": {d: 0 for d in config.DIMENSIONES},
            "probabilidades": [],
        }

    probabilidades = [e["resultado"]["p"] for e in validos]
    conteo = {"bajo": 0, "medio": 0, "alto": 0}
    n_interv = 0
    suma_contrib = {d: 0.0 for d in config.DIMENSIONES}
    suma_sub = {d: 0.0 for d in config.DIMENSIONES}
    problemas_dim = {d: 0 for d in config.DIMENSIONES}

    for e in validos:
        res = e["resultado"]
        conteo[res["nivel"]] += 1
        if res["requiere_intervencion"]:
            n_interv += 1
        for d in config.DIMENSIONES:
            suma_contrib[d] += res["contribuciones"][d]
            suma_sub[d] += res["subpuntajes"][d]
        for d in res["problemas"]:
            problemas_dim[d] += 1

    def pct(cantidad):
        return 100.0 * cantidad / total_validos

    return {
        "n_total": len(estudiantes),
        "n_validos": total_validos,
        "n_revision_humana": n_revision,
        # Indice de riesgo general = probabilidad media de la cohorte valida.
        "indice_general": sum(probabilidades) / total_validos,
        "pct_bajo": pct(conteo["bajo"]),
        "pct_medio": pct(conteo["medio"]),
        "pct_alto": pct(conteo["alto"]),
        "pct_intervencion": pct(n_interv),
        "conteo_nivel": conteo,
        "n_intervencion": n_interv,
        "contribucion_promedio": {d: suma_contrib[d] / total_validos
                                  for d in config.DIMENSIONES},
        "subpuntaje_promedio": {d: suma_sub[d] / total_validos
                                for d in config.DIMENSIONES},
        "problemas_por_dimension": problemas_dim,
        "probabilidades": probabilidades,
    }


# Valor b0 calibrado de la simulacion de referencia (n=500, semilla=42, tasa=0.09)
# cuando se evalua un estudiante aislado sin una simulacion previa cargada.
B0_REFERENCIA_DEFECTO = -4.94753435254097


def evaluar_estudiante(registro, b0=None, umbral_medio=None, umbral_alto=None,
                       k_montecarlo=None, semilla=None):
    """Evalua un unico estudiante con la cadena oficial Paso 1 -> 2 -> 3.

    Elimina la necesidad de duplicar formulas, topes o validaciones en JS:
    devuelve exactamente la misma estructura que un elemento de 'estudiantes'
    en simular(), incluyendo el intervalo de incertidumbre P5-P95.
    """
    b0_uso = B0_REFERENCIA_DEFECTO if b0 is None else b0
    u_medio = config.UMBRAL_MEDIO if umbral_medio is None else umbral_medio
    u_alto = config.UMBRAL_ALTO if umbral_alto is None else umbral_alto
    k = config.K_MONTECARLO if k_montecarlo is None else k_montecarlo
    sem = config.SEMILLA_POR_DEFECTO if semilla is None else semilla

    parametros_uso = {
        "b0_calibrado": b0_uso,
        "umbral_medio": u_medio,
        "umbral_alto": u_alto,
        "umbral_problema": config.UMBRAL_PROBLEMA,
        "k_montecarlo": k,
        "semilla": sem,
        "coeficientes": dict(config.COEFICIENTES),
    }

    veredicto = validacion.validar(registro)
    if veredicto["decision"] != "valido":
        return {
            "valido": False,
            "motivo_revision": veredicto["motivo"],
            "campo_revision": veredicto["campo"],
            "mensaje_revision": veredicto["mensaje"],
            "parametros": parametros_uso,
            "resultado": None,
        }

    s = riesgo.subpuntajes(registro)
    contribs = riesgo.contribuciones(s)
    z = riesgo.combinacion_lineal(s, b0_uso)
    p = riesgo.probabilidad(s, b0_uso)
    niv = riesgo.nivel(p, u_medio, u_alto)
    probs = riesgo.problemas(s)
    factor = riesgo.factor_principal(contribs)

    rng_mc = random.Random(sem + DESFASE_SEMILLA_INCERTIDUMBRE)
    muestras = incertidumbre.muestrear_coeficientes(rng_mc, k)
    p5, p95 = incertidumbre.intervalo(s, b0_uso, muestras)
    plan = intervencion.decidir(niv, probs, factor)

    return {
        "valido": True,
        "motivo_revision": None,
        "campo_revision": None,
        "mensaje_revision": "",
        "parametros": parametros_uso,
        "resultado": {
            "subpuntajes": s,
            "contribuciones": contribs,
            "logit": z,
            "p": p,
            "p5": p5,
            "p95": p95,
            "nivel": niv,
            "factor_principal": factor,
            "problemas": probs,
            "requiere_intervencion": plan["requiere_intervencion"],
            "intervenciones": plan["intervenciones"],
        },
    }


def configuracion_publica():
    """Metadatos del contrato y parametros del modelo para el frontend."""
    return {
        "dimensiones": list(config.DIMENSIONES),
        "campos_por_dimension": {
            d: list(campos) for d, campos in config.CAMPOS_POR_DIMENSION.items()
        },
        "campos_obligatorios": list(config.CAMPOS_OBLIGATORIOS),
        "campos_enteros": list(config.CAMPOS_ENTEROS),
        "campos_decimales": list(config.CAMPOS_DECIMALES),
        "campos_booleanos": list(config.CAMPOS_BOOLEANOS),
        "rangos": {k: list(v) for k, v in config.RANGOS.items()},
        "coeficientes": dict(config.COEFICIENTES),
        "pesos": {
            "academica": dict(config.PESOS_ACADEMICA),
            "financiera": dict(config.PESOS_FINANCIERA),
            "laboral": dict(config.PESOS_LABORAL),
            "personal": dict(config.PESOS_PERSONAL),
        },
        "saturaciones": {
            "materias_perdidas": config.PERDIDAS_SATURACION,
            "saldo_pendiente_cop": config.SALDO_SATURACION,
            "ingreso_hogar_smmlv": config.INGRESO_SATURACION,
            "horas_trabajo_semana": config.HORAS_SATURACION,
            "tiempo_desplazamiento_min": config.DESPLAZAMIENTO_SATURACION,
            "personas_a_cargo": config.PERSONAS_SATURACION,
        },
        "por_defecto": {
            "n": config.N_POR_DEFECTO,
            "semilla": config.SEMILLA_POR_DEFECTO,
            "tasa_base": config.TASA_BASE_SEMESTRAL,
            "umbral_medio": config.UMBRAL_MEDIO,
            "umbral_alto": config.UMBRAL_ALTO,
            "umbral_problema": config.UMBRAL_PROBLEMA,
            "k_montecarlo": config.K_MONTECARLO,
            "b0_referencia": B0_REFERENCIA_DEFECTO,
        },
        "intervenciones": {
            dim: {
                "tipo": ficha["tipo"],
                "nombre": ficha["nombre"],
                "acciones": list(ficha["acciones"]),
            }
            for dim, ficha in config.INTERVENCIONES.items()
        },
    }
