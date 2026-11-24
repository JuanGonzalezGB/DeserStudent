"""
Generacion de la cohorte sintetica. PRIMER uso de Montecarlo.

Aqui Montecarlo si es la herramienta correcta, porque el problema es de
muestreo: no hay datos reales de estudiantes disponibles (privacidad), asi que
se construye una poblacion artificial muestreando cada variable de una
distribucion plausible, con dependencias simples entre variables.

Montecarlo NO decide quien deserta. Solo produce los perfiles de entrada E.
Quien calcula el riesgo es la regresion logistica de riesgo.py.

Dependencias que se modelan (todas documentadas en config.py y en
docs/justificacion_modelo.md):

    estrato                 -> distribucion discreta con mas peso en 1-3
    ingreso | estrato       -> Normal(media(estrato), 0.35*media)
    horas_trabajo | ingreso -> mas horas cuando el ingreso del hogar es bajo
    asistencia | horas      -> baja cuando las horas de trabajo son altas
    promedio | asistencia   -> Normal truncada a [0, 5], correlacionada
    perdidas | promedio     -> Poisson con media mayor si el promedio es bajo
    apoyo, saldo, desplazamiento, primera generacion | estrato e ingreso

Todo se muestrea con random de la libreria estandar y una semilla fija, asi
que la misma semilla reproduce exactamente la misma cohorte.

Ademas se inyecta un 3% de registros con errores a proposito (campo vacio,
valor fuera de rango, contradiccion) para demostrar que el Paso 1 funciona.
Esos registros se marcan en la salida con "error_inyectado".
"""

import math
import random

import config


# ----------------------------------------------------------------- utiles --
def _recorte(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _discreta(rng, valores, pesos):
    """Un valor de una distribucion discreta con los pesos dados."""
    return rng.choices(valores, weights=pesos, k=1)[0]


def _poisson(rng, lam):
    """Poisson(lam) por el metodo de Knuth (solo libreria estandar)."""
    if lam <= 0:
        return 0
    limite = math.exp(-lam)
    k = 0
    acumulado = rng.random()
    while acumulado > limite:
        k += 1
        acumulado *= rng.random()
    return k


# ------------------------------------------------- muestreo de un alumno --
def generar_registro(rng):
    """Muestrea un registro de estudiante valido y plausible."""

    # --- dimension financiera: el estrato manda -------------------------
    estrato = _discreta(rng, config.ESTRATO_VALORES, config.ESTRATO_PESOS)

    media_ingreso = config.INGRESO_MEDIA_POR_ESTRATO[estrato]
    ingreso = rng.gauss(media_ingreso,
                        config.INGRESO_SIGMA_RELATIVA * media_ingreso)
    ingreso = _recorte(ingreso, *config.RANGOS["ingreso_hogar_smmlv"])
    # Topes anti-contradiccion: el azar no debe producir las combinaciones
    # imposibles que el Paso 1 rechaza (eso se inyecta aparte, a proposito).
    if estrato >= 5:
        ingreso = max(ingreso, config.INGRESO_PISO_ESTRATO_ALTO)
    if estrato <= 2:
        ingreso = min(ingreso, config.INGRESO_TECHO_ESTRATO_BAJO)
    ingreso = round(ingreso, 2)

    tiene_apoyo = rng.random() < config.APOYO_PROB_POR_ESTRATO[estrato]

    prob_saldo = (config.SALDO_PROB_CON_APOYO if tiene_apoyo
                  else config.SALDO_PROB_BASE)
    if rng.random() < prob_saldo:
        mu_saldo = max(config.SALDO_MU_MIN,
                       config.SALDO_MU_BASE - config.SALDO_MU_PENDIENTE * ingreso)
        saldo = rng.gauss(mu_saldo, config.SALDO_SIGMA_RELATIVA * mu_saldo)
        saldo = int(_recorte(saldo, *config.RANGOS["saldo_pendiente_cop"]))
    else:
        saldo = 0

    # --- semestre y dimension laboral ----------------------------------
    semestre = _discreta(rng, config.SEMESTRE_VALORES, config.SEMESTRE_PESOS)

    prob_trabaja = _recorte(
        config.TRABAJO_PROB_BASE - config.TRABAJO_PROB_PENDIENTE * ingreso,
        config.TRABAJO_PROB_MIN, config.TRABAJO_PROB_MAX)
    if rng.random() < prob_trabaja:
        mu_horas = _recorte(
            config.HORAS_MU_BASE - config.HORAS_MU_PENDIENTE * ingreso,
            config.HORAS_MU_MIN, config.HORAS_MU_MAX)
        horas = rng.gauss(mu_horas, config.HORAS_SIGMA)
        horas = round(_recorte(horas, 1.0,
                               config.RANGOS["horas_trabajo_semana"][1]), 1)
        prob_area = _recorte(
            config.AREA_PROB_BASE + config.AREA_PROB_POR_SEMESTRE * semestre,
            0.0, 1.0)
        trabaja_en_area = rng.random() < prob_area
    else:
        horas = 0.0
        trabaja_en_area = False

    # --- dimension academica: depende de las horas de trabajo ----------
    mu_asistencia = (config.ASISTENCIA_MU_BASE
                     - config.ASISTENCIA_MU_PENDIENTE * horas)
    asistencia = rng.gauss(mu_asistencia, config.ASISTENCIA_SIGMA)
    asistencia = round(_recorte(asistencia, *config.RANGOS["asistencia_pct"]), 1)

    mu_promedio = (config.PROMEDIO_MU_BASE
                   + config.PROMEDIO_MU_PENDIENTE * asistencia)
    promedio = rng.gauss(mu_promedio, config.PROMEDIO_SIGMA)
    promedio = round(_recorte(promedio, *config.RANGOS["promedio"]), 2)

    lam = max(0.0, config.PERDIDAS_PENDIENTE
              * (config.PERDIDAS_UMBRAL_PROMEDIO - promedio))
    perdidas = min(_poisson(rng, lam), config.RANGOS["materias_perdidas"][1])
    # Tercer tope anti-contradiccion: promedio 5.0 con materias perdidas.
    if perdidas > 0 and promedio >= config.RANGOS["promedio"][1]:
        promedio = 4.9

    # --- dimension personal --------------------------------------------
    desplazamiento = rng.gauss(config.DESPLAZAMIENTO_MU_POR_ESTRATO[estrato],
                               config.DESPLAZAMIENTO_SIGMA)
    desplazamiento = int(_recorte(desplazamiento,
                                  *config.RANGOS["tiempo_desplazamiento_min"]))
    personas = _discreta(rng, tuple(range(0, 7)), config.PERSONAS_PESOS)
    apoyo_familiar = _discreta(rng, tuple(range(1, 6)),
                               config.APOYO_FAMILIAR_PESOS)
    primera_gen = (rng.random()
                   < config.PRIMERA_GEN_PROB_POR_ESTRATO[estrato])

    return {
        "promedio": promedio,
        "materias_perdidas": perdidas,
        "asistencia_pct": asistencia,
        "semestre": semestre,
        "saldo_pendiente_cop": saldo,
        "ingreso_hogar_smmlv": ingreso,
        "estrato": estrato,
        "tiene_apoyo_financiero": tiene_apoyo,
        "horas_trabajo_semana": horas,
        "trabaja_en_area_de_estudio": trabaja_en_area,
        "tiempo_desplazamiento_min": desplazamiento,
        "personas_a_cargo": personas,
        "apoyo_familiar": apoyo_familiar,
        "primera_generacion_universitaria": primera_gen,
    }


# -------------------------------------------- errores inyectados a mano --
def _danar_registro(registro, tipo, vuelta):
    """Rompe un registro a proposito para probar el Paso 1.

    tipo: "campo_vacio" | "fuera_de_rango" | "contradiccion"
    vuelta: cuantas veces ya se uso ESTE tipo. Rota entre los campos
    afectados para que los 3% de registros danados no sean todos identicos.

    Ojo: la vuelta se cuenta por tipo, no sobre el total de registros
    danados. Contar sobre el total hacia que la subvariante quedara
    correlacionada con el tipo (ambas rotaban modulo 3), y la contradiccion
    del caso A03 nunca se generaba. Lo encontro test_generador.py.
    """
    r = dict(registro)

    if tipo == "campo_vacio":
        campos = ("promedio", "asistencia_pct", "estrato", "apoyo_familiar")
        r[campos[vuelta % len(campos)]] = None
        return r, "campo_vacio"

    if tipo == "fuera_de_rango":
        fuera = (("promedio", 6.3), ("asistencia_pct", 142.0),
                 ("semestre", 19), ("personas_a_cargo", 11))
        campo, valor = fuera[vuelta % len(fuera)]
        r[campo] = valor
        return r, "fuera_de_rango"

    # contradiccion: rota entre las tres del contrato, incluido el hueco A03
    cual = vuelta % 3
    if cual == 0:
        r["estrato"] = 6
        r["ingreso_hogar_smmlv"] = 0.4        # estrato alto, ingreso < 1
    elif cual == 1:
        r["estrato"] = 1
        r["ingreso_hogar_smmlv"] = 14.0       # hueco A03: estrato bajo, ingreso > 10
    else:
        r["promedio"] = 5.0
        r["materias_perdidas"] = max(1, r["materias_perdidas"])
    return r, "contradiccion"


# ------------------------------------------------------------- cohorte ----
def generar_cohorte(n=None, semilla=None, pct_error=None):
    """Genera la cohorte sintetica completa.

    Devuelve una lista de dicts con:
        codigo          -> identificador sintetico (UNA-0001, ...)
        datos           -> el registro de entrada E
        error_inyectado -> None, o el tipo de error que se le metio a proposito

    La misma semilla produce exactamente la misma cohorte.
    """
    n = config.N_POR_DEFECTO if n is None else n
    semilla = config.SEMILLA_POR_DEFECTO if semilla is None else semilla
    pct_error = (config.PCT_REGISTROS_CON_ERROR if pct_error is None
                 else pct_error)

    rng = random.Random(semilla)
    cohorte = [{"codigo": "UNA-%04d" % (i + 1),
                "datos": generar_registro(rng),
                "error_inyectado": None}
               for i in range(n)]

    # Registros danados a proposito: posiciones elegidas con el mismo rng,
    # asi que tambien son reproducibles.
    cantidad = int(round(n * pct_error))
    if cantidad > 0:
        posiciones = sorted(rng.sample(range(n), min(cantidad, n)))
        tipos = config.TIPOS_DE_ERROR_INYECTADO
        for indice, pos in enumerate(posiciones):
            tipo = tipos[indice % len(tipos)]
            vuelta = indice // len(tipos)
            datos, marca = _danar_registro(cohorte[pos]["datos"], tipo, vuelta)
            cohorte[pos]["datos"] = datos
            cohorte[pos]["error_inyectado"] = marca

    return cohorte
