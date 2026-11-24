"""
Pruebas del Paso 2 (riesgo): subpuntajes, probabilidad logistica y calibracion.

Lo que se garantiza aqui es lo que hace defendible el modelo:
  - los subpuntajes siempre caen en [0, 1];
  - p siempre cae en [0, 1];
  - empeorar una variable nunca baja p (monotonia);
  - la probabilidad media de la cohorte coincide con la tasa base (+-0.005).
"""

import math

import pytest

import config
from modelo import generador, riesgo, sensibilidad, validacion


# ------------------------------------------------------ la logistica -----
@pytest.mark.parametrize("z", [-800, -50, -1, 0, 1, 50, 800])
def test_logistica_no_desborda_y_queda_en_cero_uno(z):
    valor = riesgo.logistica(z)
    assert 0.0 <= valor <= 1.0


def test_logistica_en_cero_es_un_medio():
    assert riesgo.logistica(0) == pytest.approx(0.5)


def test_logistica_es_creciente():
    valores = [riesgo.logistica(z) for z in range(-20, 21)]
    assert all(b >= a for a, b in zip(valores, valores[1:]))


# ------------------------------------------------------- subpuntajes ----
def test_subpuntajes_en_rango_para_el_registro_base(registro):
    s = riesgo.subpuntajes(registro)
    assert set(s) == set(config.DIMENSIONES)
    for dim, valor in s.items():
        assert 0.0 <= valor <= 1.0, (dim, valor)


def test_subpuntajes_en_rango_para_toda_la_cohorte():
    """Mil estudiantes muestreados: ningun subpuntaje se sale de [0, 1]."""
    cohorte = generador.generar_cohorte(n=1000, semilla=7)
    for item in cohorte:
        if not validacion.es_valido(item["datos"]):
            continue
        for dim, valor in riesgo.subpuntajes(item["datos"]).items():
            assert 0.0 <= valor <= 1.0, (item["codigo"], dim, valor)


def test_perfil_sin_riesgo_da_subpuntajes_casi_cero():
    perfil = {
        "promedio": 5.0, "materias_perdidas": 0, "asistencia_pct": 100.0,
        "semestre": 1,
        "saldo_pendiente_cop": 0, "ingreso_hogar_smmlv": 20.0, "estrato": 6,
        "tiene_apoyo_financiero": True,
        "horas_trabajo_semana": 0.0, "trabaja_en_area_de_estudio": True,
        "tiempo_desplazamiento_min": 0, "personas_a_cargo": 0,
        "apoyo_familiar": 5, "primera_generacion_universitaria": False,
    }
    assert validacion.es_valido(perfil)
    for dim, valor in riesgo.subpuntajes(perfil).items():
        assert valor == pytest.approx(0.0), (dim, valor)


def test_perfil_de_riesgo_maximo_da_subpuntajes_uno():
    perfil = {
        "promedio": 0.0, "materias_perdidas": 8, "asistencia_pct": 0.0,
        "semestre": 6,
        "saldo_pendiente_cop": 20_000_000, "ingreso_hogar_smmlv": 0.0,
        "estrato": 1, "tiene_apoyo_financiero": False,
        "horas_trabajo_semana": 60.0, "trabaja_en_area_de_estudio": False,
        "tiempo_desplazamiento_min": 240, "personas_a_cargo": 6,
        "apoyo_familiar": 1, "primera_generacion_universitaria": True,
    }
    assert validacion.es_valido(perfil)
    for dim, valor in riesgo.subpuntajes(perfil).items():
        assert valor == pytest.approx(1.0), (dim, valor)


def test_los_pesos_de_cada_dimension_suman_uno():
    """Es lo que garantiza que s_d no pueda pasarse de 1."""
    for pesos in (config.PESOS_ACADEMICA, config.PESOS_FINANCIERA,
                  config.PESOS_LABORAL, config.PESOS_PERSONAL):
        assert sum(pesos.values()) == pytest.approx(1.0)


def test_quien_no_trabaja_no_tiene_riesgo_laboral(registro):
    """Sin horas de trabajo, 'no trabaja en su area' no debe penalizar."""
    registro["horas_trabajo_semana"] = 0.0
    registro["trabaja_en_area_de_estudio"] = False
    assert riesgo.subpuntaje_laboral(registro) == pytest.approx(0.0)


def test_formula_academica_documentada(registro):
    """El subpuntaje academico se puede recalcular a mano, como en los docs."""
    registro["promedio"] = 2.5
    registro["materias_perdidas"] = 2
    registro["asistencia_pct"] = 70.0
    esperado = (0.4 * (1 - 2.5 / 5)
                + 0.3 * min(2 / 3, 1)
                + 0.3 * (1 - 70.0 / 100))
    assert riesgo.subpuntaje_academico(registro) == pytest.approx(esperado)


# ------------------------------------------------------ probabilidad ----
def test_p_en_rango_para_toda_la_cohorte():
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    validos = [c["datos"] for c in cohorte if validacion.es_valido(c["datos"])]
    lista_s = [riesgo.subpuntajes(d) for d in validos]
    b0 = riesgo.calibrar_b0(lista_s)
    for s in lista_s:
        p = riesgo.probabilidad(s, b0)
        assert 0.0 <= p <= 1.0


@pytest.mark.parametrize("b0", [-50.0, -5.0, 0.0, 5.0, 50.0])
def test_p_en_rango_con_cualquier_b0(registro, b0):
    p = riesgo.probabilidad(riesgo.subpuntajes(registro), b0)
    assert 0.0 <= p <= 1.0


def test_la_formula_logistica_es_la_documentada(registro):
    s = riesgo.subpuntajes(registro)
    b0 = -4.9
    c = config.COEFICIENTES
    logit = (b0 + c["academica"] * s["academica"]
             + c["financiera"] * s["financiera"]
             + c["laboral"] * s["laboral"]
             + c["personal"] * s["personal"])
    esperado = 1 / (1 + math.exp(-logit))
    assert riesgo.probabilidad(s, b0) == pytest.approx(esperado)


# -------------------------------------------------------- monotonia -----
@pytest.mark.parametrize("campo", list(sensibilidad.PASOS_MONOTONIA))
def test_monotonia_por_variable(campo):
    """Empeorar la variable nunca debe bajar p, en ninguno de sus pasos."""
    pasos = sensibilidad.PASOS_MONOTONIA[campo]
    b0 = -4.95
    anterior = None
    for valor in pasos:
        prueba = dict(sensibilidad.REGISTRO_BASE_MONOTONIA)
        prueba[campo] = valor
        # Todos los pasos tienen que seguir siendo registros validos: si no,
        # la prueba de monotonia estaria midiendo basura.
        assert validacion.es_valido(prueba), (campo, valor)
        p = riesgo.probabilidad(riesgo.subpuntajes(prueba), b0)
        if anterior is not None:
            assert p >= anterior - 1e-12, (campo, valor, anterior, p)
        anterior = p


def test_monotonia_estricta_en_las_variables_con_peso(registro):
    """Para estas variables el cambio no solo no baja p: la sube de verdad."""
    b0 = -4.95
    base = riesgo.probabilidad(riesgo.subpuntajes(registro), b0)
    empeoramientos = {
        "promedio": 1.0,
        "materias_perdidas": 3,
        "asistencia_pct": 40.0,
        "saldo_pendiente_cop": 18_000_000,
        "ingreso_hogar_smmlv": 0.5,
        "estrato": 1,
        "horas_trabajo_semana": 50.0,
        "tiempo_desplazamiento_min": 200,
        "personas_a_cargo": 5,
        "apoyo_familiar": 1,
        "primera_generacion_universitaria": True,
    }
    for campo, valor in empeoramientos.items():
        prueba = dict(registro)
        prueba[campo] = valor
        assert validacion.es_valido(prueba), campo
        p = riesgo.probabilidad(riesgo.subpuntajes(prueba), b0)
        assert p > base, (campo, base, p)


def test_apoyo_financiero_baja_el_riesgo(registro):
    b0 = -4.95
    sin_apoyo = dict(registro, tiene_apoyo_financiero=False)
    con_apoyo = dict(registro, tiene_apoyo_financiero=True)
    p_sin = riesgo.probabilidad(riesgo.subpuntajes(sin_apoyo), b0)
    p_con = riesgo.probabilidad(riesgo.subpuntajes(con_apoyo), b0)
    assert p_con < p_sin


def test_trabajar_en_su_area_baja_el_riesgo_laboral(registro):
    registro["horas_trabajo_semana"] = 30.0
    fuera = dict(registro, trabaja_en_area_de_estudio=False)
    dentro = dict(registro, trabaja_en_area_de_estudio=True)
    assert riesgo.subpuntaje_laboral(dentro) < riesgo.subpuntaje_laboral(fuera)


# ------------------------------------------------------- calibracion ----
@pytest.mark.parametrize("tasa", [0.05, 0.09, 0.15, 0.30])
def test_calibracion_deja_la_media_en_la_tasa_base(tasa):
    """La prueba central: media de p == tasa_base +- 0.005."""
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    lista_s = [riesgo.subpuntajes(c["datos"]) for c in cohorte
               if validacion.es_valido(c["datos"])]
    b0 = riesgo.calibrar_b0(lista_s, tasa)
    ps = [riesgo.probabilidad(s, b0) for s in lista_s]
    media = sum(ps) / len(ps)
    assert abs(media - tasa) <= config.CALIBRACION_MARGEN_OK


def test_calibracion_con_cohorte_vacia_devuelve_el_logit_de_la_tasa():
    b0 = riesgo.calibrar_b0([], 0.09)
    assert b0 == pytest.approx(math.log(0.09 / 0.91))


def test_calibrar_b0_es_determinista():
    cohorte = generador.generar_cohorte(n=200, semilla=3)
    lista_s = [riesgo.subpuntajes(c["datos"]) for c in cohorte
               if validacion.es_valido(c["datos"])]
    assert riesgo.calibrar_b0(lista_s, 0.09) == riesgo.calibrar_b0(lista_s, 0.09)


def test_una_tasa_base_mayor_exige_un_b0_mayor():
    cohorte = generador.generar_cohorte(n=300, semilla=11)
    lista_s = [riesgo.subpuntajes(c["datos"]) for c in cohorte
               if validacion.es_valido(c["datos"])]
    assert riesgo.calibrar_b0(lista_s, 0.20) > riesgo.calibrar_b0(lista_s, 0.05)


# ------------------------------------- contribuciones, factor, niveles --
def test_contribucion_es_coeficiente_por_subpuntaje(registro):
    s = riesgo.subpuntajes(registro)
    contribs = riesgo.contribuciones(s)
    for dim in config.DIMENSIONES:
        assert contribs[dim] == pytest.approx(config.COEFICIENTES[dim] * s[dim])


def test_factor_principal_es_la_mayor_contribucion():
    contribs = {"academica": 0.3, "financiera": 2.1, "laboral": 0.5,
                "personal": 0.4}
    assert riesgo.factor_principal(contribs) == "financiera"


def test_problemas_son_las_dimensiones_sobre_el_umbral():
    s = {"academica": 0.59, "financiera": 0.60, "laboral": 0.95,
         "personal": 0.10}
    problemas = riesgo.problemas(s)
    # 0.60 exacto SI cuenta (el umbral es inclusivo); 0.59 no.
    assert problemas == ["laboral", "financiera"]


@pytest.mark.parametrize("p,esperado", [
    (0.0, "bajo"),
    (0.1499, "bajo"),
    (0.15, "medio"),        # borde exacto: ya es medio
    (0.20, "medio"),
    (0.3499, "medio"),
    (0.35, "alto"),         # borde exacto: ya es alto
    (1.0, "alto"),
])
def test_niveles_y_sus_bordes(p, esperado):
    assert riesgo.nivel(p) == esperado


def test_nivel_acepta_umbrales_propios():
    assert riesgo.nivel(0.25, umbral_medio=0.30, umbral_alto=0.60) == "bajo"
    assert riesgo.nivel(0.35, umbral_medio=0.30, umbral_alto=0.60) == "medio"
    assert riesgo.nivel(0.75, umbral_medio=0.30, umbral_alto=0.60) == "alto"


def test_evaluar_devuelve_el_paquete_completo(registro):
    resultado = riesgo.evaluar(registro, -4.95)
    assert set(resultado) == {"subpuntajes", "p", "nivel", "contribuciones",
                              "factor_principal", "problemas"}
    assert 0.0 <= resultado["p"] <= 1.0
    assert resultado["nivel"] in ("bajo", "medio", "alto")
    assert resultado["factor_principal"] in config.DIMENSIONES
