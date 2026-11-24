"""
Paso 2 del simulador: calcular el riesgo de desercion de un estudiante valido.

Dos niveles, a proposito:

  a) Subpuntaje por dimension s_d en [0, 1]: formulas transparentes, un
     promedio ponderado de variables normalizadas. Cualquiera puede
     recalcularlas a mano en la sustentacion.

  b) Probabilidad de desercion semestral, por REGRESION LOGISTICA:

         p = 1 / (1 + exp(-(b0 + bA*sA + bF*sF + bL*sL + bP*sP)))

     Los b_d son supuestos expertos (config.COEFICIENTES). b0 NO se inventa:
     se calibra por biseccion para que la probabilidad media de la cohorte
     sea igual a la tasa base de desercion semestral.

El modelo que EXPLICA el riesgo es la regresion logistica. Montecarlo solo
muestrea (la cohorte en generador.py y la incertidumbre en incertidumbre.py).

Las cuatro formulas de subpuntaje, con los pesos de config.py:

  sA = 0.40*(1 - promedio/5) + 0.30*min(perdidas/3, 1)
     + 0.30*(1 - asistencia/100)

  sF = 0.35*min(saldo/8.000.000, 1) + 0.30*(1 - min(ingreso/4, 1))
     + 0.20*((6 - estrato)/5) + 0.15*(0 si tiene apoyo, 1 si no)

  sL = 0.70*intensidad + 0.30*intensidad*(0 si trabaja en su area, 1 si no)
       con intensidad = min(horas/40, 1)

  sP = 0.30*min(desplazamiento/120, 1) + 0.25*min(personas_a_cargo/3, 1)
     + 0.30*((5 - apoyo_familiar)/4) + 0.15*(1 si primera generacion, 0 si no)

En las cuatro, los pesos suman 1.0 y cada componente esta en [0, 1], asi que
s_d queda garantizado en [0, 1]: 0 = sin riesgo, 1 = riesgo maximo.
"""

import math

import config


# ----------------------------------------------------------------- utiles --
def _recorte(valor, minimo=0.0, maximo=1.0):
    """Recorta a [minimo, maximo]. Blinda los subpuntajes contra el redondeo."""
    return max(minimo, min(maximo, valor))


def logistica(z):
    """1/(1+exp(-z)) sin desbordarse con z muy grande o muy pequeno."""
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    # Forma equivalente que evita exp() de un numero enorme.
    ez = math.exp(z)
    return ez / (1.0 + ez)


# ------------------------------------------------- 2a. SUBPUNTAJES s_d ----
def subpuntaje_academico(r):
    """Riesgo academico: promedio bajo, materias perdidas y poca asistencia."""
    w = config.PESOS_ACADEMICA
    maximo_promedio = config.RANGOS["promedio"][1]
    s = (w["promedio"] * (1 - r["promedio"] / maximo_promedio)
         + w["materias_perdidas"] * min(r["materias_perdidas"]
                                        / config.PERDIDAS_SATURACION, 1.0)
         + w["asistencia"] * (1 - r["asistencia_pct"] / 100.0))
    return _recorte(s)


def subpuntaje_financiero(r):
    """Riesgo financiero: deuda, ingreso bajo, estrato bajo y falta de apoyo."""
    w = config.PESOS_FINANCIERA
    estrato_min, estrato_max = config.RANGOS["estrato"]
    s = (w["saldo"] * min(r["saldo_pendiente_cop"]
                          / config.SALDO_SATURACION, 1.0)
         + w["ingreso"] * (1 - min(r["ingreso_hogar_smmlv"]
                                   / config.INGRESO_SATURACION, 1.0))
         + w["estrato"] * ((estrato_max - r["estrato"])
                           / (estrato_max - estrato_min))
         + w["sin_apoyo"] * (0.0 if r["tiene_apoyo_financiero"] else 1.0))
    return _recorte(s)


def subpuntaje_laboral(r):
    """Riesgo laboral: intensidad horaria y desalineacion con la carrera.

    La desalineacion se multiplica por la intensidad para que quien trabaja
    0 horas tenga subpuntaje 0: no se le puede penalizar por "no trabajar en
    su area" si no trabaja.
    """
    w = config.PESOS_LABORAL
    intensidad = min(r["horas_trabajo_semana"] / config.HORAS_SATURACION, 1.0)
    desalineado = 0.0 if r["trabaja_en_area_de_estudio"] else 1.0
    s = (w["intensidad"] * intensidad
         + w["desalineacion"] * intensidad * desalineado)
    return _recorte(s)


def subpuntaje_personal(r):
    """Riesgo personal: desplazamiento, personas a cargo, apoyo y 1a generacion."""
    w = config.PESOS_PERSONAL
    apoyo_min, apoyo_max = config.RANGOS["apoyo_familiar"]
    s = (w["desplazamiento"] * min(r["tiempo_desplazamiento_min"]
                                   / config.DESPLAZAMIENTO_SATURACION, 1.0)
         + w["personas_a_cargo"] * min(r["personas_a_cargo"]
                                       / config.PERSONAS_SATURACION, 1.0)
         + w["apoyo_familiar"] * ((apoyo_max - r["apoyo_familiar"])
                                  / (apoyo_max - apoyo_min))
         + w["primera_generacion"] * (1.0 if r["primera_generacion_universitaria"]
                                      else 0.0))
    return _recorte(s)


_CALCULADORAS = {
    "academica": subpuntaje_academico,
    "financiera": subpuntaje_financiero,
    "laboral": subpuntaje_laboral,
    "personal": subpuntaje_personal,
}


def subpuntajes(r):
    """Los cuatro subpuntajes del estudiante, todos en [0, 1]."""
    return {dim: _CALCULADORAS[dim](r) for dim in config.DIMENSIONES}


# --------------------------------------- 2b. PROBABILIDAD (LOGISTICA) ----
def combinacion_lineal(s, b0, coeficientes=None):
    """b0 + suma(b_d * s_d). Es el logit de la probabilidad."""
    coef = config.COEFICIENTES if coeficientes is None else coeficientes
    return b0 + sum(coef[dim] * s[dim] for dim in config.DIMENSIONES)


def probabilidad(s, b0, coeficientes=None):
    """Probabilidad de desercion semestral del estudiante. Siempre en (0, 1)."""
    return logistica(combinacion_lineal(s, b0, coeficientes))


def calibrar_b0(lista_subpuntajes, tasa_base=None, coeficientes=None):
    """Despeja b0 por BISECCION para que media(p) == tasa_base.

    La probabilidad media de la cohorte crece de forma monotona con b0, asi
    que la biseccion converge siempre. Devuelve el b0 calibrado.

    Si la cohorte valida esta vacia no hay nada que calibrar y se devuelve el
    logit de la tasa base (el b0 que haria que un estudiante con todos los
    subpuntajes en 0 tuviera exactamente esa probabilidad).
    """
    tasa = config.TASA_BASE_SEMESTRAL if tasa_base is None else tasa_base

    if not lista_subpuntajes:
        return math.log(tasa / (1 - tasa))

    def media(b0):
        total = sum(probabilidad(s, b0, coeficientes)
                    for s in lista_subpuntajes)
        return total / len(lista_subpuntajes)

    bajo, alto = config.CALIBRACION_B0_MIN, config.CALIBRACION_B0_MAX
    # La tasa pedida tiene que caber entre los extremos de la busqueda.
    if media(bajo) > tasa:
        return bajo
    if media(alto) < tasa:
        return alto

    for _ in range(config.CALIBRACION_MAX_ITER):
        medio = (bajo + alto) / 2.0
        if media(medio) < tasa:
            bajo = medio
        else:
            alto = medio
        if alto - bajo < config.CALIBRACION_TOLERANCIA:
            break
    return (bajo + alto) / 2.0


# ----------------------------- 2c y 2d. CONTRIBUCIONES Y PROBLEMAS -------
def contribuciones(s, coeficientes=None):
    """Aporte de cada dimension al logit: b_d * s_d."""
    coef = config.COEFICIENTES if coeficientes is None else coeficientes
    return {dim: coef[dim] * s[dim] for dim in config.DIMENSIONES}


def factor_principal(contribs):
    """La dimension que mas aporta al riesgo. Empate: orden de DIMENSIONES."""
    return max(config.DIMENSIONES, key=lambda dim: contribs[dim])


def problemas(s):
    """Dimensiones con subpuntaje >= UMBRAL_PROBLEMA, de mayor a menor."""
    criticas = [dim for dim in config.DIMENSIONES
                if s[dim] >= config.UMBRAL_PROBLEMA]
    return sorted(criticas, key=lambda dim: s[dim], reverse=True)


def nivel(p, umbral_medio=None, umbral_alto=None):
    """bajo / medio / alto. Por defecto usa los umbrales de config.py.

    Se pueden pasar otros umbrales porque la API deja que cada simulacion
    defina los suyos. Los umbrales son inclusivos por abajo: p exactamente
    igual a UMBRAL_MEDIO ya es "medio".
    """
    u_medio = config.UMBRAL_MEDIO if umbral_medio is None else umbral_medio
    u_alto = config.UMBRAL_ALTO if umbral_alto is None else umbral_alto
    if p >= u_alto:
        return "alto"
    if p >= u_medio:
        return "medio"
    return "bajo"


# ------------------------------------------------------ PASO 2 COMPLETO --
def evaluar(r, b0, coeficientes=None, umbral_medio=None, umbral_alto=None):
    """Paso 2 completo para un registro ya validado.

    Devuelve subpuntajes, p, nivel, contribuciones, factor principal y
    problemas. No incluye el intervalo P5-P95 (eso es incertidumbre.py) ni
    la intervencion (eso es intervencion.py).
    """
    s = subpuntajes(r)
    contribs = contribuciones(s, coeficientes)
    p = probabilidad(s, b0, coeficientes)
    return {
        "subpuntajes": s,
        "p": p,
        "nivel": nivel(p, umbral_medio, umbral_alto),
        "contribuciones": contribs,
        "factor_principal": factor_principal(contribs),
        "problemas": problemas(s),
    }
