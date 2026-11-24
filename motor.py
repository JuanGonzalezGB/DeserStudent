"""
Sistema bajo prueba: motor de recomendación del Portal de Acompañamiento.

Tres pasos encadenados, cada uno con su propio contrato (ver 01_contrato.md):

    E ──> [Paso 1: validar perfil] ──> [Paso 2: clasificar riesgo] ──> [Paso 3: recomendar plan]
              │ S1                          │ S2                            │ S3

Hay dos versiones:
  - motor_v1: la primera versión, escrita solo con las reglas del "camino feliz".
  - motor_v2: la versión corregida con los fallos que encontró la ronda 1.
"""

SMMLV_MAX = 20
SALDO_MAX = 20_000_000          # tope de matrícula semestral en COP
DIST_MAX = 100
CAMPOS_OBLIGATORIOS = ["id_estudiante", "nivel", "matriculado", "semestre", "promedio",
                       "materias_inscritas", "materias_perdidas", "saldo_pendiente",
                       "ingreso_hogar_smmlv", "estrato", "distancia_km", "solicita"]
SOLICITUDES = {"financiero", "tutoria", "ambos"}


def _error(motivo, detalle=""):
    return {"decision": "error", "motivo": motivo, "detalle": detalle}


def _abstener(motivo, detalle=""):
    return {"decision": "abstener", "motivo": motivo, "detalle": detalle}


# ---------------------------------------------------------------- PASO 1 ---
def paso1_v1(e):
    """Versión 1: revisa campos faltantes y rangos básicos."""
    for c in CAMPOS_OBLIGATORIOS:
        if c not in e or e[c] is None:
            return _abstener("campo_faltante", c)
    if not e["matriculado"]:
        return _abstener("fuera_de_poblacion", "no matriculado")
    if not (0.0 <= e["promedio"] <= 5.0):
        return _error("fuera_de_rango", "promedio")
    if e["saldo_pendiente"] < 0:
        return _error("fuera_de_rango", "saldo_pendiente")
    if not (1 <= e["semestre"] <= 12):
        return _error("fuera_de_rango", "semestre")
    if e["materias_perdidas"] > e["materias_inscritas"]:
        return _abstener("datos_contradictorios", "perdidas > inscritas")
    return {"decision": "valido", "perfil": dict(e)}


def paso1_v2(e):
    """Versión 2: añade tipos, población, topes, coherencia socioeconómica y semestre 1."""
    for c in CAMPOS_OBLIGATORIOS:
        if c not in e:
            return _abstener("campo_faltante", c)
        if e[c] is None and not (c == "promedio" and e.get("semestre") == 1):
            return _abstener("campo_faltante", c)
    numericos = ["semestre", "materias_inscritas", "materias_perdidas", "saldo_pendiente",
                 "ingreso_hogar_smmlv", "estrato", "distancia_km"]
    if e["promedio"] is not None:
        numericos.append("promedio")
    for c in numericos:
        if isinstance(e[c], bool) or not isinstance(e[c], (int, float)):
            return _error("tipo_invalido", c)
    if e["nivel"] != "pregrado":
        return _abstener("fuera_de_poblacion", f"nivel={e['nivel']}")
    if e["matriculado"] is not True:
        return _abstener("fuera_de_poblacion", "no matriculado")
    if e["solicita"] not in SOLICITUDES:
        return _error("valor_no_permitido", "solicita")
    rangos = {"semestre": (1, 12), "materias_inscritas": (1, 8), "materias_perdidas": (0, 8),
              "saldo_pendiente": (0, SALDO_MAX), "ingreso_hogar_smmlv": (0, SMMLV_MAX),
              "estrato": (1, 6), "distancia_km": (0, DIST_MAX)}
    if e["promedio"] is not None:
        rangos["promedio"] = (0.0, 5.0)
    for c, (lo, hi) in rangos.items():
        if not (lo <= e[c] <= hi):
            return _error("fuera_de_rango", c)
    if e["materias_perdidas"] > e["materias_inscritas"]:
        return _abstener("datos_contradictorios", "perdidas > inscritas")
    if e["estrato"] >= 5 and e["ingreso_hogar_smmlv"] < 1:
        return _abstener("datos_contradictorios", "estrato alto con ingreso < 1 SMMLV")
    return {"decision": "valido", "perfil": dict(e)}


# ---------------------------------------------------------------- PASO 2 ---
def _riesgo_academico(p):
    if p["promedio"] is None:
        return "sin_datos"
    if p["promedio"] < 3.0 or p["materias_perdidas"] >= 2:
        return "alto"
    if p["promedio"] < 3.5 or p["materias_perdidas"] == 1:
        return "medio"
    return "bajo"


def paso2_v1(s1):
    p = s1["perfil"]
    if p["saldo_pendiente"] > 0 and (p["ingreso_hogar_smmlv"] < 2 or p["estrato"] <= 2):
        fin = "alto"
    elif p["saldo_pendiente"] > 0 and p["ingreso_hogar_smmlv"] <= 4:
        fin = "medio"
    else:
        fin = "bajo"
    return {"perfil": p, "riesgo_financiero": fin, "riesgo_academico": _riesgo_academico(p)}


def paso2_v2(s1):
    p = s1["perfil"]
    if p["saldo_pendiente"] > 0 and (p["ingreso_hogar_smmlv"] <= 2 or p["estrato"] <= 2):
        fin = "alto"
    elif p["saldo_pendiente"] > 0 and p["ingreso_hogar_smmlv"] <= 4:
        fin = "medio"
    else:
        fin = "bajo"
    return {"perfil": p, "riesgo_financiero": fin, "riesgo_academico": _riesgo_academico(p)}


# ---------------------------------------------------------------- PASO 3 ---
def paso3(s2):
    """Igual en v1 y v2."""
    p, fin, aca = s2["perfil"], s2["riesgo_financiero"], s2["riesgo_academico"]
    quiere_fin = p["solicita"] in ("financiero", "ambos")
    quiere_tut = p["solicita"] in ("tutoria", "ambos")

    cuotas = 4 if quiere_fin and fin in ("alto", "medio") else 0
    beca = quiere_fin and fin == "alto"
    bono = quiere_fin and fin in ("alto", "medio") and p["distancia_km"] >= 5

    if aca == "alto":
        tutoria = "academica_prioritaria"       # se ofrece aunque no la pida
    elif aca == "medio" and quiere_tut:
        tutoria = "academica"
    elif quiere_tut:
        tutoria = "orientacion"
    else:
        tutoria = "ninguna"

    return {"decision": "plan", "cuotas": cuotas, "beca_alimentacion": beca,
            "bono_transporte": bono, "tutoria": tutoria,
            "riesgo_financiero": fin, "riesgo_academico": aca}


# ------------------------------------------------------------- PIPELINE ---
def _pipeline(e, paso1, paso2):
    traza = {}
    try:
        s1 = paso1(e)
        traza["S1"] = s1["decision"] if s1["decision"] == "valido" else s1
        if s1["decision"] != "valido":
            return s1, traza
        s2 = paso2(s1)
        traza["S2"] = {"riesgo_financiero": s2["riesgo_financiero"],
                       "riesgo_academico": s2["riesgo_academico"]}
        s3 = paso3(s2)
        traza["S3"] = s3
        return s3, traza
    except Exception as ex:                      # un fallo no controlado es un fallo del sistema
        r = {"decision": "excepcion", "motivo": type(ex).__name__, "detalle": str(ex)}
        traza["excepcion"] = r
        return r, traza


def motor_v1(e):
    return _pipeline(e, paso1_v1, paso2_v1)


def motor_v2(e):
    return _pipeline(e, paso1_v2, paso2_v2)
