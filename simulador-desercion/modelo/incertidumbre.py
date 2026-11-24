"""
Segundo uso de Montecarlo: propagar la incertidumbre de los coeficientes.

Los b_d son supuestos expertos, no estimaciones hechas con datos. Reportar un
unico numero "p = 0.27" vende como exacto algo que no lo es. Entonces, para
cada estudiante se repite el calculo K veces muestreando

    b_d ~ Normal(b_d, COEF_SIGMA_RELATIVA * b_d)

y se reportan tres numeros: p (estimacion puntual con los coeficientes
nominales), P5 y P95. El intervalo P5-P95 dice "con estos supuestos, la
probabilidad de este estudiante esta entre tanto y tanto".

Ojo con lo que Montecarlo hace y no hace aqui: NO es el modelo de desercion.
El modelo es la regresion logistica de riesgo.py. Montecarlo solo responde
"cuanto se mueve el resultado si los coeficientes estuvieran un 25% arriba o
abajo". La incertidumbre por falta de datos reales no se corrige muestreando.

b0 queda FIJO en su valor calibrado: es el parametro que absorbe la tasa base
observada, no un supuesto experto que convenga perturbar.
"""

import config
from modelo import riesgo


def percentil(valores_ordenados, pct):
    """Percentil por interpolacion lineal sobre una lista YA ordenada.

    Convencion equivalente a la de numpy.percentile con method="linear",
    implementada a mano porque solo se permiten flask y pytest.
    """
    if not valores_ordenados:
        raise ValueError("no hay valores para calcular el percentil")
    if len(valores_ordenados) == 1:
        return valores_ordenados[0]

    posicion = (len(valores_ordenados) - 1) * (pct / 100.0)
    inferior = int(posicion)
    superior = min(inferior + 1, len(valores_ordenados) - 1)
    fraccion = posicion - inferior
    return (valores_ordenados[inferior] * (1 - fraccion)
            + valores_ordenados[superior] * fraccion)


def muestrear_coeficientes(rng, k=None, coeficientes=None):
    """K vectores de coeficientes muestreados ~ Normal(b_d, sigma_rel*b_d).

    Se generan una sola vez por simulacion y se reusan para todos los
    estudiantes (tecnica de numeros aleatorios comunes). Eso hace los
    intervalos comparables entre estudiantes -- dos estudiantes con el mismo
    perfil obtienen el mismo intervalo -- y evita volver a muestrear 4
    coeficientes N*K veces.
    """
    k = config.K_MONTECARLO if k is None else k
    coef = config.COEFICIENTES if coeficientes is None else coeficientes
    sigma_rel = config.COEF_SIGMA_RELATIVA

    muestras = []
    for _ in range(k):
        muestras.append({dim: rng.gauss(coef[dim], sigma_rel * coef[dim])
                         for dim in config.DIMENSIONES})
    return muestras


def intervalo(s, b0, muestras):
    """Intervalo P5-P95 de la probabilidad de un estudiante.

    s: subpuntajes del estudiante. b0: intercepto calibrado.
    muestras: los vectores de coeficientes de muestrear_coeficientes().
    """
    probabilidades = sorted(riesgo.probabilidad(s, b0, coef)
                            for coef in muestras)
    return (percentil(probabilidades, config.PERCENTIL_BAJO),
            percentil(probabilidades, config.PERCENTIL_ALTO))


def resumen(s, b0, muestras):
    """p puntual mas su intervalo, listo para guardar o mostrar."""
    p5, p95 = intervalo(s, b0, muestras)
    return {"p": riesgo.probabilidad(s, b0), "p5": p5, "p95": p95}
