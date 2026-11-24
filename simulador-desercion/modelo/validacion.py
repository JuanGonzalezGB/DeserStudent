"""
Paso 1 del simulador: validar el registro del estudiante.

Reusa la filosofia del contrato de la entrega anterior
(practica-pruebas-estres/01_contrato.md):

  - Nunca lanza una excepcion: toda entrada termina en "valido" o en
    "requiere_revision_humana" con un motivo.
  - Nunca inventa datos que faltan.
  - Un registro invalido NO recibe probabilidad de desercion: se remite a un
    asesor humano del comite de apoyo.

Orden de evaluacion (el primero que aplique gana), igual que en motor.py:

  1. campo_faltante       -> falta un campo obligatorio o viene vacio
  2. tipo_invalido        -> el tipo no corresponde (texto donde va numero, etc.)
  3. fuera_de_rango       -> el valor no cabe en el rango del contrato
  4. datos_contradictorios -> la combinacion de valores es imposible

El motivo "datos_contradictorios" incluye el hueco A03 que quedo abierto en la
entrega anterior (estrato <= 2 con ingreso > 10 SMMLV): aqui ya esta cerrado.
"""

import math
from numbers import Real

import config

MOTIVOS = ("campo_faltante", "tipo_invalido", "fuera_de_rango",
           "datos_contradictorios")


def _valido():
    return {"decision": "valido", "motivo": None, "campo": None, "mensaje": ""}


def _revision(motivo, campo, mensaje):
    """Resultado terminal: el caso va a revision humana."""
    return {"decision": "requiere_revision_humana", "motivo": motivo,
            "campo": campo, "mensaje": mensaje}


def _es_entero(valor):
    # bool es subclase de int en Python: se excluye a proposito.
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_numero(valor):
    return isinstance(valor, Real) and not isinstance(valor, bool)


def _vacio(valor):
    return valor is None or (isinstance(valor, str) and valor.strip() == "")


def validar(registro):
    """Valida un registro de estudiante. Devuelve siempre un dict, nunca lanza.

    Claves del resultado: decision, motivo, campo, mensaje.
    decision es "valido" o "requiere_revision_humana".
    """
    if not isinstance(registro, dict):
        return _revision("tipo_invalido", "registro",
                         "el registro no es un objeto con campos")

    # --- 1. Campos faltantes o vacios -------------------------------------
    # Ningun campo es opcional: no se asume promedio 0 ni saldo 0.
    for campo in config.CAMPOS_OBLIGATORIOS:
        if campo not in registro or _vacio(registro[campo]):
            return _revision("campo_faltante", campo,
                             "falta el campo obligatorio '%s'" % campo)

    # --- 2. Tipos estrictos -----------------------------------------------
    for campo in config.CAMPOS_BOOLEANOS:
        if not isinstance(registro[campo], bool):
            return _revision("tipo_invalido", campo,
                             "'%s' debe ser booleano" % campo)

    for campo in config.CAMPOS_ENTEROS:
        if not _es_entero(registro[campo]):
            return _revision("tipo_invalido", campo,
                             "'%s' debe ser un entero" % campo)

    for campo in config.CAMPOS_DECIMALES:
        if not _es_numero(registro[campo]):
            return _revision("tipo_invalido", campo,
                             "'%s' debe ser numerico" % campo)
        # NaN e infinito son float, pero no son numeros usables: NaN hace
        # falsas TODAS las comparaciones, asi que colarse aqui le permitiria
        # pasar la prueba de rango y envenenar la probabilidad con un NaN.
        # Lo encontro test_estres.py.
        if not math.isfinite(float(registro[campo])):
            return _revision("tipo_invalido", campo,
                             "'%s' no es un numero finito (%r)"
                             % (campo, registro[campo]))

    # --- 3. Rangos (bordes inclusivos) ------------------------------------
    for campo, (minimo, maximo) in config.RANGOS.items():
        valor = registro[campo]
        if valor < minimo or valor > maximo:
            return _revision("fuera_de_rango", campo,
                             "'%s' = %r fuera del rango [%s, %s]"
                             % (campo, valor, minimo, maximo))

    # --- 4. Contradicciones ------------------------------------------------
    estrato = registro["estrato"]
    ingreso = registro["ingreso_hogar_smmlv"]
    perdidas = registro["materias_perdidas"]
    promedio = registro["promedio"]

    if estrato >= 5 and ingreso < 1:
        return _revision("datos_contradictorios", "estrato_ingreso",
                         "estrato %d con ingreso de %s SMMLV (menor a 1)"
                         % (estrato, ingreso))

    # Hueco A03 de la entrega anterior, ahora cerrado.
    if estrato <= 2 and ingreso > 10:
        return _revision("datos_contradictorios", "estrato_ingreso",
                         "estrato %d con ingreso de %s SMMLV (mayor a 10)"
                         % (estrato, ingreso))

    if perdidas > 0 and promedio == 5.0:
        return _revision("datos_contradictorios", "promedio_materias_perdidas",
                         "promedio 5.0 con %d materias perdidas" % perdidas)

    return _valido()


def es_valido(registro):
    """Atajo booleano para filtros y pruebas."""
    return validar(registro)["decision"] == "valido"
