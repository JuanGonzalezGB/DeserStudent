"""
Pruebas del Paso 1 (validacion).

Cubren los cuatro motivos del contrato y las tres contradicciones, incluido el
caso A03 que quedo abierto en la entrega anterior.
"""

import pytest

import config
from modelo import validacion


# ------------------------------------------------- el registro de control --
def test_registro_valido_pasa(registro):
    resultado = validacion.validar(registro)
    assert resultado["decision"] == "valido"
    assert resultado["motivo"] is None
    assert resultado["campo"] is None


def test_es_valido_es_atajo_de_validar(registro):
    assert validacion.es_valido(registro) is True
    del registro["promedio"]
    assert validacion.es_valido(registro) is False


# ------------------------------------------------------ campo_faltante ----
@pytest.mark.parametrize("campo", config.CAMPOS_OBLIGATORIOS)
def test_campo_ausente_va_a_revision(registro, campo):
    """Ningun campo es opcional: faltar cualquiera manda el caso a revision."""
    del registro[campo]
    resultado = validacion.validar(registro)
    assert resultado["decision"] == "requiere_revision_humana"
    assert resultado["motivo"] == "campo_faltante"
    assert resultado["campo"] == campo


@pytest.mark.parametrize("campo", config.CAMPOS_OBLIGATORIOS)
def test_campo_en_none_va_a_revision(registro, campo):
    """None cuenta como vacio: el modelo nunca inventa el dato que falta."""
    registro[campo] = None
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "campo_faltante"
    assert resultado["campo"] == campo


def test_cadena_de_espacios_cuenta_como_vacio(registro):
    registro["promedio"] = "   "
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "campo_faltante"
    assert resultado["campo"] == "promedio"


# -------------------------------------------------------- tipo_invalido ---
@pytest.mark.parametrize("campo,valor", [
    ("promedio", "3.5"),
    ("asistencia_pct", "85"),
    ("ingreso_hogar_smmlv", "tres"),
    ("horas_trabajo_semana", [15]),
    ("semestre", 4.5),
    ("materias_perdidas", 1.0),
    ("estrato", "3"),
    ("saldo_pendiente_cop", 2_000_000.5),
    ("personas_a_cargo", 1.5),
    ("apoyo_familiar", "4"),
    ("tiempo_desplazamiento_min", 40.5),
])
def test_tipo_invalido_en_numericos(registro, campo, valor):
    registro[campo] = valor
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "tipo_invalido"
    assert resultado["campo"] == campo


@pytest.mark.parametrize("campo", config.CAMPOS_BOOLEANOS)
@pytest.mark.parametrize("valor", [1, 0, "true", "si"])
def test_booleanos_solo_aceptan_bool(registro, campo, valor):
    """1 y 0 NO son booleanos aqui: el tipo se exige estricto."""
    registro[campo] = valor
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "tipo_invalido"
    assert resultado["campo"] == campo


@pytest.mark.parametrize("campo", config.CAMPOS_ENTEROS)
def test_bool_no_sirve_como_entero(registro, campo):
    """bool es subclase de int en Python; se excluye a proposito."""
    registro[campo] = True
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "tipo_invalido"
    assert resultado["campo"] == campo


def test_entrada_que_no_es_dict(registro):
    for entrada in (None, [], "texto", 42):
        resultado = validacion.validar(entrada)
        assert resultado["decision"] == "requiere_revision_humana"
        assert resultado["motivo"] == "tipo_invalido"
        assert resultado["campo"] == "registro"


# ------------------------------------------------------- fuera_de_rango ---
@pytest.mark.parametrize("campo,valor", [
    ("promedio", 5.1),
    ("promedio", -0.1),
    ("materias_perdidas", 9),
    ("materias_perdidas", -1),
    ("asistencia_pct", 100.1),
    ("asistencia_pct", -1.0),
    ("semestre", 0),
    ("semestre", 13),
    ("saldo_pendiente_cop", 20_000_001),
    ("saldo_pendiente_cop", -1),
    ("ingreso_hogar_smmlv", 20.1),
    ("ingreso_hogar_smmlv", -0.5),
    ("estrato", 0),
    ("estrato", 7),
    ("horas_trabajo_semana", 60.1),
    ("horas_trabajo_semana", -1.0),
    ("tiempo_desplazamiento_min", 241),
    ("tiempo_desplazamiento_min", -1),
    ("personas_a_cargo", 7),
    ("personas_a_cargo", -1),
    ("apoyo_familiar", 0),
    ("apoyo_familiar", 6),
])
def test_fuera_de_rango(registro, campo, valor):
    registro[campo] = valor
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "fuera_de_rango"
    assert resultado["campo"] == campo


@pytest.mark.parametrize("campo", list(config.RANGOS))
def test_los_bordes_exactos_son_validos(registro, campo):
    """Los rangos son cerrados: el minimo y el maximo exactos pasan."""
    minimo, maximo = config.RANGOS[campo]
    for borde in (minimo, maximo):
        prueba = dict(registro)
        prueba[campo] = borde
        # El borde promedio=5.0 choca con materias_perdidas=1 por contrato:
        # esa combinacion se prueba aparte, en los tests de contradiccion.
        if campo == "promedio" and borde == 5.0:
            prueba["materias_perdidas"] = 0
        # estrato 1 o 2 con el ingreso base de 3.0 SMMLV es consistente;
        # estrato 5 o 6 tambien, porque 3.0 >= 1.
        resultado = validacion.validar(prueba)
        assert resultado["decision"] == "valido", (campo, borde, resultado)


# -------------------------------------------------- datos_contradictorios -
def test_contradiccion_estrato_alto_ingreso_bajo(registro):
    registro["estrato"] = 5
    registro["ingreso_hogar_smmlv"] = 0.8
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "datos_contradictorios"
    assert resultado["campo"] == "estrato_ingreso"


def test_contradiccion_estrato_bajo_ingreso_alto_caso_a03(registro):
    """Caso A03: el hueco del contrato anterior, ahora cerrado.

    En la entrega pasada este registro recibia un plan de apoyo financiero
    porque nadie verificaba la combinacion. Ahora va a revision humana.
    """
    registro["estrato"] = 2
    registro["ingreso_hogar_smmlv"] = 12.0
    resultado = validacion.validar(registro)
    assert resultado["decision"] == "requiere_revision_humana"
    assert resultado["motivo"] == "datos_contradictorios"
    assert resultado["campo"] == "estrato_ingreso"


def test_contradiccion_promedio_perfecto_con_materias_perdidas(registro):
    registro["promedio"] = 5.0
    registro["materias_perdidas"] = 2
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "datos_contradictorios"
    assert resultado["campo"] == "promedio_materias_perdidas"


@pytest.mark.parametrize("estrato,ingreso", [
    (5, 1.0),     # exactamente 1 SMMLV: no es contradiccion (la regla es < 1)
    (6, 1.0),
    (1, 10.0),    # exactamente 10 SMMLV: no es contradiccion (la regla es > 10)
    (2, 10.0),
    (4, 0.5),     # estrato 4 no entra en ninguna de las dos reglas
    (3, 15.0),
])
def test_bordes_de_las_contradicciones_no_disparan(registro, estrato, ingreso):
    """Los umbrales de contradiccion son estrictos, como dice el contrato."""
    registro["estrato"] = estrato
    registro["ingreso_hogar_smmlv"] = ingreso
    assert validacion.validar(registro)["decision"] == "valido"


def test_promedio_cinco_sin_perdidas_es_valido(registro):
    registro["promedio"] = 5.0
    registro["materias_perdidas"] = 0
    assert validacion.validar(registro)["decision"] == "valido"


# ------------------------------------------------------ orden y garantias -
def test_campo_faltante_gana_a_contradiccion(registro):
    """El orden del contrato: primero se mira que no falte nada."""
    registro["estrato"] = 6
    registro["ingreso_hogar_smmlv"] = 0.2   # contradiccion
    registro["promedio"] = None             # y ademas falta el promedio
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "campo_faltante"
    assert resultado["campo"] == "promedio"


def test_tipo_invalido_gana_a_fuera_de_rango(registro):
    registro["semestre"] = "99"             # tipo malo y valor fuera de rango
    assert validacion.validar(registro)["motivo"] == "tipo_invalido"


def test_fuera_de_rango_gana_a_contradiccion(registro):
    registro["estrato"] = 9                 # fuera de rango
    registro["ingreso_hogar_smmlv"] = 0.1   # y contradictorio con estrato alto
    resultado = validacion.validar(registro)
    assert resultado["motivo"] == "fuera_de_rango"
    assert resultado["campo"] == "estrato"


def test_todo_motivo_esta_en_la_lista_del_contrato(registro):
    """Garantia: validar nunca devuelve un motivo fuera del contrato."""
    casos = [
        {"promedio": None},
        {"promedio": "x"},
        {"promedio": 9.0},
        {"estrato": 6, "ingreso_hogar_smmlv": 0.1},
        {"tiene_apoyo_financiero": 1},
    ]
    for cambios in casos:
        prueba = dict(registro)
        prueba.update(cambios)
        resultado = validacion.validar(prueba)
        assert resultado["decision"] == "requiere_revision_humana"
        assert resultado["motivo"] in validacion.MOTIVOS
        assert resultado["mensaje"]          # siempre explica el rechazo
