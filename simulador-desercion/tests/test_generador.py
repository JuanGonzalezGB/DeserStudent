"""
Pruebas del generador de la cohorte sintetica (Montecarlo de muestreo).

Lo que importa comprobar:
  - reproducibilidad: la misma semilla da exactamente la misma cohorte;
  - los registros sanos respetan el contrato de la entrada E;
  - el azar NO produce contradicciones por accidente;
  - el 3% de registros danados a proposito existe y el Paso 1 los atrapa;
  - las dependencias declaradas (ingreso-estrato, horas-ingreso,
    asistencia-horas, promedio-asistencia) aparecen de verdad en los datos.
"""

import pytest

import config
from modelo import generador, validacion


# --------------------------------------------------- reproducibilidad ----
def test_misma_semilla_misma_cohorte():
    a = generador.generar_cohorte(n=200, semilla=42)
    b = generador.generar_cohorte(n=200, semilla=42)
    assert a == b


def test_semillas_distintas_dan_cohortes_distintas():
    a = generador.generar_cohorte(n=200, semilla=42)
    b = generador.generar_cohorte(n=200, semilla=43)
    assert a != b


def test_el_tamano_es_el_pedido():
    for n in (1, 10, 137, 500):
        assert len(generador.generar_cohorte(n=n, semilla=5)) == n


def test_codigos_unicos_y_con_formato():
    cohorte = generador.generar_cohorte(n=300, semilla=9)
    codigos = [c["codigo"] for c in cohorte]
    assert len(set(codigos)) == len(codigos)
    assert codigos[0] == "UNA-0001"
    assert codigos[299] == "UNA-0300"


def test_valores_por_defecto_vienen_de_config():
    cohorte = generador.generar_cohorte()
    esperada = generador.generar_cohorte(n=config.N_POR_DEFECTO,
                                         semilla=config.SEMILLA_POR_DEFECTO)
    assert len(cohorte) == config.N_POR_DEFECTO
    assert cohorte == esperada


# ------------------------------------------------- contrato de la entrada -
def test_todos_los_registros_traen_todos_los_campos():
    cohorte = generador.generar_cohorte(n=300, semilla=13)
    for item in cohorte:
        if item["error_inyectado"] == "campo_vacio":
            continue        # a este se le quito un campo a proposito
        for campo in config.CAMPOS_OBLIGATORIOS:
            assert campo in item["datos"], (item["codigo"], campo)


def test_los_registros_sanos_son_validos_y_estan_en_rango():
    cohorte = generador.generar_cohorte(n=1000, semilla=21)
    sanos = [c for c in cohorte if c["error_inyectado"] is None]
    assert len(sanos) > 900

    for item in sanos:
        datos = item["datos"]
        veredicto = validacion.validar(datos)
        assert veredicto["decision"] == "valido", (item["codigo"], veredicto)
        for campo, (minimo, maximo) in config.RANGOS.items():
            assert minimo <= datos[campo] <= maximo, (item["codigo"], campo)


def test_los_tipos_son_los_del_contrato():
    cohorte = generador.generar_cohorte(n=300, semilla=4)
    for item in cohorte:
        if item["error_inyectado"] is not None:
            continue
        datos = item["datos"]
        for campo in config.CAMPOS_ENTEROS:
            assert isinstance(datos[campo], int)
            assert not isinstance(datos[campo], bool)
        for campo in config.CAMPOS_BOOLEANOS:
            assert isinstance(datos[campo], bool)
        for campo in config.CAMPOS_DECIMALES:
            assert isinstance(datos[campo], float)


def test_el_azar_no_crea_contradicciones():
    """Los topes anti-contradiccion de config.py hacen su trabajo.

    Las contradicciones solo deben aparecer en los registros danados a
    proposito, nunca por azar.
    """
    cohorte = generador.generar_cohorte(n=2000, semilla=77)
    for item in cohorte:
        if item["error_inyectado"] is not None:
            continue
        datos = item["datos"]
        assert not (datos["estrato"] >= 5 and datos["ingreso_hogar_smmlv"] < 1)
        assert not (datos["estrato"] <= 2 and datos["ingreso_hogar_smmlv"] > 10)
        assert not (datos["materias_perdidas"] > 0 and datos["promedio"] == 5.0)


# -------------------------------------------- errores inyectados a mano --
def test_hay_aproximadamente_un_tres_por_ciento_de_errores():
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    danados = [c for c in cohorte if c["error_inyectado"] is not None]
    assert len(danados) == round(500 * config.PCT_REGISTROS_CON_ERROR)
    assert len(danados) == 15


def test_el_paso_1_atrapa_todos_los_registros_danados():
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    for item in cohorte:
        if item["error_inyectado"] is None:
            continue
        veredicto = validacion.validar(item["datos"])
        assert veredicto["decision"] == "requiere_revision_humana", item["codigo"]


def test_aparecen_los_tres_tipos_de_error():
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    tipos = {c["error_inyectado"] for c in cohorte
             if c["error_inyectado"] is not None}
    assert tipos == set(config.TIPOS_DE_ERROR_INYECTADO)


def test_cada_tipo_de_error_produce_el_motivo_que_le_toca():
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    esperado = {
        "campo_vacio": "campo_faltante",
        "fuera_de_rango": "fuera_de_rango",
        "contradiccion": "datos_contradictorios",
    }
    vistos = set()
    for item in cohorte:
        tipo = item["error_inyectado"]
        if tipo is None:
            continue
        motivo = validacion.validar(item["datos"])["motivo"]
        assert motivo == esperado[tipo], (item["codigo"], tipo, motivo)
        vistos.add(tipo)
    assert vistos == set(esperado)


def test_las_contradicciones_inyectadas_incluyen_el_caso_a03():
    """Entre los registros danados tiene que estar el hueco A03.

    A03 = estrato bajo (<= 2) con ingreso alto (> 10 SMMLV).
    """
    cohorte = generador.generar_cohorte(n=500, semilla=42)
    a03 = [c for c in cohorte
           if c["error_inyectado"] == "contradiccion"
           and c["datos"]["estrato"] <= 2
           and c["datos"]["ingreso_hogar_smmlv"] > 10]
    assert a03, "ninguna contradiccion inyectada reproduce el caso A03"


def test_sin_errores_si_el_porcentaje_es_cero():
    cohorte = generador.generar_cohorte(n=100, semilla=1, pct_error=0.0)
    assert all(c["error_inyectado"] is None for c in cohorte)
    assert all(validacion.es_valido(c["datos"]) for c in cohorte)


# ------------------------------------------------------- dependencias ---
def _promedio(valores):
    return sum(valores) / len(valores)


def test_el_ingreso_sube_con_el_estrato():
    cohorte = generador.generar_cohorte(n=3000, semilla=101, pct_error=0.0)
    por_estrato = {}
    for item in cohorte:
        datos = item["datos"]
        por_estrato.setdefault(datos["estrato"], []).append(
            datos["ingreso_hogar_smmlv"])

    medias = {e: _promedio(v) for e, v in sorted(por_estrato.items())}
    estratos = sorted(medias)
    for bajo, alto in zip(estratos, estratos[1:]):
        assert medias[bajo] < medias[alto], (bajo, alto, medias)


def test_quien_tiene_menos_ingreso_trabaja_mas_horas():
    cohorte = generador.generar_cohorte(n=3000, semilla=102, pct_error=0.0)
    bajos = [c["datos"]["horas_trabajo_semana"] for c in cohorte
             if c["datos"]["ingreso_hogar_smmlv"] <= 2]
    altos = [c["datos"]["horas_trabajo_semana"] for c in cohorte
             if c["datos"]["ingreso_hogar_smmlv"] >= 6]
    assert bajos and altos
    assert _promedio(bajos) > _promedio(altos)


def test_la_asistencia_baja_cuando_hay_muchas_horas_de_trabajo():
    cohorte = generador.generar_cohorte(n=3000, semilla=103, pct_error=0.0)
    pocas = [c["datos"]["asistencia_pct"] for c in cohorte
             if c["datos"]["horas_trabajo_semana"] <= 5]
    muchas = [c["datos"]["asistencia_pct"] for c in cohorte
              if c["datos"]["horas_trabajo_semana"] >= 35]
    assert pocas and muchas
    assert _promedio(pocas) > _promedio(muchas)


def test_el_promedio_sube_con_la_asistencia():
    cohorte = generador.generar_cohorte(n=3000, semilla=104, pct_error=0.0)
    baja = [c["datos"]["promedio"] for c in cohorte
            if c["datos"]["asistencia_pct"] <= 75]
    alta = [c["datos"]["promedio"] for c in cohorte
            if c["datos"]["asistencia_pct"] >= 92]
    assert baja and alta
    assert _promedio(baja) < _promedio(alta)


def test_se_pierden_mas_materias_cuando_el_promedio_es_bajo():
    cohorte = generador.generar_cohorte(n=3000, semilla=105, pct_error=0.0)
    bajo = [c["datos"]["materias_perdidas"] for c in cohorte
            if c["datos"]["promedio"] <= 3.5]
    alto = [c["datos"]["materias_perdidas"] for c in cohorte
            if c["datos"]["promedio"] >= 4.5]
    assert bajo and alto
    assert _promedio(bajo) > _promedio(alto)


def test_el_estrato_bajo_pesa_mas_en_la_cohorte():
    """La distribucion de estrato carga hacia 1-3, como dice config.py."""
    cohorte = generador.generar_cohorte(n=3000, semilla=106, pct_error=0.0)
    bajos = sum(1 for c in cohorte if c["datos"]["estrato"] <= 3)
    assert bajos / len(cohorte) > 0.5


@pytest.mark.parametrize("semilla", [1, 42, 999])
def test_el_poisson_de_materias_perdidas_respeta_el_tope(semilla):
    cohorte = generador.generar_cohorte(n=1000, semilla=semilla, pct_error=0.0)
    maximo = config.RANGOS["materias_perdidas"][1]
    for item in cohorte:
        assert 0 <= item["datos"]["materias_perdidas"] <= maximo
