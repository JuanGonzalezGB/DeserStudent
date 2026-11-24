"""
Motor de recomendación del Portal de Acompañamiento.

Cadena de pasos con cortocircuito:

    E ──> ejecutar_paso1 ──> ejecutar_paso2 ──> ejecutar_paso3
              S1                  S2                  S3

procesar_estudiante(entrada) siempre devuelve {"S1": ..., "S2": ..., "S3": ...}
y nunca lanza una excepción.
"""

from numbers import Real

NIVEL_OBJETIVO = "pregrado"
SOLICITUDES = ("financiero", "tutoria", "ambos")
PIDE_FINANCIERO = ("financiero", "ambos")
PIDE_TUTORIA = ("tutoria", "ambos")

CAMPOS_OBLIGATORIOS = (
    "id_estudiante", "nivel", "matriculado", "semestre", "promedio",
    "materias_inscritas", "materias_perdidas", "saldo_pendiente",
    "ingreso_hogar_smmlv", "estrato", "distancia_km", "solicita",
)
CAMPOS_ENTEROS = ("semestre", "materias_inscritas", "materias_perdidas", "estrato")
CAMPOS_NUMERICOS = ("promedio", "saldo_pendiente", "ingreso_hogar_smmlv", "distancia_km")
RANGOS = {
    "semestre": (1, 12),
    "promedio": (0.0, 5.0),
    "materias_inscritas": (1, 8),
    "materias_perdidas": (0, 8),
    "saldo_pendiente": (0, 20_000_000),
    "ingreso_hogar_smmlv": (0.0, 20.0),
    "estrato": (1, 6),
    "distancia_km": (0.0, 100.0),
}


def _resultado(decision, motivo, campo):
    return {"decision": decision, "motivo": motivo, "campo": campo}


def _es_entero(valor):
    # bool es subclase de int en Python: se excluye a propósito
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_numero(valor):
    return isinstance(valor, Real) and not isinstance(valor, bool)


def _vacio(valor):
    return valor is None or (isinstance(valor, str) and valor.strip() == "")


# ------------------------------------------------------------------ PASO 1 --
def ejecutar_paso1(entrada):
    """Valida el perfil. Devuelve "valido" o un dict con decision error/abstener.

    Orden de evaluación (el primero que aplique gana):
    1. campo_faltante  2. tipo_invalido  3. fuera_de_poblacion
    4. valor_no_permitido  5. fuera_de_rango  6. datos_contradictorios
    """
    if not isinstance(entrada, dict):
        return _resultado("error", "tipo_invalido", "entrada")

    # 1. Campos faltantes (promedio puede ser None solo en semestre 1)
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in entrada or _vacio(entrada[campo]):
            if campo == "promedio" and entrada.get("promedio") is None and entrada.get("semestre") == 1:
                continue
            return _resultado("abstener", "campo_faltante", campo)

    # 2. Tipos estrictos
    if not isinstance(entrada["id_estudiante"], str):
        return _resultado("error", "tipo_invalido", "id_estudiante")
    if not isinstance(entrada["nivel"], str):
        return _resultado("error", "tipo_invalido", "nivel")
    if not isinstance(entrada["matriculado"], bool):
        return _resultado("error", "tipo_invalido", "matriculado")
    if not isinstance(entrada["solicita"], str):
        return _resultado("error", "tipo_invalido", "solicita")
    for campo in CAMPOS_ENTEROS:
        if not _es_entero(entrada[campo]):
            return _resultado("error", "tipo_invalido", campo)
    for campo in CAMPOS_NUMERICOS:
        if campo == "promedio" and entrada[campo] is None:
            continue
        if not _es_numero(entrada[campo]):
            return _resultado("error", "tipo_invalido", campo)

    # 3. Población objetivo
    if entrada["nivel"].strip().lower() != NIVEL_OBJETIVO:
        return _resultado("abstener", "fuera_de_poblacion", "nivel")
    if entrada["matriculado"] is False:
        return _resultado("abstener", "fuera_de_poblacion", "matriculado")

    # 4. Valores permitidos
    if entrada["solicita"].strip().lower() not in SOLICITUDES:
        return _resultado("error", "valor_no_permitido", "solicita")

    # 5. Rangos
    for campo, (minimo, maximo) in RANGOS.items():
        valor = entrada[campo]
        if valor is None:
            continue
        if valor != valor or not (minimo <= valor <= maximo):   # valor != valor detecta NaN
            return _resultado("error", "fuera_de_rango", campo)

    # 6. Contradicciones
    if entrada["materias_perdidas"] > entrada["materias_inscritas"]:
        return _resultado("abstener", "datos_contradictorios", "materias_perdidas")
    if entrada["estrato"] >= 5 and entrada["ingreso_hogar_smmlv"] < 1.0:
        return _resultado("abstener", "datos_contradictorios", "estrato")

    return "valido"


# ------------------------------------------------------------------ PASO 2 --
def ejecutar_paso2(entrada):
    """Clasifica riesgo financiero y académico de un perfil ya validado."""
    saldo = entrada["saldo_pendiente"]
    ingreso = entrada["ingreso_hogar_smmlv"]
    if saldo > 0 and (ingreso <= 2.0 or entrada["estrato"] <= 2):
        financiero = "alto"
    elif saldo > 0 and ingreso <= 4.0:
        financiero = "medio"
    else:
        financiero = "bajo"

    promedio = entrada["promedio"]
    perdidas = entrada["materias_perdidas"]
    if promedio is None:
        academico = "sin_datos"
    elif promedio < 3.0 or perdidas >= 2:
        academico = "alto"
    elif promedio < 3.5 or perdidas == 1:
        academico = "medio"
    else:
        academico = "bajo"

    return {"riesgo_financiero": financiero, "riesgo_academico": academico}


# ------------------------------------------------------------------ PASO 3 --
def ejecutar_paso3(entrada, paso2):
    """Genera el plan de beneficios a partir de la solicitud y los riesgos."""
    solicita = entrada["solicita"].strip().lower()
    financiero = paso2["riesgo_financiero"]
    academico = paso2["riesgo_academico"]
    pide_financiero = solicita in PIDE_FINANCIERO
    pide_tutoria = solicita in PIDE_TUTORIA
    riesgo_fin = financiero in ("alto", "medio")

    if academico == "alto":
        tutoria = "academica_prioritaria"
    elif academico == "medio" and pide_tutoria:
        tutoria = "academica"
    elif pide_tutoria:
        tutoria = "orientacion"
    else:
        tutoria = "ninguna"

    return {
        "decision": "plan",
        "cuotas": 4 if pide_financiero and riesgo_fin else 0,
        "beca_alimentacion": pide_financiero and financiero == "alto",
        "bono_transporte": pide_financiero and riesgo_fin and entrada["distancia_km"] >= 5.0,
        "tutoria": tutoria,
    }


# --------------------------------------------------------------- PIPELINE --
def procesar_estudiante(entrada):
    """Ejecuta la cadena completa con cortocircuito. Nunca lanza excepciones."""
    try:
        s1 = ejecutar_paso1(entrada)
        if s1 != "valido":
            return {"S1": s1, "S2": None, "S3": None}
        s2 = ejecutar_paso2(entrada)
        s3 = ejecutar_paso3(entrada, s2)
        return {"S1": s1, "S2": s2, "S3": s3}
    except Exception as exc:  # red de seguridad: un fallo interno se reporta como error controlado
        return {"S1": _resultado("error", "error_interno", type(exc).__name__), "S2": None, "S3": None}
