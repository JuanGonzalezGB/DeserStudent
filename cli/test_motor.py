"""Pruebas unitarias del motor. Ejecutar con: pytest -v"""

import json
from pathlib import Path

import pytest

from ejecutar_pruebas import comparar, main
from motor import ejecutar_paso1, ejecutar_paso2, ejecutar_paso3, procesar_estudiante

AQUI = Path(__file__).parent


def perfil(**cambios):
    base = {
        "id_estudiante": "EST-0001", "nivel": "pregrado", "matriculado": True,
        "semestre": 4, "promedio": 3.8, "materias_inscritas": 5, "materias_perdidas": 0,
        "saldo_pendiente": 1_500_000, "ingreso_hogar_smmlv": 3.0, "estrato": 3,
        "distancia_km": 6.0, "solicita": "ambos",
    }
    base.update(cambios)
    return base


def sin(campo):
    p = perfil()
    del p[campo]
    return p


def s1(entrada):
    return procesar_estudiante(entrada)["S1"]


# ---------------------------------------------------------- casos típicos --
def test_caso_tipico_riesgo_alto_completo():
    r = procesar_estudiante(perfil(promedio=3.2, materias_perdidas=1, saldo_pendiente=2_400_000,
                                   ingreso_hogar_smmlv=1.5, estrato=2, distancia_km=12))
    assert r["S1"] == "valido"
    assert r["S2"] == {"riesgo_financiero": "alto", "riesgo_academico": "medio"}
    assert r["S3"] == {"decision": "plan", "cuotas": 4, "beca_alimentacion": True,
                       "bono_transporte": True, "tutoria": "academica"}


def test_estudiante_al_dia_solo_orientacion():
    r = procesar_estudiante(perfil(promedio=4.1, saldo_pendiente=0, ingreso_hogar_smmlv=5,
                                   estrato=4, solicita="tutoria"))
    assert r["S2"] == {"riesgo_financiero": "bajo", "riesgo_academico": "bajo"}
    assert r["S3"]["cuotas"] == 0 and r["S3"]["tutoria"] == "orientacion"


def test_tutoria_prioritaria_aunque_no_la_pida():
    r = procesar_estudiante(perfil(promedio=2.5, solicita="financiero"))
    assert r["S3"]["tutoria"] == "academica_prioritaria"


def test_solo_tutoria_no_recibe_beneficios_financieros():
    r = procesar_estudiante(perfil(ingreso_hogar_smmlv=1.0, solicita="tutoria"))
    assert (r["S3"]["cuotas"], r["S3"]["beca_alimentacion"], r["S3"]["bono_transporte"]) == (0, False, False)


# ------------------------------------------------------------ bordes -------
@pytest.mark.parametrize("ingreso, esperado", [(2.0, "alto"), (2.01, "medio"), (4.0, "medio"), (4.01, "bajo")])
def test_umbrales_de_ingreso(ingreso, esperado):
    assert ejecutar_paso2(perfil(ingreso_hogar_smmlv=ingreso, estrato=3))["riesgo_financiero"] == esperado


@pytest.mark.parametrize("estrato, esperado", [(2, "alto"), (3, "medio")])
def test_umbral_de_estrato(estrato, esperado):
    assert ejecutar_paso2(perfil(estrato=estrato, ingreso_hogar_smmlv=3.0))["riesgo_financiero"] == esperado


@pytest.mark.parametrize("promedio, perdidas, esperado", [
    (2.99, 0, "alto"), (3.0, 0, "medio"), (3.49, 0, "medio"), (3.5, 0, "bajo"),
    (4.5, 1, "medio"), (4.5, 2, "alto"),
])
def test_umbrales_academicos(promedio, perdidas, esperado):
    p = perfil(promedio=promedio, materias_perdidas=perdidas)
    assert ejecutar_paso2(p)["riesgo_academico"] == esperado


@pytest.mark.parametrize("distancia, bono", [(4.99, False), (5.0, True)])
def test_umbral_de_distancia(distancia, bono):
    assert procesar_estudiante(perfil(distancia_km=distancia))["S3"]["bono_transporte"] is bono


def test_saldo_de_un_peso_cuenta_como_deuda():
    assert ejecutar_paso2(perfil(saldo_pendiente=1))["riesgo_financiero"] == "medio"


def test_saldo_cero_riesgo_bajo():
    r = procesar_estudiante(perfil(saldo_pendiente=0, ingreso_hogar_smmlv=1.0, estrato=1, solicita="financiero"))
    assert r["S2"]["riesgo_financiero"] == "bajo" and r["S3"]["cuotas"] == 0


def test_perdidas_igual_a_inscritas_es_valido():
    assert s1(perfil(materias_inscritas=8, materias_perdidas=8, promedio=1.2)) == "valido"


@pytest.mark.parametrize("campo, valor", [
    ("semestre", 1), ("semestre", 12), ("promedio", 0.0), ("promedio", 5.0),
    ("saldo_pendiente", 20_000_000), ("ingreso_hogar_smmlv", 20.0), ("distancia_km", 100.0),
])
def test_limites_de_rango_incluidos(campo, valor):
    assert s1(perfil(**{campo: valor})) == "valido"


# --------------------------------------------------------- semestre 1 ------
def test_semestre_1_sin_promedio_es_valido():
    r = procesar_estudiante(perfil(semestre=1, promedio=None, ingreso_hogar_smmlv=1.8, estrato=2, distancia_km=2))
    assert r["S1"] == "valido"
    assert r["S2"]["riesgo_academico"] == "sin_datos"
    assert r["S3"]["tutoria"] == "orientacion"


def test_semestre_2_sin_promedio_se_abstiene():
    assert s1(perfil(semestre=2, promedio=None)) == {"decision": "abstener", "motivo": "campo_faltante", "campo": "promedio"}


# ------------------------------------------------------- nulos / faltantes --
@pytest.mark.parametrize("campo", ["id_estudiante", "nivel", "matriculado", "semestre", "promedio",
                                   "materias_inscritas", "materias_perdidas", "saldo_pendiente",
                                   "ingreso_hogar_smmlv", "estrato", "distancia_km", "solicita"])
def test_campo_ausente_se_abstiene(campo):
    assert s1(sin(campo)) == {"decision": "abstener", "motivo": "campo_faltante", "campo": campo}


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_id_vacio_se_abstiene(valor):
    assert s1(perfil(id_estudiante=valor))["motivo"] == "campo_faltante"


# ------------------------------------------------------- inyección de tipos --
@pytest.mark.parametrize("campo, valor", [
    ("promedio", "tres punto cinco"), ("promedio", "3.5"), ("semestre", "primer semestre"),
    ("semestre", 4.0), ("semestre", True), ("estrato", False), ("materias_inscritas", 5.5),
    ("saldo_pendiente", "1500000"), ("matriculado", "true"), ("matriculado", 1),
    ("distancia_km", [6]), ("solicita", 3), ("id_estudiante", 1021), ("nivel", None),
])
def test_tipo_invalido_es_error_controlado(campo, valor):
    r = s1(perfil(**{campo: valor}))
    assert r["decision"] in ("error", "abstener")      # None en nivel es faltante; el resto es tipo inválido
    if valor is not None:
        assert r == {"decision": "error", "motivo": "tipo_invalido", "campo": campo}


def test_entrada_que_no_es_dict():
    assert procesar_estudiante("hola")["S1"]["motivo"] == "tipo_invalido"


def test_nunca_lanza_excepcion():
    for basura in (None, [], 42, {"x": 1}, perfil(promedio=float("nan"))):
        r = procesar_estudiante(basura)
        assert set(r) == {"S1", "S2", "S3"}


# ------------------------------------------------------------ fuera de rango --
@pytest.mark.parametrize("campo, valor", [
    ("promedio", 7.5), ("promedio", -0.1), ("saldo_pendiente", -500_000), ("saldo_pendiente", 95_000_000),
    ("semestre", 0), ("semestre", 14), ("materias_inscritas", 0), ("materias_inscritas", 9),
    ("estrato", 7), ("distancia_km", -5.0), ("ingreso_hogar_smmlv", -1.0), ("ingreso_hogar_smmlv", 25.0),
    ("promedio", float("nan")),
])
def test_fuera_de_rango(campo, valor):
    assert s1(perfil(**{campo: valor})) == {"decision": "error", "motivo": "fuera_de_rango", "campo": campo}


def test_solicitud_no_permitida():
    assert s1(perfil(solicita="beca_completa"))["motivo"] == "valor_no_permitido"


# ------------------------------------------------------------- contradicciones --
def test_perdidas_mayores_que_inscritas():
    assert s1(perfil(materias_inscritas=3, materias_perdidas=5))["motivo"] == "datos_contradictorios"


def test_estrato_alto_con_ingreso_minimo():
    assert s1(perfil(estrato=6, ingreso_hogar_smmlv=0.3))["motivo"] == "datos_contradictorios"


# --------------------------------------------------------------- población --
@pytest.mark.parametrize("nivel", ["posgrado", "doctorado", "extension"])
def test_otra_poblacion(nivel):
    assert s1(perfil(nivel=nivel)) == {"decision": "abstener", "motivo": "fuera_de_poblacion", "campo": "nivel"}


@pytest.mark.parametrize("nivel", ["Pregrado", "  PREGRADO  "])
def test_nivel_ignora_mayusculas_y_espacios(nivel):
    assert s1(perfil(nivel=nivel)) == "valido"


def test_no_matriculado():
    assert s1(perfil(matriculado=False))["motivo"] == "fuera_de_poblacion"


# ------------------------------------------------------------- cortocircuito --
@pytest.mark.parametrize("entrada", [perfil(matriculado=False), perfil(promedio=7.5), sin("solicita")])
def test_cortocircuito_si_s1_no_es_valido(entrada):
    r = procesar_estudiante(entrada)
    assert r["S1"] != "valido" and r["S2"] is None and r["S3"] is None


def test_paso3_directo():
    s3 = ejecutar_paso3(perfil(distancia_km=10), {"riesgo_financiero": "alto", "riesgo_academico": "bajo"})
    assert s3 == {"decision": "plan", "cuotas": 4, "beca_alimentacion": True,
                  "bono_transporte": True, "tutoria": "orientacion"}


# ------------------------------------------------------------------- CLI -----
def test_cli_dataset_de_ejemplo_pasa_completo(tmp_path):
    salida = tmp_path / "res.csv"
    codigo = main(["--dataset", str(AQUI / "03_dataset_ejemplo.json"),
                   "--oraculo", str(AQUI / "04_oraculo_ejemplo.json"), "--salida", str(salida)])
    assert codigo == 0 and salida.exists()


def test_comparar_detecta_diferencias_en_s2():
    esperado = {"S1": "valido", "S2": {"riesgo_financiero": "alto", "riesgo_academico": "bajo"}, "S3": None}
    obtenido = {"S1": "valido", "S2": {"riesgo_financiero": "medio", "riesgo_academico": "bajo"}, "S3": None}
    assert any("S2.riesgo_financiero" in d for d in comparar(esperado, obtenido))
