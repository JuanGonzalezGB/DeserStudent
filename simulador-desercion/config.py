"""
Parametros del simulador de desercion. TODOS los numeros del modelo viven aqui.

Nada en modelo/ define constantes propias: si hay que sustentar o ajustar una
cifra ante el profesor, se cambia en este archivo y el resto del sistema la usa.

Secciones:
    1. Contrato de la entrada E (campos, tipos, rangos)
    2. Pesos de los subpuntajes por dimension (Paso 2a)
    3. Coeficientes de la regresion logistica (Paso 2b)
    4. Umbrales de nivel y de problema (Paso 2d y 6)
    5. Montecarlo de incertidumbre (seccion 5 del modelo)
    6. Distribuciones de la cohorte sintetica (Montecarlo de generacion)
    7. Catalogo de intervenciones (Paso 3)
"""

# ===========================================================================
# 1. CONTRATO DE LA ENTRADA E
# ===========================================================================

DIMENSIONES = ("academica", "financiera", "laboral", "personal")

# Campo -> dimension a la que pertenece. Todos son obligatorios.
CAMPOS_POR_DIMENSION = {
    "academica": ("promedio", "materias_perdidas", "asistencia_pct", "semestre"),
    "financiera": ("saldo_pendiente_cop", "ingreso_hogar_smmlv", "estrato",
                   "tiene_apoyo_financiero"),
    "laboral": ("horas_trabajo_semana", "trabaja_en_area_de_estudio"),
    "personal": ("tiempo_desplazamiento_min", "personas_a_cargo",
                 "apoyo_familiar", "primera_generacion_universitaria"),
}

CAMPOS_OBLIGATORIOS = tuple(
    campo for dim in DIMENSIONES for campo in CAMPOS_POR_DIMENSION[dim]
)

# Enteros estrictos (bool NO cuenta como entero, igual que en el motor anterior).
CAMPOS_ENTEROS = (
    "materias_perdidas", "semestre", "saldo_pendiente_cop", "estrato",
    "tiempo_desplazamiento_min", "personas_a_cargo", "apoyo_familiar",
)
# Numericos que admiten decimales.
CAMPOS_DECIMALES = ("promedio", "asistencia_pct", "ingreso_hogar_smmlv",
                    "horas_trabajo_semana")
CAMPOS_BOOLEANOS = ("tiene_apoyo_financiero", "trabaja_en_area_de_estudio",
                    "primera_generacion_universitaria")

# Rangos cerrados [minimo, maximo]: los bordes exactos son VALIDOS.
RANGOS = {
    "promedio": (0.0, 5.0),
    "materias_perdidas": (0, 8),
    "asistencia_pct": (0.0, 100.0),
    "semestre": (1, 12),
    "saldo_pendiente_cop": (0, 20_000_000),
    "ingreso_hogar_smmlv": (0.0, 20.0),
    "estrato": (1, 6),
    "horas_trabajo_semana": (0.0, 60.0),
    "tiempo_desplazamiento_min": (0, 240),
    "personas_a_cargo": (0, 6),
    "apoyo_familiar": (1, 5),
}

# ===========================================================================
# 2. PESOS DE LOS SUBPUNTAJES POR DIMENSION (Paso 2a)
# ===========================================================================
# Cada subpuntaje s_d es un promedio ponderado de variables normalizadas a
# [0, 1] en el que 0 = sin riesgo y 1 = riesgo maximo. Los pesos de cada
# dimension suman 1.0 exactamente, asi que s_d siempre queda en [0, 1].
# Son [SUPUESTO] de juicio experto: no se estimaron con datos.

# Academica: el promedio pesa mas que las perdidas y la asistencia.
PESOS_ACADEMICA = {"promedio": 0.4, "materias_perdidas": 0.3, "asistencia": 0.3}
# Se considera riesgo academico maximo por perdidas a partir de 3 materias.
PERDIDAS_SATURACION = 3

# Financiera: el saldo y el ingreso dominan; el estrato y el apoyo matizan.
PESOS_FINANCIERA = {"saldo": 0.35, "ingreso": 0.30, "estrato": 0.20,
                    "sin_apoyo": 0.15}
# Saldo que ya se considera deuda maxima para el subpuntaje (COP).
SALDO_SATURACION = 8_000_000
# Ingreso del hogar (SMMLV) a partir del cual el componente de ingreso es 0.
INGRESO_SATURACION = 4.0

# Laboral: la intensidad horaria pesa mas que la desalineacion con la carrera.
# La desalineacion se escala por la intensidad para que quien no trabaja
# (0 horas) tenga subpuntaje 0 aunque "no trabaje en su area".
PESOS_LABORAL = {"intensidad": 0.70, "desalineacion": 0.30}
# Horas semanales que ya se consideran carga laboral maxima.
HORAS_SATURACION = 40.0

# Personal: el apoyo familiar y el desplazamiento dominan.
PESOS_PERSONAL = {"desplazamiento": 0.30, "personas_a_cargo": 0.25,
                  "apoyo_familiar": 0.30, "primera_generacion": 0.15}
# Minutos de desplazamiento que ya se consideran carga maxima.
DESPLAZAMIENTO_SATURACION = 120
# Personas a cargo que ya se consideran carga maxima.
PERSONAS_SATURACION = 3

# ===========================================================================
# 3. COEFICIENTES DE LA REGRESION LOGISTICA (Paso 2b)
# ===========================================================================
#   p = 1 / (1 + exp(-(b0 + bA*sA + bF*sF + bL*sL + bP*sP)))
# Los b_d son [SUPUESTO] de juicio experto, ordenados segun el peso que la
# literatura de desercion da a cada dimension (ver docs/justificacion_modelo.md):
# lo academico primero, luego lo financiero, y despues lo laboral y lo personal.
COEFICIENTES = {
    "academica": 3.0,
    "financiera": 2.5,
    "laboral": 1.5,
    "personal": 1.2,
}

# b0 NO se inventa: se CALIBRA por biseccion para que la probabilidad media de
# la cohorte sea igual a TASA_BASE_SEMESTRAL.
# [SUPUESTO] verificar la cifra vigente de desercion anual universitaria en
# SPADEA (Ministerio de Educacion Nacional) y ajustar.
TASA_BASE_SEMESTRAL = 0.09

# Parametros de la biseccion que despeja b0.
CALIBRACION_B0_MIN = -30.0
CALIBRACION_B0_MAX = 30.0
CALIBRACION_TOLERANCIA = 1e-6
CALIBRACION_MAX_ITER = 200
# Margen con el que se declara "calibrado" en la validacion del modelo.
CALIBRACION_MARGEN_OK = 0.005

# ===========================================================================
# 4. UMBRALES DE NIVEL Y DE PROBLEMA
# ===========================================================================
# nivel: bajo si p < UMBRAL_MEDIO; medio si UMBRAL_MEDIO <= p < UMBRAL_ALTO;
#        alto si p >= UMBRAL_ALTO.
UMBRAL_MEDIO = 0.15
UMBRAL_ALTO = 0.35
# Una dimension es "problema" del estudiante si su subpuntaje llega a este valor.
UMBRAL_PROBLEMA = 0.60

# ===========================================================================
# 5. MONTECARLO DE INCERTIDUMBRE (seccion 5)
# ===========================================================================
# Para cada estudiante se repite el calculo K veces muestreando
#   b_d ~ Normal(b_d, COEF_SIGMA_RELATIVA * b_d)
# y se reportan los percentiles P5 y P95. b0 queda fijo en su valor calibrado:
# es el parametro que absorbe la tasa base, no un supuesto experto.
K_MONTECARLO = 1000
COEF_SIGMA_RELATIVA = 0.25
PERCENTIL_BAJO = 5
PERCENTIL_ALTO = 95

# ===========================================================================
# 6. DISTRIBUCIONES DE LA COHORTE SINTETICA (Montecarlo de generacion)
# ===========================================================================
# No hay datos reales disponibles (privacidad de los estudiantes), asi que la
# cohorte se MUESTREA de distribuciones plausibles con dependencias simples.
# Todas son [VERIFICAR] contra las estadisticas reales de la universidad.
N_POR_DEFECTO = 500
SEMILLA_POR_DEFECTO = 42

# --- estrato ~ distribucion discreta con mas peso en 1-3 -------------------
ESTRATO_VALORES = (1, 2, 3, 4, 5, 6)
ESTRATO_PESOS = (0.18, 0.27, 0.25, 0.16, 0.09, 0.05)

# --- ingreso_hogar_smmlv | estrato ~ Normal(media(estrato), 0.35*media) ----
INGRESO_MEDIA_POR_ESTRATO = {1: 1.2, 2: 2.0, 3: 3.2, 4: 5.0, 5: 8.0, 6: 12.0}
INGRESO_SIGMA_RELATIVA = 0.35
# Topes anti-contradiccion: el generador nunca produce por azar una de las
# contradicciones que el Paso 1 rechaza (estrato>=5 con ingreso<1,
# estrato<=2 con ingreso>10). Los registros contradictorios se inyectan
# a proposito mas abajo, no por accidente.
INGRESO_PISO_ESTRATO_ALTO = 1.05   # para estrato >= 5
INGRESO_TECHO_ESTRATO_BAJO = 9.5   # para estrato <= 2

# --- trabajo: mas horas cuando el ingreso del hogar es bajo ----------------
# P(trabaja) = recorte(TRABAJO_PROB_BASE - TRABAJO_PROB_PENDIENTE*ingreso)
TRABAJO_PROB_BASE = 0.85
TRABAJO_PROB_PENDIENTE = 0.06
TRABAJO_PROB_MIN = 0.10
TRABAJO_PROB_MAX = 0.90
# horas | trabaja ~ Normal(mu(ingreso), 10) recortada a [1, 60]
HORAS_MU_BASE = 34.0
HORAS_MU_PENDIENTE = 5.0           # mu = BASE - PENDIENTE*ingreso
HORAS_MU_MIN = 8.0
HORAS_MU_MAX = 40.0
HORAS_SIGMA = 10.0
# P(trabaja en el area de estudio) sube con el semestre.
AREA_PROB_BASE = 0.18
AREA_PROB_POR_SEMESTRE = 0.035

# --- asistencia_pct: baja cuando las horas de trabajo son altas -----------
# mu = BASE - PENDIENTE*horas, ~Normal(mu, 6) recortada a [0, 100]
ASISTENCIA_MU_BASE = 92.0
ASISTENCIA_MU_PENDIENTE = 0.45
ASISTENCIA_SIGMA = 6.0

# --- promedio ~ Normal truncada a [0, 5], correlacionado con asistencia ---
# mu = BASE + PENDIENTE*asistencia  (asistencia 100 -> 4.6; 60 -> 3.4)
PROMEDIO_MU_BASE = 1.6
PROMEDIO_MU_PENDIENTE = 0.030
PROMEDIO_SIGMA = 0.45

# --- materias_perdidas: mas probables cuando el promedio es bajo ----------
# lambda = max(0, PENDIENTE*(UMBRAL - promedio)); perdidas ~ Poisson(lambda)
PERDIDAS_UMBRAL_PROMEDIO = 4.0
PERDIDAS_PENDIENTE = 0.9

# --- semestre ~ discreta con mas peso en los primeros semestres -----------
SEMESTRE_VALORES = tuple(range(1, 13))
SEMESTRE_PESOS = (0.14, 0.13, 0.11, 0.10, 0.09, 0.09,
                  0.08, 0.07, 0.06, 0.05, 0.04, 0.04)

# --- tiene_apoyo_financiero: mas probable en estratos bajos ---------------
APOYO_PROB_POR_ESTRATO = {1: 0.55, 2: 0.45, 3: 0.30, 4: 0.18, 5: 0.10, 6: 0.05}

# --- saldo_pendiente_cop: mayor si no hay apoyo y el ingreso es bajo ------
SALDO_PROB_BASE = 0.70             # P(tiene saldo) sin apoyo financiero
SALDO_PROB_CON_APOYO = 0.25        # P(tiene saldo) con apoyo financiero
SALDO_MU_BASE = 6_500_000.0
SALDO_MU_PENDIENTE = 450_000.0     # mu = BASE - PENDIENTE*ingreso
SALDO_MU_MIN = 600_000.0
SALDO_SIGMA_RELATIVA = 0.45

# --- dimension personal ---------------------------------------------------
DESPLAZAMIENTO_MU_POR_ESTRATO = {1: 85, 2: 75, 3: 60, 4: 45, 5: 35, 6: 30}
DESPLAZAMIENTO_SIGMA = 30.0
PERSONAS_PESOS = (0.58, 0.20, 0.12, 0.06, 0.02, 0.01, 0.01)  # 0..6 personas
APOYO_FAMILIAR_PESOS = (0.06, 0.11, 0.25, 0.33, 0.25)        # 1..5
# P(primera generacion) baja con el estrato.
PRIMERA_GEN_PROB_POR_ESTRATO = {1: 0.72, 2: 0.60, 3: 0.44, 4: 0.28,
                                5: 0.16, 6: 0.09}

# --- registros con errores inyectados a proposito -------------------------
# Demuestran que el Paso 1 funciona: se rotan los tres tipos de error.
PCT_REGISTROS_CON_ERROR = 0.03
TIPOS_DE_ERROR_INYECTADO = ("campo_vacio", "fuera_de_rango", "contradiccion")

# ===========================================================================
# 7. CATALOGO DE INTERVENCIONES (Paso 3)
# ===========================================================================
# Una intervencion por dimension problematica. Las opciones financieras son
# las mismas del prototipo y del motor de la entrega anterior.
INTERVENCIONES = {
    "academica": {
        "tipo": "tutoria_academica",
        "nombre": "Tutoria academica",
        "acciones": ("tutoria par en las materias perdidas",
                     "plan de recuperacion con el docente guia"),
    },
    "financiera": {
        "tipo": "apoyo_financiero",
        "nombre": "Plan de apoyo financiero",
        "acciones": ("reestructuracion de matricula en 4 cuotas sin intereses",
                     "beca de alimentacion",
                     "bono de transporte mensual"),
    },
    "laboral": {
        "tipo": "flexibilidad_laboral",
        "nombre": "Flexibilidad horaria / jornada nocturna",
        "acciones": ("reubicacion de horario de clases",
                     "oferta de asignaturas en jornada nocturna"),
    },
    "personal": {
        "tipo": "bienestar_universitario",
        "nombre": "Acompanamiento de bienestar universitario",
        "acciones": ("cita con bienestar universitario",
                     "red de apoyo entre pares"),
    },
}
