"""
Pruebas de estres: 15 registros adversariales con su respuesta esperada.

Mismo espiritu que la ronda 2 de la entrega anterior: no se prueba el camino
feliz, se intenta romper el contrato. Cada caso trae escrito, en la tabla de
abajo, exactamente lo que el Paso 1 debe responder.

Los cuatro grupos de ataque:
  - vacios            (E01, E02)
  - tipos raros       (E03, E04, E05, E06, E15)
  - bordes exactos    (E07, E08, E09, E10, E11)
  - valores extremos  (E12, E13, E14)

Hallazgo de esta ronda: E15. NaN es un float y TODAS sus comparaciones dan
False, asi que pasaba la prueba de rango y llegaba hasta el calculo de la
probabilidad. Se cerro en validacion.py exigiendo que los decimales sean
numeros finitos.
"""

import math

import pytest

import config
from modelo import intervencion, riesgo, validacion


# Base valida sobre la que se construyen los ataques.
BASE = {
    "promedio": 3.5, "materias_perdidas": 1, "asistencia_pct": 85.0,
    "semestre": 4,
    "saldo_pendiente_cop": 2_000_000, "ingreso_hogar_smmlv": 3.0,
    "estrato": 3, "tiene_apoyo_financiero": False,
    "horas_trabajo_semana": 15.0, "trabaja_en_area_de_estudio": False,
    "tiempo_desplazamiento_min": 40, "personas_a_cargo": 1,
    "apoyo_familiar": 4, "primera_generacion_universitaria": False,
}

# Todos los campos en su minimo legal.
MINIMOS = {
    "promedio": 0.0, "materias_perdidas": 0, "asistencia_pct": 0.0,
    "semestre": 1,
    "saldo_pendiente_cop": 0, "ingreso_hogar_smmlv": 0.0,
    "estrato": 1, "tiene_apoyo_financiero": False,
    "horas_trabajo_semana": 0.0, "trabaja_en_area_de_estudio": False,
    "tiempo_desplazamiento_min": 0, "personas_a_cargo": 0,
    "apoyo_familiar": 1, "primera_generacion_universitaria": False,
}

# Todos los campos en su maximo legal (promedio 5.0 y 8 materias perdidas:
# combinacion imposible, a proposito).
MAXIMOS = {
    "promedio": 5.0, "materias_perdidas": 8, "asistencia_pct": 100.0,
    "semestre": 12,
    "saldo_pendiente_cop": 20_000_000, "ingreso_hogar_smmlv": 20.0,
    "estrato": 6, "tiene_apoyo_financiero": True,
    "horas_trabajo_semana": 60.0, "trabaja_en_area_de_estudio": True,
    "tiempo_desplazamiento_min": 240, "personas_a_cargo": 6,
    "apoyo_familiar": 5, "primera_generacion_universitaria": False,
}


def _con(**cambios):
    registro = dict(BASE)
    registro.update(cambios)
    return registro


# ===========================================================================
# LOS 15 CASOS. 'esperado' es la respuesta que el Paso 1 DEBE dar.
# ===========================================================================
CASOS = [
    # ------------------------------------------------------- vacios -----
    {
        "id": "E01",
        "ataque": "Registro completamente vacio",
        "registro": {},
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "campo_faltante", "campo": "promedio"},
    },
    {
        "id": "E02",
        "ataque": "Todos los campos presentes pero en None",
        "registro": {campo: None for campo in config.CAMPOS_OBLIGATORIOS},
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "campo_faltante", "campo": "promedio"},
    },
    # --------------------------------------------------- tipos raros ----
    {
        "id": "E03",
        "ataque": "Promedio como texto, aunque el texto parezca un numero",
        "registro": _con(promedio="4.5"),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "tipo_invalido", "campo": "promedio"},
    },
    {
        "id": "E04",
        "ataque": "Booleano enviado como 1 (verdadero en otros lenguajes)",
        "registro": _con(tiene_apoyo_financiero=1),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "tipo_invalido",
                     "campo": "tiene_apoyo_financiero"},
    },
    {
        "id": "E05",
        "ataque": "Semestre como decimal exacto (4.0 no es un entero)",
        "registro": _con(semestre=4.0),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "tipo_invalido", "campo": "semestre"},
    },
    {
        "id": "E06",
        "ataque": "Lista donde va un numero",
        "registro": _con(horas_trabajo_semana=[15.0]),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "tipo_invalido",
                     "campo": "horas_trabajo_semana"},
    },
    # ------------------------------------------------ bordes exactos ----
    {
        "id": "E07",
        "ataque": "Todos los campos en su minimo legal exacto",
        "registro": dict(MINIMOS),
        "esperado": {"decision": "valido", "motivo": None, "campo": None},
        # El peor estudiante posible que sigue siendo un registro valido:
        # promedio 0.0, 0% de asistencia, sin ingreso y en estrato 1.
        "subpuntajes": {"academica": 0.7, "financiera": 0.65,
                        "laboral": 0.0, "personal": 0.3},
        "problemas": ["academica", "financiera"],
    },
    {
        "id": "E08",
        "ataque": ("Todos los campos en su maximo legal exacto: promedio 5.0 "
                   "con 8 materias perdidas es imposible"),
        "registro": dict(MAXIMOS),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "datos_contradictorios",
                     "campo": "promedio_materias_perdidas"},
    },
    {
        "id": "E09",
        "ataque": "Maximos legales sin la contradiccion (0 materias perdidas)",
        "registro": dict(MAXIMOS, materias_perdidas=0),
        "esperado": {"decision": "valido", "motivo": None, "campo": None},
        "subpuntajes": {"academica": 0.0, "financiera": 0.35,
                        "laboral": 0.7, "personal": 0.55},
        "problemas": ["laboral"],
    },
    {
        "id": "E10",
        "ataque": ("Borde de la contradiccion: estrato 5 con exactamente "
                   "1 SMMLV (la regla rechaza < 1, no <= 1)"),
        "registro": _con(estrato=5, ingreso_hogar_smmlv=1.0),
        "esperado": {"decision": "valido", "motivo": None, "campo": None},
    },
    {
        "id": "E11",
        "ataque": ("Borde del caso A03: estrato 2 con exactamente 10 SMMLV "
                   "(la regla rechaza > 10, no >= 10)"),
        "registro": _con(estrato=2, ingreso_hogar_smmlv=10.0),
        "esperado": {"decision": "valido", "motivo": None, "campo": None},
    },
    # ---------------------------------------------- valores extremos ----
    {
        "id": "E12",
        "ataque": ("Un centesimo al otro lado del borde A03: estrato 2 con "
                   "10.01 SMMLV"),
        "registro": _con(estrato=2, ingreso_hogar_smmlv=10.01),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "datos_contradictorios",
                     "campo": "estrato_ingreso"},
    },
    {
        "id": "E13",
        "ataque": "Un centesimo al otro lado: estrato 5 con 0.99 SMMLV",
        "registro": _con(estrato=5, ingreso_hogar_smmlv=0.99),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "datos_contradictorios",
                     "campo": "estrato_ingreso"},
    },
    {
        "id": "E14",
        "ataque": "Saldo absurdo: un billon de pesos",
        "registro": _con(saldo_pendiente_cop=1_000_000_000_000),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "fuera_de_rango",
                     "campo": "saldo_pendiente_cop"},
    },
    {
        "id": "E15",
        "ataque": ("NaN en el promedio: es un float y todas sus comparaciones "
                   "dan False, asi que burlaba la prueba de rango"),
        "registro": _con(promedio=float("nan")),
        "esperado": {"decision": "requiere_revision_humana",
                     "motivo": "tipo_invalido", "campo": "promedio"},
    },
]


def _ids(casos):
    return [c["id"] + " " + c["ataque"][:45] for c in casos]


# ===========================================================================
# LAS PRUEBAS
# ===========================================================================
def test_hay_quince_casos_adversariales():
    assert len(CASOS) == 15
    assert len({c["id"] for c in CASOS}) == 15


@pytest.mark.parametrize("caso", CASOS, ids=_ids(CASOS))
def test_el_paso_1_responde_lo_esperado(caso):
    """El corazon de la ronda: respuesta obtenida vs. respuesta esperada."""
    obtenido = validacion.validar(caso["registro"])
    esperado = caso["esperado"]

    assert obtenido["decision"] == esperado["decision"], caso["ataque"]
    assert obtenido["motivo"] == esperado["motivo"], caso["ataque"]
    assert obtenido["campo"] == esperado["campo"], caso["ataque"]


@pytest.mark.parametrize("caso", CASOS, ids=_ids(CASOS))
def test_ningun_caso_lanza_una_excepcion(caso):
    """Garantia 1 del contrato: ninguna entrada produce una excepcion."""
    resultado = validacion.validar(caso["registro"])
    assert resultado["decision"] in ("valido", "requiere_revision_humana")


@pytest.mark.parametrize("caso", CASOS, ids=_ids(CASOS))
def test_los_rechazados_siempre_explican_el_motivo(caso):
    resultado = validacion.validar(caso["registro"])
    if resultado["decision"] == "requiere_revision_humana":
        assert resultado["motivo"] in validacion.MOTIVOS
        assert resultado["campo"]
        assert resultado["mensaje"]


@pytest.mark.parametrize(
    "caso", [c for c in CASOS if "subpuntajes" in c],
    ids=_ids([c for c in CASOS if "subpuntajes" in c]))
def test_los_subpuntajes_de_los_bordes_son_los_calculados_a_mano(caso):
    """Los bordes exactos dan los subpuntajes que salen de las formulas."""
    s = riesgo.subpuntajes(caso["registro"])
    for dimension, valor_esperado in caso["subpuntajes"].items():
        assert s[dimension] == pytest.approx(valor_esperado), dimension


@pytest.mark.parametrize(
    "caso", [c for c in CASOS if "problemas" in c],
    ids=_ids([c for c in CASOS if "problemas" in c]))
def test_los_problemas_de_los_bordes_son_los_esperados(caso):
    problemas = riesgo.problemas(riesgo.subpuntajes(caso["registro"]))
    assert set(problemas) == set(caso["problemas"])


# ------------------------------------------- lo que pasa aguas abajo ----
@pytest.mark.parametrize("caso", CASOS, ids=_ids(CASOS))
def test_un_registro_rechazado_nunca_recibe_probabilidad(caso):
    """Garantia 2: sin validacion no hay probabilidad, ni inventada ni cero."""
    resultado = validacion.validar(caso["registro"])
    if resultado["decision"] == "valido":
        p = riesgo.probabilidad(riesgo.subpuntajes(caso["registro"]), -4.95)
        assert math.isfinite(p)
        assert 0.0 <= p <= 1.0
    else:
        # El simulador no sigue adelante: no hay nada que calcular.
        assert resultado["motivo"] is not None


@pytest.mark.parametrize("caso", [c for c in CASOS
                                  if c["esperado"]["decision"] == "valido"],
                         ids=_ids([c for c in CASOS
                                   if c["esperado"]["decision"] == "valido"]))
def test_los_validos_recorren_la_cadena_completa_sin_romperse(caso):
    """Pasos 2 y 3 sobre los registros adversariales que SI son validos."""
    evaluacion = riesgo.evaluar(caso["registro"], -4.95)
    plan = intervencion.decidir(evaluacion["nivel"], evaluacion["problemas"],
                                evaluacion["factor_principal"])

    assert 0.0 <= evaluacion["p"] <= 1.0
    assert evaluacion["nivel"] in ("bajo", "medio", "alto")
    assert evaluacion["factor_principal"] in config.DIMENSIONES
    for valor in evaluacion["subpuntajes"].values():
        assert 0.0 <= valor <= 1.0
    if plan["requiere_intervencion"]:
        assert plan["intervenciones"]
    else:
        assert plan["intervenciones"] == []


def test_infinito_tambien_se_rechaza():
    """Hermano de E15: +inf e -inf tampoco son numeros usables."""
    for valor in (float("inf"), float("-inf")):
        resultado = validacion.validar(_con(promedio=valor))
        assert resultado["decision"] == "requiere_revision_humana"
        assert resultado["motivo"] == "tipo_invalido"
        assert resultado["campo"] == "promedio"


def test_el_registro_base_de_los_ataques_es_valido():
    """Control: si BASE no fuera valido, los 15 ataques no probarian nada."""
    assert validacion.validar(BASE)["decision"] == "valido"
