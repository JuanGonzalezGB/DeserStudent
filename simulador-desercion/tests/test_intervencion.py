"""
Pruebas del Paso 3 (intervencion): la regla de decision y la prioridad.

Regla:
    requiere_intervencion = nivel alto, o nivel medio con al menos un problema.

Tipo: uno por dimension problematica, del catalogo de config.INTERVENCIONES.
Prioridad: la del factor principal va primero.
"""

import pytest

import config
from modelo import intervencion, riesgo


TIPOS_ESPERADOS = {
    "academica": "tutoria_academica",
    "financiera": "apoyo_financiero",
    "laboral": "flexibilidad_laboral",
    "personal": "bienestar_universitario",
}


# ------------------------------------------------- la regla de decision --
@pytest.mark.parametrize("nivel,problemas,esperado", [
    # Nivel alto: siempre entra, con o sin dimensiones problematicas.
    ("alto", ["financiera"], True),
    ("alto", ["academica", "laboral"], True),
    ("alto", [], True),
    # Nivel medio: solo si hay al menos un problema.
    ("medio", ["financiera"], True),
    ("medio", ["personal"], True),
    ("medio", [], False),
    # Nivel bajo: nunca, aunque tenga una dimension problematica.
    ("bajo", [], False),
    ("bajo", ["financiera"], False),
    ("bajo", ["academica", "financiera", "laboral", "personal"], False),
])
def test_regla_de_requiere_intervencion(nivel, problemas, esperado):
    assert intervencion.requiere_intervencion(nivel, problemas) is esperado


def test_decidir_respeta_la_regla():
    assert intervencion.decidir("bajo", ["financiera"], "financiera") == {
        "requiere_intervencion": False, "intervenciones": []}
    assert intervencion.decidir("medio", [], "financiera") == {
        "requiere_intervencion": False, "intervenciones": []}


# ------------------------------------------- un tipo por cada dimension --
@pytest.mark.parametrize("dimension", config.DIMENSIONES)
def test_cada_dimension_problematica_da_su_intervencion(dimension):
    plan = intervencion.decidir("alto", [dimension], dimension)
    assert plan["requiere_intervencion"] is True
    assert len(plan["intervenciones"]) == 1
    propuesta = plan["intervenciones"][0]
    assert propuesta["dimension"] == dimension
    assert propuesta["tipo"] == TIPOS_ESPERADOS[dimension]
    assert propuesta["prioridad"] == 1
    assert propuesta["acciones"], "toda intervencion propone acciones concretas"


def test_el_plan_financiero_trae_las_opciones_del_prototipo():
    """Cuotas, beca de alimentacion y bono de transporte, como en el motor anterior."""
    plan = intervencion.decidir("alto", ["financiera"], "financiera")
    acciones = " ".join(plan["intervenciones"][0]["acciones"]).lower()
    assert "cuotas" in acciones
    assert "beca de alimentacion" in acciones
    assert "bono de transporte" in acciones


def test_la_intervencion_academica_es_tutoria():
    plan = intervencion.decidir("alto", ["academica"], "academica")
    assert plan["intervenciones"][0]["tipo"] == "tutoria_academica"
    assert "tutoria" in " ".join(plan["intervenciones"][0]["acciones"]).lower()


def test_la_intervencion_laboral_ofrece_jornada_nocturna():
    plan = intervencion.decidir("alto", ["laboral"], "laboral")
    acciones = " ".join(plan["intervenciones"][0]["acciones"]).lower()
    assert "nocturna" in acciones or "horario" in acciones


def test_la_intervencion_personal_es_bienestar():
    plan = intervencion.decidir("alto", ["personal"], "personal")
    acciones = " ".join(plan["intervenciones"][0]["acciones"]).lower()
    assert "bienestar" in acciones


# ---------------------------------------------------------- prioridad ---
def test_el_factor_principal_va_primero():
    plan = intervencion.decidir(
        "alto", ["financiera", "laboral", "personal"], "laboral")
    orden = [i["dimension"] for i in plan["intervenciones"]]
    assert orden[0] == "laboral"
    assert set(orden) == {"financiera", "laboral", "personal"}


def test_las_prioridades_son_consecutivas_desde_uno():
    plan = intervencion.decidir(
        "alto", ["academica", "financiera", "laboral", "personal"], "personal")
    prioridades = [i["prioridad"] for i in plan["intervenciones"]]
    assert prioridades == [1, 2, 3, 4]
    assert plan["intervenciones"][0]["dimension"] == "personal"


def test_se_conserva_el_orden_de_los_demas_problemas():
    """Detras del factor principal, el orden de entrada se mantiene."""
    plan = intervencion.decidir(
        "alto", ["financiera", "academica", "personal"], "academica")
    orden = [i["dimension"] for i in plan["intervenciones"]]
    assert orden == ["academica", "financiera", "personal"]


def test_una_sola_intervencion_cuando_hay_un_solo_problema():
    plan = intervencion.decidir("medio", ["financiera"], "financiera")
    assert len(plan["intervenciones"]) == 1


# ------------------------------------------------------ caso de borde ---
def test_nivel_alto_sin_problemas_atiende_el_factor_principal():
    """Riesgo alto repartido, sin ninguna dimension por encima de 0.60.

    Requiere intervencion, pero la lista de problemas esta vacia. El plan no
    puede quedar vacio: se atiende el factor principal.
    """
    plan = intervencion.decidir("alto", [], "financiera")
    assert plan["requiere_intervencion"] is True
    assert len(plan["intervenciones"]) == 1
    assert plan["intervenciones"][0]["dimension"] == "financiera"
    assert plan["intervenciones"][0]["prioridad"] == 1


def test_factor_principal_que_no_es_problema_no_desplaza_a_los_que_si():
    """Si el factor principal no esta entre los problemas, no se inventa.

    Solo se atienden las dimensiones problematicas; el factor principal pasa
    al frente unicamente cuando tambien es un problema.
    """
    plan = intervencion.decidir("alto", ["laboral", "personal"], "financiera")
    orden = [i["dimension"] for i in plan["intervenciones"]]
    assert orden == ["laboral", "personal"]
    assert "financiera" not in orden


def test_requiere_intervencion_implica_plan_no_vacio():
    """Garantia del Paso 3: nunca 'requiere intervencion' con plan vacio."""
    for nivel in ("bajo", "medio", "alto"):
        for problemas in ([], ["financiera"], ["academica", "personal"],
                          list(config.DIMENSIONES)):
            for factor in config.DIMENSIONES:
                plan = intervencion.decidir(nivel, problemas, factor)
                if plan["requiere_intervencion"]:
                    assert plan["intervenciones"], (nivel, problemas, factor)
                else:
                    assert plan["intervenciones"] == []


# ------------------------------------- integracion con el Paso 2 real ---
def test_cadena_completa_sobre_un_perfil_critico():
    """Paso 2 y Paso 3 encadenados sobre un estudiante de riesgo alto."""
    perfil = {
        "promedio": 1.2, "materias_perdidas": 4, "asistencia_pct": 45.0,
        "semestre": 5,
        "saldo_pendiente_cop": 15_000_000, "ingreso_hogar_smmlv": 0.8,
        "estrato": 1, "tiene_apoyo_financiero": False,
        "horas_trabajo_semana": 45.0, "trabaja_en_area_de_estudio": False,
        "tiempo_desplazamiento_min": 150, "personas_a_cargo": 3,
        "apoyo_familiar": 2, "primera_generacion_universitaria": True,
    }
    evaluacion = riesgo.evaluar(perfil, -4.95)
    plan = intervencion.decidir(evaluacion["nivel"], evaluacion["problemas"],
                                evaluacion["factor_principal"])

    assert evaluacion["nivel"] == "alto"
    assert plan["requiere_intervencion"] is True
    # Las cuatro dimensiones estan sobre el umbral en este perfil.
    assert set(evaluacion["problemas"]) == set(config.DIMENSIONES)
    assert plan["intervenciones"][0]["dimension"] == evaluacion["factor_principal"]


def test_cadena_completa_sobre_un_perfil_tranquilo():
    perfil = {
        "promedio": 4.6, "materias_perdidas": 0, "asistencia_pct": 96.0,
        "semestre": 3,
        "saldo_pendiente_cop": 0, "ingreso_hogar_smmlv": 7.0,
        "estrato": 4, "tiene_apoyo_financiero": True,
        "horas_trabajo_semana": 0.0, "trabaja_en_area_de_estudio": False,
        "tiempo_desplazamiento_min": 15, "personas_a_cargo": 0,
        "apoyo_familiar": 5, "primera_generacion_universitaria": False,
    }
    evaluacion = riesgo.evaluar(perfil, -4.95)
    plan = intervencion.decidir(evaluacion["nivel"], evaluacion["problemas"],
                                evaluacion["factor_principal"])
    assert evaluacion["nivel"] == "bajo"
    assert evaluacion["problemas"] == []
    assert plan["requiere_intervencion"] is False
    assert plan["intervenciones"] == []
