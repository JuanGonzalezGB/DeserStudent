"""
Persistencia del simulador en SQLite (modulo estandar sqlite3, sin ORM).

Reglas que se cumplen en todo el modulo:

  - TODA consulta es parametrizada con '?'. Nunca se concatena un valor
    dentro de una cadena SQL. Los unicos textos que se interpolan son
    nombres de columna de una lista blanca cerrada (ORDEN_PERMITIDO).
  - Cada operacion abre y cierra su propia conexion, asi que el servidor
    Flask puede atender varias peticiones sin compartir una conexion entre
    hilos.
  - La base de datos vive en data/simulador.db y se crea sola. Las
    simulaciones anteriores siguen disponibles al reiniciar el servidor.
"""

import json
import os
import sqlite3
from datetime import datetime

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_SCHEMA = os.path.join(RAIZ, "schema.sql")

# La ruta se puede cambiar con la variable de entorno SIMULADOR_DB (las
# pruebas la usan para trabajar sobre una base temporal).
RUTA_POR_DEFECTO = os.environ.get(
    "SIMULADOR_DB", os.path.join(RAIZ, "data", "simulador.db"))

# Lista blanca de columnas por las que se permite ordenar.
ORDEN_PERMITIDO = {
    "p": "r.p", "nivel": "r.nivel", "codigo": "e.codigo",
    "s_academico": "r.s_academico", "s_financiero": "r.s_financiero",
    "s_laboral": "r.s_laboral", "s_personal": "r.s_personal",
}
DIMENSIONES_VALIDAS = ("academica", "financiera", "laboral", "personal")


# ------------------------------------------------------------ conexion ----
def _ruta(ruta=None):
    return RUTA_POR_DEFECTO if ruta is None else ruta


def conectar(ruta=None):
    """Abre una conexion con claves foraneas activas y filas tipo dict."""
    destino = _ruta(ruta)
    carpeta = os.path.dirname(destino)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    con = sqlite3.connect(destino)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar(ruta=None):
    """Crea las tablas si no existen. Es idempotente."""
    with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
        schema = f.read()
    con = conectar(ruta)
    try:
        con.executescript(schema)
        con.commit()
    finally:
        con.close()


# -------------------------------------------------------- escritura ------
def guardar_simulacion(simulacion, ruta=None, fecha=None):
    """Guarda una simulacion completa y devuelve su id.

    'simulacion' es el dict que devuelve modelo.simular(). Todo se escribe en
    una sola transaccion: o queda la simulacion entera o no queda nada.
    """
    params = simulacion["parametros"]
    resumen = simulacion["resumen"]
    cuando = fecha or datetime.now().isoformat(timespec="seconds")

    # El resumen que se guarda no lleva la lista completa de probabilidades:
    # esa se reconstruye desde la tabla resultados cuando la pagina la pide.
    resumen_guardable = {k: v for k, v in resumen.items() if k != "probabilidades"}

    con = conectar(ruta)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO simulaciones
                 (fecha, semilla, n, tasa_base, parametros_json, b0_calibrado,
                  indice_general, pct_bajo, pct_medio, pct_alto,
                  pct_intervencion, n_validos, n_revision_humana,
                  resumen_json, validacion_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cuando, params["semilla"], params["n"], params["tasa_base"],
             json.dumps(params, ensure_ascii=False), params["b0_calibrado"],
             resumen["indice_general"], resumen["pct_bajo"],
             resumen["pct_medio"], resumen["pct_alto"],
             resumen["pct_intervencion"], resumen["n_validos"],
             resumen["n_revision_humana"],
             json.dumps(resumen_guardable, ensure_ascii=False),
             json.dumps(simulacion["validacion_modelo"], ensure_ascii=False)))
        simulacion_id = cur.lastrowid

        for est in simulacion["estudiantes"]:
            cur.execute(
                """INSERT INTO estudiantes
                     (simulacion_id, codigo, datos_json, valido,
                      motivo_revision, campo_revision, error_inyectado)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (simulacion_id, est["codigo"],
                 json.dumps(est["datos"], ensure_ascii=False),
                 1 if est["valido"] else 0,
                 est["motivo_revision"], est["campo_revision"],
                 est["error_inyectado"]))
            estudiante_id = cur.lastrowid

            res = est["resultado"]
            if res is None:
                continue        # invalido: no recibe probabilidad, por contrato
            s = res["subpuntajes"]
            cur.execute(
                """INSERT INTO resultados
                     (estudiante_id, s_academico, s_financiero, s_laboral,
                      s_personal, p, p5, p95, nivel, factor_principal,
                      problemas_json, requiere_intervencion,
                      intervenciones_json, contribuciones_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (estudiante_id, s["academica"], s["financiera"], s["laboral"],
                 s["personal"], res["p"], res["p5"], res["p95"], res["nivel"],
                 res["factor_principal"],
                 json.dumps(res["problemas"], ensure_ascii=False),
                 1 if res["requiere_intervencion"] else 0,
                 json.dumps(res["intervenciones"], ensure_ascii=False),
                 json.dumps(res["contribuciones"], ensure_ascii=False)))

        con.commit()
        return simulacion_id
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ----------------------------------------------------------- lectura -----
def listar_simulaciones(limite=50, ruta=None):
    """Historial de simulaciones, la mas reciente primero."""
    con = conectar(ruta)
    try:
        filas = con.execute(
            """SELECT id, fecha, semilla, n, tasa_base, b0_calibrado,
                      indice_general, pct_bajo, pct_medio, pct_alto,
                      pct_intervencion, n_validos, n_revision_humana,
                      parametros_json
                 FROM simulaciones
                ORDER BY id DESC
                LIMIT ?""", (limite,)).fetchall()
        salida = []
        for f in filas:
            d = dict(f)
            params = json.loads(d.pop("parametros_json", "{}") or "{}")
            d["origen"] = params.get("origen", "sintetica")
            salida.append(d)
        return salida
    finally:
        con.close()


def obtener_simulacion(simulacion_id, ruta=None):
    """Una simulacion con su resumen, sus parametros y su validacion."""
    con = conectar(ruta)
    try:
        fila = con.execute(
            "SELECT * FROM simulaciones WHERE id = ?",
            (simulacion_id,)).fetchone()
        if fila is None:
            return None

        sim = dict(fila)
        sim["parametros"] = json.loads(sim.pop("parametros_json"))
        sim["resumen"] = json.loads(sim.pop("resumen_json"))
        sim["validacion_modelo"] = json.loads(sim.pop("validacion_json"))

        # La lista de probabilidades alimenta el histograma de la pagina.
        sim["resumen"]["probabilidades"] = [
            f["p"] for f in con.execute(
                """SELECT r.p FROM resultados r
                     JOIN estudiantes e ON e.id = r.estudiante_id
                    WHERE e.simulacion_id = ?
                    ORDER BY r.p""", (simulacion_id,)).fetchall()]
        return sim
    finally:
        con.close()


def listar_estudiantes(simulacion_id, nivel=None, intervencion=None,
                       dimension=None, solo_revision=None, orden="p",
                       descendente=True, ruta=None):
    """Estudiantes de una simulacion, con los filtros de la pagina.

    nivel          -> "bajo" | "medio" | "alto"
    intervencion   -> True / False
    dimension      -> la dimension aparece entre los problemas del estudiante
    solo_revision  -> True devuelve unicamente los que esperan revision humana

    Los invalidos aparecen con resultado None: la pagina los muestra en la
    tabla con su motivo, pero sin probabilidad.
    """
    condiciones = ["e.simulacion_id = ?"]
    valores = [simulacion_id]

    if nivel:
        condiciones.append("r.nivel = ?")
        valores.append(nivel)
    if intervencion is not None:
        condiciones.append("r.requiere_intervencion = ?")
        valores.append(1 if intervencion else 0)
    if dimension:
        if dimension not in DIMENSIONES_VALIDAS:
            raise ValueError("dimension no valida: %r" % (dimension,))
        # El patron va como parametro: no se concatena en el SQL.
        condiciones.append("r.problemas_json LIKE ?")
        valores.append('%"' + dimension + '"%')
    if solo_revision:
        condiciones.append("e.valido = 0")

    columna = ORDEN_PERMITIDO.get(orden, "r.p")
    sentido = "DESC" if descendente else "ASC"

    sql = ("""SELECT e.id, e.codigo, e.datos_json, e.valido,
                     e.motivo_revision, e.campo_revision, e.error_inyectado,
                     r.s_academico, r.s_financiero, r.s_laboral, r.s_personal,
                     r.p, r.p5, r.p95, r.nivel, r.factor_principal,
                     r.problemas_json, r.requiere_intervencion,
                     r.intervenciones_json, r.contribuciones_json
                FROM estudiantes e
                LEFT JOIN resultados r ON r.estudiante_id = e.id
               WHERE """ + " AND ".join(condiciones) +
           " ORDER BY " + columna + " " + sentido + ", e.id ASC")

    con = conectar(ruta)
    try:
        return [_fila_a_estudiante(f)
                for f in con.execute(sql, tuple(valores)).fetchall()]
    finally:
        con.close()


def obtener_estudiante(estudiante_id, ruta=None):
    """Detalle de un estudiante: entrada E, subpuntajes, p, intervalo y plan."""
    con = conectar(ruta)
    try:
        fila = con.execute(
            """SELECT e.id, e.simulacion_id, e.codigo, e.datos_json, e.valido,
                      e.motivo_revision, e.campo_revision, e.error_inyectado,
                      r.s_academico, r.s_financiero, r.s_laboral, r.s_personal,
                      r.p, r.p5, r.p95, r.nivel, r.factor_principal,
                      r.problemas_json, r.requiere_intervencion,
                      r.intervenciones_json, r.contribuciones_json
                 FROM estudiantes e
                 LEFT JOIN resultados r ON r.estudiante_id = e.id
                WHERE e.id = ?""", (estudiante_id,)).fetchone()
        if fila is None:
            return None
        estudiante = _fila_a_estudiante(fila)
        estudiante["simulacion_id"] = fila["simulacion_id"]
        return estudiante
    finally:
        con.close()


def _fila_a_estudiante(fila):
    """Convierte una fila del JOIN en el dict que consume la pagina."""
    estudiante = {
        "id": fila["id"],
        "codigo": fila["codigo"],
        "datos": json.loads(fila["datos_json"]),
        "valido": bool(fila["valido"]),
        "motivo_revision": fila["motivo_revision"],
        "campo_revision": fila["campo_revision"],
        "error_inyectado": fila["error_inyectado"],
        "resultado": None,
    }
    if fila["p"] is None:
        return estudiante

    estudiante["resultado"] = {
        "subpuntajes": {
            "academica": fila["s_academico"],
            "financiera": fila["s_financiero"],
            "laboral": fila["s_laboral"],
            "personal": fila["s_personal"],
        },
        "contribuciones": json.loads(fila["contribuciones_json"]),
        "p": fila["p"],
        "p5": fila["p5"],
        "p95": fila["p95"],
        "nivel": fila["nivel"],
        "factor_principal": fila["factor_principal"],
        "problemas": json.loads(fila["problemas_json"]),
        "requiere_intervencion": bool(fila["requiere_intervencion"]),
        "intervenciones": json.loads(fila["intervenciones_json"]),
    }
    return estudiante


def borrar_todo(ruta=None):
    """Vacia las tres tablas. Solo lo usan las pruebas."""
    con = conectar(ruta)
    try:
        con.execute("DELETE FROM resultados")
        con.execute("DELETE FROM estudiantes")
        con.execute("DELETE FROM simulaciones")
        con.commit()
    finally:
        con.close()
