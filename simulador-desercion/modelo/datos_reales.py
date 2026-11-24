"""
Cargador y adaptador del dataset publico real UCI (Realinho et al., 4.424
estudiantes) hacia el contrato de 14 variables del simulador, y calculo de
metricas predictivas empiricas contra el desenlace real observado ('Target').

Fuente del dataset:
  Realinho, V., Machado, J., Baptista, L., & Martins, M. V. (2022).
  Predict students' dropout and academic success [Dataset].
  UCI Machine Learning Repository. https://doi.org/10.24432/C5MC89

Reglas de mapeo (documentadas en Calibracion Y FUentes/fuentes_de_datasets):
  - promedio (0..5): promedio de 'Curricular units 1st sem (grade)' y '2nd sem
    (grade)' (escala portuguesa 0..20 dividida entre 4).
  - materias_perdidas (0..8): unidades matriculadas menos aprobadas en los dos
    semestres, acotado a [0, 8].
  - asistencia_pct (0..100): estimada a partir de la tasa de presentacion a
    evaluaciones (matriculadas menos 'without evaluations') y de aprobacion.
  - semestre (1..12): 2 si tiene unidades matriculadas en 2do semestre, 1 si no.
  - saldo_pendiente_cop (0..20M): derivado de 'Debtor' (deudor) y 'Tuition fees
    up to date' (matricula al dia).
  - tiene_apoyo_financiero (bool): directo de 'Scholarship holder' (1 = True).
  - estrato (1..6) e ingreso_hogar_smmlv (0..20): aproximados a partir de la
    ocupacion de los padres ('Mother's/Father's occupation', codigos ISCO) y
    condicion de beca/deuda, alineados con los umbrales DANE 2024.
  - horas_trabajo_semana (0..60) y trabaja_en_area_de_estudio (bool):
    aproximados a partir de 'Daytime/evening attendance' (jornada nocturna = 0)
    y 'Age at enrollment'.
  - tiempo_desplazamiento_min (0..240): de 'Displaced' (1 = 85 min, 0 = 30 min).
  - personas_a_cargo (0..6): de 'Marital status'.
  - apoyo_familiar (1..5): de 'Tuition fees up to date' y estado civil.
  - primera_generacion_universitaria (bool): True si ni la madre ni el padre
    tienen codigos de educacion superior en 'Mother's/Father's qualification'.
"""

import csv
import os
import random

RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_UCI_DEFECTO = os.path.join(
    RAIZ_PROYECTO,
    "data",
    "predict+students+dropout+and+academic+success",
    "data.csv",
)

# Codigos de 'Mother's/Father's qualification' que corresponden a educacion
# superior en el diccionario de variables del dataset UCI (Realinho et al.).
CODIGOS_EDUCACION_SUPERIOR_UCI = frozenset({2, 3, 4, 5, 6, 40, 41, 42, 43, 44})


def mapear_fila_uci(fila):
    """Transforma una fila del CSV de UCI al registro E de 14 campos."""
    g1 = float(fila["Curricular units 1st sem (grade)"])
    g2 = float(fila["Curricular units 2nd sem (grade)"])
    if g1 > 0 and g2 > 0:
        prom_20 = (g1 + g2) / 2.0
    elif g2 > 0:
        prom_20 = g2
    elif g1 > 0:
        prom_20 = g1
    else:
        prom_20 = 0.0
    promedio = round(min(5.0, max(0.0, prom_20 / 4.0)), 2)

    enr1 = int(float(fila["Curricular units 1st sem (enrolled)"]))
    app1 = int(float(fila["Curricular units 1st sem (approved)"]))
    enr2 = int(float(fila["Curricular units 2nd sem (enrolled)"]))
    app2 = int(float(fila["Curricular units 2nd sem (approved)"]))
    noeval1 = int(float(fila["Curricular units 1st sem (without evaluations)"]))
    noeval2 = int(float(fila["Curricular units 2nd sem (without evaluations)"]))

    perdidas = max(0, (enr1 - app1) + (enr2 - app2))
    materias_perdidas = min(8, perdidas)
    if materias_perdidas > 0 and promedio >= 5.0:
        promedio = 4.9

    total_enr = enr1 + enr2
    if total_enr > 0:
        presentadas = max(0, total_enr - (noeval1 + noeval2))
        ratio_pres = min(1.0, presentadas / total_enr)
        ratio_app = min(1.0, (app1 + app2) / total_enr)
        asistencia_pct = round(
            min(100.0, max(0.0, 40.0 + 35.0 * ratio_pres + 25.0 * ratio_app)),
            1,
        )
    else:
        asistencia_pct = 75.0

    semestre = 2 if enr2 > 0 else 1

    debtor = int(float(fila["Debtor"]))
    up_to_date = int(float(fila["Tuition fees up to date"]))
    if debtor == 1 and up_to_date == 0:
        saldo = 8_000_000
    elif up_to_date == 0:
        saldo = 5_500_000
    elif debtor == 1:
        saldo = 3_500_000
    else:
        saldo = 0

    becado = int(float(fila["Scholarship holder"])) == 1
    occ_m = int(float(fila["Mother's occupation"]))
    occ_f = int(float(fila["Father's occupation"]))
    mejor_occ = min(occ_m if occ_m > 0 else 99, occ_f if occ_f > 0 else 99)
    if mejor_occ in (1, 2):
        estrato, ingreso = 4, 5.5
    elif mejor_occ in (3, 4):
        estrato, ingreso = 3, 3.2
    elif mejor_occ in (5, 6, 7, 8):
        estrato, ingreso = 2, 2.0
    else:
        estrato = 1 if (becado or debtor == 1) else 2
        ingreso = 1.3 if estrato == 1 else 2.2

    daytime = int(float(fila["Daytime/evening attendance"]))
    age = int(float(fila["Age at enrollment"]))
    if daytime == 0:
        horas = 36.0
    elif age >= 25:
        horas = 28.0
    elif debtor == 1 or (not becado and estrato <= 2):
        horas = 16.0
    else:
        horas = 0.0
    trabaja_area = (horas > 0.0) and (promedio >= 3.5)

    displaced = int(float(fila["Displaced"]))
    desplazamiento = 85 if displaced == 1 else 30
    marital = int(float(fila["Marital status"]))
    personas = 1 if marital in (2, 4, 5, 6) else 0
    apoyo_fam = 4 if (up_to_date == 1 and marital in (1, 2)) else 2
    qm = int(float(fila["Mother's qualification"]))
    qf = int(float(fila["Father's qualification"]))
    primera_gen = (
        qm not in CODIGOS_EDUCACION_SUPERIOR_UCI
        and qf not in CODIGOS_EDUCACION_SUPERIOR_UCI
    )

    return {
        "promedio": promedio,
        "materias_perdidas": materias_perdidas,
        "asistencia_pct": asistencia_pct,
        "semestre": semestre,
        "saldo_pendiente_cop": saldo,
        "ingreso_hogar_smmlv": ingreso,
        "estrato": estrato,
        "tiene_apoyo_financiero": becado,
        "horas_trabajo_semana": horas,
        "trabaja_en_area_de_estudio": trabaja_area,
        "tiempo_desplazamiento_min": desplazamiento,
        "personas_a_cargo": personas,
        "apoyo_familiar": apoyo_fam,
        "primera_generacion_universitaria": primera_gen,
    }


def cargar_cohorte_uci(n=None, solo_cerrados=True, ruta_csv=None, semilla=None):
    """Lee el CSV real de UCI y devuelve una lista con el mismo formato que
    generador.generar_cohorte(), agregando el campo 'desenlace_real'
    ('Dropout', 'Graduate' o 'Enrolled').

    Cuando 0 < n < total_filas y se proporciona 'semilla', toma una muestra
    aleatoria sin reemplazo reproducible a lo largo de todo el archivo en vez
    de truncar las primeras n filas (que en el CSV estan agrupadas por carrera).
    """
    ruta = RUTA_UCI_DEFECTO if ruta_csv is None else ruta_csv
    if not os.path.exists(ruta):
        raise FileNotFoundError("No se encontro el dataset UCI en: %s" % ruta)

    with open(ruta, "r", encoding="utf-8-sig") as f:
        lector = csv.DictReader(f, delimiter=";")
        filas = [{k.strip(): v.strip() for k, v in r.items()} for r in lector]

    if solo_cerrados:
        filas = [r for r in filas if r.get("Target") in ("Dropout", "Graduate")]

    if n is not None and 0 < n < len(filas):
        if semilla is None:
            filas = filas[:n]
        else:
            rng = random.Random(semilla)
            indices = sorted(rng.sample(range(len(filas)), n))
            filas = [filas[idx] for idx in indices]

    cohorte = []
    for i, fila in enumerate(filas):
        cohorte.append({
            "codigo": "UCI-%04d" % (i + 1),
            "datos": mapear_fila_uci(fila),
            "error_inyectado": None,
            "desenlace_real": fila.get("Target"),
        })
    return cohorte


def _curva_roc(pares, max_puntos=64):
    """Calcula puntos compactos [fpr, tpr] de la curva ROC empirica."""
    desc = sorted(pares, key=lambda x: x[0], reverse=True)
    n_pos = sum(1 for _, _, y in desc if y == 1)
    n_neg = len(desc) - n_pos
    if n_pos == 0 or n_neg == 0:
        return [[0.0, 0.0], [1.0, 1.0]]

    puntos = [[0.0, 0.0]]
    tp = 0
    fp = 0
    i = 0
    total = len(desc)
    while i < total:
        j = i
        while j < total and desc[j][0] == desc[i][0]:
            if desc[j][2] == 1:
                tp += 1
            else:
                fp += 1
            j += 1
        puntos.append([round(fp / n_neg, 4), round(tp / n_pos, 4)])
        i = j

    if len(puntos) <= max_puntos:
        return puntos

    paso = (len(puntos) - 1) / float(max_puntos - 1)
    reducida = [puntos[int(round(k * paso))] for k in range(max_puntos - 1)]
    reducida.append([1.0, 1.0])
    return reducida


def evaluar_contra_desenlace_real(estudiantes):
    """Calcula AUC-ROC (estadistico U de Mann-Whitney), probabilidades medias
    por grupo real y matriz de confusion frente a 'requiere_intervencion' para
    los estudiantes validos que tienen 'desenlace_real' ('Dropout'/'Graduate').
    """
    pares = []
    for est in estudiantes:
        res = est.get("resultado")
        target = est.get("desenlace_real")
        if res is not None and target in ("Dropout", "Graduate"):
            pares.append((res["p"], bool(res["requiere_intervencion"]),
                          1 if target == "Dropout" else 0))

    if not pares:
        return None

    pos = [p for p, _, y in pares if y == 1]
    neg = [p for p, _, y in pares if y == 0]
    if not pos or not neg:
        return None

    # AUC-ROC exacto en O(N log N) ordenando los puntajes
    ordenados = sorted(pares, key=lambda x: x[0])
    n_total = len(ordenados)
    suma_rangos_pos = 0.0
    i = 0
    while i < n_total:
        j = i
        while j < n_total and ordenados[j][0] == ordenados[i][0]:
            j += 1
        rango_medio = (i + 1 + j) / 2.0
        for k in range(i, j):
            if ordenados[k][2] == 1:
                suma_rangos_pos += rango_medio
        i = j

    n_pos = len(pos)
    n_neg = len(neg)
    u = suma_rangos_pos - (n_pos * (n_pos + 1)) / 2.0
    auc = u / (n_pos * n_neg)

    vp = sum(1 for _, interv, y in pares if y == 1 and interv)
    fn = sum(1 for _, interv, y in pares if y == 1 and not interv)
    fp = sum(1 for _, interv, y in pares if y == 0 and interv)
    vn = sum(1 for _, interv, y in pares if y == 0 and not interv)

    return {
        "fuente": "UCI Machine Learning Repository — Realinho et al. (2022)",
        "n_evaluados": len(pares),
        "n_desertores_reales": n_pos,
        "n_graduados_reales": n_neg,
        "tasa_desercion_observada": n_pos / len(pares),
        "p_media_desertores": sum(pos) / n_pos,
        "p_media_graduados": sum(neg) / n_neg,
        "auc_roc": auc,
        "curva_roc": _curva_roc(pares),
        "matriz_confusion": {
            "vp": vp,
            "fn": fn,
            "fp": fp,
            "vn": vn,
            "sensibilidad": vp / n_pos if n_pos else 0.0,
            "especificidad": vn / n_neg if n_neg else 0.0,
            "exactitud": (vp + vn) / len(pares),
        },
    }
