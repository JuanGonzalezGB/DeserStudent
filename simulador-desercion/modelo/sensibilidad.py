"""
Validacion del modelo: lo que el profesor pidio para creerle al simulador.

Cuatro comprobaciones, todas calculadas con los datos de la corrida, no
escritas a mano:

  1. CALIBRACION  -- la probabilidad media de la cohorte debe coincidir con la
     tasa base de desercion semestral (+-0.005). Es lo que garantiza que el
     simulador no este inflando ni subestimando el riesgo global.

  2. SENSIBILIDAD -- se varia cada coeficiente b_d en +-50% y se mide cuanto
     se mueve el indice general. Muestra de que supuesto depende mas el
     resultado, que es exactamente la pregunta "y si tus coeficientes estan
     mal?".

  3. VALIDEZ DE CARA -- tres perfiles de referencia con resultado esperado
     escrito de antemano. Si un estudiante sin ningun problema saliera "alto",
     el modelo estaria mal por mucho que calibre.

  4. MONOTONIA -- empeorar una variable de riesgo nunca debe bajar p. Es la
     propiedad que hace el modelo defendible: no hay sorpresas de signo.

Nota de alcance: 'semestre' es parte de la entrada E (dimension academica) y
se usa para describir al estudiante y para generar la cohorte, pero NO entra
en ninguna de las cuatro formulas de subpuntaje. Por eso no aparece en la
prueba de monotonia. Esta documentado como limitacion en
docs/justificacion_modelo.md.
"""

import config
from modelo import riesgo
from modelo import intervencion

VARIACION_SENSIBILIDAD = 0.50   # +-50% sobre cada coeficiente


# ===================================================== 1. CALIBRACION =====
def calibracion(lista_subpuntajes, b0, tasa_base=None):
    """Compara la probabilidad media obtenida contra la tasa base."""
    tasa = config.TASA_BASE_SEMESTRAL if tasa_base is None else tasa_base
    if not lista_subpuntajes:
        return {"tasa_base": tasa, "media_obtenida": 0.0, "diferencia": tasa,
                "margen": config.CALIBRACION_MARGEN_OK, "ok": False,
                "b0_calibrado": b0}

    ps = [riesgo.probabilidad(s, b0) for s in lista_subpuntajes]
    media = sum(ps) / len(ps)
    diferencia = media - tasa
    return {
        "tasa_base": tasa,
        "media_obtenida": media,
        "diferencia": diferencia,
        "margen": config.CALIBRACION_MARGEN_OK,
        "ok": abs(diferencia) <= config.CALIBRACION_MARGEN_OK,
        "b0_calibrado": b0,
    }


# ==================================================== 2. SENSIBILIDAD =====
def _indice(lista_subpuntajes, b0, coeficientes):
    """Indice general (probabilidad media) con unos coeficientes dados."""
    if not lista_subpuntajes:
        return 0.0
    ps = [riesgo.probabilidad(s, b0, coeficientes) for s in lista_subpuntajes]
    return sum(ps) / len(ps)


def sensibilidad(lista_subpuntajes, b0, variacion=VARIACION_SENSIBILIDAD):
    """Varia cada coeficiente +-variacion y mide el cambio del indice general.

    b0 se mantiene en su valor calibrado a proposito: si se recalibrara, el
    indice volveria por construccion a la tasa base y la prueba no mostraria
    nada. Lo que interesa es el efecto neto de equivocarse en un b_d.
    """
    base = _indice(lista_subpuntajes, b0, config.COEFICIENTES)
    filas = []
    for dim in config.DIMENSIONES:
        fila = {"dimension": dim, "coeficiente_base": config.COEFICIENTES[dim],
                "indice_base": base}
        for etiqueta, factor in (("bajo", 1 - variacion), ("alto", 1 + variacion)):
            coef = dict(config.COEFICIENTES)
            coef[dim] = config.COEFICIENTES[dim] * factor
            indice = _indice(lista_subpuntajes, b0, coef)
            fila["coeficiente_" + etiqueta] = coef[dim]
            fila["indice_" + etiqueta] = indice
            fila["delta_" + etiqueta] = indice - base
        # Cuanto se mueve el indice, en puntos porcentuales, de un extremo a otro.
        fila["amplitud_pp"] = 100.0 * (fila["indice_alto"] - fila["indice_bajo"])
        filas.append(fila)

    filas.sort(key=lambda f: abs(f["amplitud_pp"]), reverse=True)
    return {"variacion": variacion, "indice_base": base, "filas": filas,
            "mas_influyente": filas[0]["dimension"] if filas else None}


# ================================================= 3. VALIDEZ DE CARA =====
# Tres perfiles con el resultado que CUALQUIERA esperaria, escrito antes de
# correr el modelo. El perfil 2 tiene una sola dimension problematica (la
# financiera, con s_F > 0.9) y las otras tres en valores tipicos de la
# cohorte, no en cero: asi se comprueba que un problema financiero por si
# solo alcanza para entrar al programa de acompanamiento.
PERFILES_REFERENCIA = (
    {
        "nombre": "sin_riesgo",
        "descripcion": "Buen promedio, sin deuda, no trabaja, con apoyo familiar",
        "esperado": {"nivel": "bajo", "requiere_intervencion": False,
                     "problemas": []},
        "datos": {
            "promedio": 4.8, "materias_perdidas": 0, "asistencia_pct": 98.0,
            "semestre": 5,
            "saldo_pendiente_cop": 0, "ingreso_hogar_smmlv": 8.0,
            "estrato": 5, "tiene_apoyo_financiero": True,
            "horas_trabajo_semana": 0.0, "trabaja_en_area_de_estudio": False,
            "tiempo_desplazamiento_min": 10, "personas_a_cargo": 0,
            "apoyo_familiar": 5, "primera_generacion_universitaria": False,
        },
    },
    {
        "nombre": "riesgo_solo_financiero",
        "descripcion": ("Deuda alta, ingreso bajo y sin apoyo; lo academico, "
                        "lo laboral y lo personal en valores tipicos"),
        "esperado": {"nivel": "medio", "requiere_intervencion": True,
                     "problemas": ["financiera"],
                     "intervencion_principal": "apoyo_financiero"},
        "datos": {
            "promedio": 3.6, "materias_perdidas": 1, "asistencia_pct": 85.0,
            "semestre": 4,
            "saldo_pendiente_cop": 20_000_000, "ingreso_hogar_smmlv": 0.5,
            "estrato": 1, "tiene_apoyo_financiero": False,
            "horas_trabajo_semana": 12.0, "trabaja_en_area_de_estudio": False,
            "tiempo_desplazamiento_min": 45, "personas_a_cargo": 1,
            "apoyo_familiar": 4, "primera_generacion_universitaria": False,
        },
    },
    {
        "nombre": "todo_alto",
        "descripcion": "Las cuatro dimensiones en su peor valor posible",
        "esperado": {"nivel": "alto", "requiere_intervencion": True,
                     "problemas": ["academica", "financiera", "laboral",
                                   "personal"]},
        "datos": {
            "promedio": 0.5, "materias_perdidas": 6, "asistencia_pct": 35.0,
            "semestre": 7,
            "saldo_pendiente_cop": 20_000_000, "ingreso_hogar_smmlv": 0.3,
            "estrato": 1, "tiene_apoyo_financiero": False,
            "horas_trabajo_semana": 55.0, "trabaja_en_area_de_estudio": False,
            "tiempo_desplazamiento_min": 200, "personas_a_cargo": 4,
            "apoyo_familiar": 1, "primera_generacion_universitaria": True,
        },
    },
)


def validez_de_cara(b0, umbral_medio=None, umbral_alto=None):
    """Corre los tres perfiles de referencia y compara con lo esperado."""
    resultados = []
    for perfil in PERFILES_REFERENCIA:
        evaluacion = riesgo.evaluar(perfil["datos"], b0,
                                    umbral_medio=umbral_medio,
                                    umbral_alto=umbral_alto)
        plan = intervencion.decidir(evaluacion["nivel"],
                                    evaluacion["problemas"],
                                    evaluacion["factor_principal"])
        esperado = perfil["esperado"]

        obtenido = {
            "nivel": evaluacion["nivel"],
            "requiere_intervencion": plan["requiere_intervencion"],
            "problemas": evaluacion["problemas"],
        }
        if plan["intervenciones"]:
            obtenido["intervencion_principal"] = plan["intervenciones"][0]["tipo"]

        # Las listas de problemas se comparan como conjuntos: lo que importa
        # es cuales dimensiones son problematicas, no en que orden salieron.
        coincide = True
        for clave, valor_esperado in esperado.items():
            valor_obtenido = obtenido.get(clave)
            if isinstance(valor_esperado, list):
                if set(valor_esperado) != set(valor_obtenido or []):
                    coincide = False
            elif valor_esperado != valor_obtenido:
                coincide = False

        resultados.append({
            "nombre": perfil["nombre"],
            "descripcion": perfil["descripcion"],
            "subpuntajes": evaluacion["subpuntajes"],
            "p": evaluacion["p"],
            "factor_principal": evaluacion["factor_principal"],
            "esperado": esperado,
            "obtenido": obtenido,
            "coincide": coincide,
        })

    return {"perfiles": resultados,
            "ok": all(r["coincide"] for r in resultados)}


# ====================================================== 4. MONOTONIA =====
# Para cada variable, una secuencia de valores de MEJOR a PEOR. Empeorar la
# variable nunca debe bajar la probabilidad p.
PASOS_MONOTONIA = {
    "promedio": (5.0, 4.0, 3.0, 2.0, 1.0, 0.0),
    "materias_perdidas": (0, 1, 2, 3, 5, 8),
    "asistencia_pct": (100.0, 90.0, 75.0, 50.0, 25.0, 0.0),
    "saldo_pendiente_cop": (0, 1_000_000, 4_000_000, 8_000_000, 20_000_000),
    "ingreso_hogar_smmlv": (20.0, 10.0, 6.0, 4.0, 2.0, 1.0, 0.0),
    "estrato": (6, 5, 4, 3, 2, 1),
    "tiene_apoyo_financiero": (True, False),
    "horas_trabajo_semana": (0.0, 10.0, 20.0, 40.0, 60.0),
    "trabaja_en_area_de_estudio": (True, False),
    "tiempo_desplazamiento_min": (0, 30, 60, 120, 240),
    "personas_a_cargo": (0, 1, 2, 3, 6),
    "apoyo_familiar": (5, 4, 3, 2, 1),
    "primera_generacion_universitaria": (False, True),
}

# Registro de partida sobre el que se mueve una variable a la vez. Esta
# elegido para que ninguna sustitucion produzca una contradiccion del Paso 1
# (estrato 3 e ingreso 3.0 SMMLV soportan todos los pasos de la tabla).
REGISTRO_BASE_MONOTONIA = {
    "promedio": 3.5, "materias_perdidas": 0, "asistencia_pct": 80.0,
    "semestre": 5,
    "saldo_pendiente_cop": 2_000_000, "ingreso_hogar_smmlv": 3.0,
    "estrato": 3, "tiene_apoyo_financiero": False,
    "horas_trabajo_semana": 15.0, "trabaja_en_area_de_estudio": False,
    "tiempo_desplazamiento_min": 40, "personas_a_cargo": 1,
    "apoyo_familiar": 4, "primera_generacion_universitaria": False,
}


def monotonia(b0, tolerancia=1e-12):
    """Comprueba que empeorar cada variable nunca baje p."""
    filas = []
    for campo, pasos in PASOS_MONOTONIA.items():
        ps = []
        for valor in pasos:
            registro = dict(REGISTRO_BASE_MONOTONIA)
            registro[campo] = valor
            ps.append(riesgo.probabilidad(riesgo.subpuntajes(registro), b0))

        violaciones = [
            {"paso": i, "de": pasos[i], "a": pasos[i + 1],
             "p_antes": ps[i], "p_despues": ps[i + 1]}
            for i in range(len(ps) - 1)
            if ps[i + 1] < ps[i] - tolerancia
        ]
        filas.append({
            "variable": campo,
            "pasos": [{"valor": v, "p": p} for v, p in zip(pasos, ps)],
            "p_mejor": ps[0],
            "p_peor": ps[-1],
            "violaciones": violaciones,
            "ok": not violaciones,
        })

    filas.sort(key=lambda f: f["variable"])
    return {"variables": filas,
            "n_variables": len(filas),
            "ok": all(f["ok"] for f in filas)}


# ================================================ VALIDACION COMPLETA =====
def validar_modelo(lista_subpuntajes, b0, tasa_base=None, umbral_medio=None,
                   umbral_alto=None):
    """Las cuatro comprobaciones juntas, listas para la API y la pagina."""
    cal = calibracion(lista_subpuntajes, b0, tasa_base)
    sens = sensibilidad(lista_subpuntajes, b0)
    cara = validez_de_cara(b0, umbral_medio, umbral_alto)
    mono = monotonia(b0)
    return {
        "calibracion": cal,
        "sensibilidad": sens,
        "validez_de_cara": cara,
        "monotonia": mono,
        "ok": cal["ok"] and cara["ok"] and mono["ok"],
    }
