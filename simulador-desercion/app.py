"""
Backend del simulador de desercion: API JSON + la pagina.

Endpoints:

  POST /api/simulaciones                      crea y guarda una simulacion
  GET  /api/simulaciones                      historial
  GET  /api/simulaciones/<id>                 resumen + validacion del modelo
  GET  /api/simulaciones/<id>/estudiantes     tabla con filtros y paginacion
  GET  /api/estudiantes/<id>                  detalle de un estudiante
  POST /api/evaluar                           evalua un registro (What-If)
  GET  /api/config                            contrato y parametros de config.py
  GET  /                                      la pagina (static/index.html)

Toda entrada de la API se valida antes de simular: un parametro mal formado
responde 400 con el motivo, nunca una traza de error. Es la misma filosofia
del Paso 1 aplicada a la frontera HTTP.

Para arrancar:  python app.py   ->   http://127.0.0.1:5000
"""

import os

from flask import Flask, jsonify, request, send_from_directory

import config
import db
import modelo

RAIZ = os.path.dirname(os.path.abspath(__file__))

# Topes de la API para que una peticion no tumbe el servidor.
N_MAXIMO = 5000
K_MAXIMO = 5000


class ErrorDeEntrada(Exception):
    """Parametro invalido en una peticion. Se traduce a un 400."""


# --------------------------------------------- validacion de parametros --
def _entero(cuerpo, clave, por_defecto, minimo, maximo):
    valor = cuerpo.get(clave, por_defecto)
    if isinstance(valor, bool) or not isinstance(valor, int):
        # Se acepta el texto que manda un formulario HTML, pero solo si es
        # un entero limpio.
        try:
            valor = int(str(valor).strip())
        except (TypeError, ValueError):
            raise ErrorDeEntrada("'%s' debe ser un entero" % clave)
    if valor < minimo or valor > maximo:
        raise ErrorDeEntrada("'%s' debe estar entre %s y %s"
                             % (clave, minimo, maximo))
    return valor


def _decimal(cuerpo, clave, por_defecto, minimo, maximo):
    valor = cuerpo.get(clave, por_defecto)
    if isinstance(valor, bool):
        raise ErrorDeEntrada("'%s' debe ser numerico" % clave)
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        raise ErrorDeEntrada("'%s' debe ser numerico" % clave)
    if valor != valor:                      # NaN
        raise ErrorDeEntrada("'%s' debe ser numerico" % clave)
    if valor < minimo or valor > maximo:
        raise ErrorDeEntrada("'%s' debe estar entre %s y %s"
                             % (clave, minimo, maximo))
    return valor


def leer_parametros(cuerpo):
    """Valida y normaliza el cuerpo de POST /api/simulaciones."""
    if cuerpo is None:
        cuerpo = {}
    if not isinstance(cuerpo, dict):
        raise ErrorDeEntrada("el cuerpo debe ser un objeto JSON")

    n = _entero(cuerpo, "n", config.N_POR_DEFECTO, 1, N_MAXIMO)
    semilla = _entero(cuerpo, "semilla", config.SEMILLA_POR_DEFECTO, 0, 2**31 - 1)
    tasa_base = _decimal(cuerpo, "tasa_base", config.TASA_BASE_SEMESTRAL,
                         0.001, 0.999)
    umbral_medio = _decimal(cuerpo, "umbral_medio", config.UMBRAL_MEDIO,
                            0.001, 0.999)
    umbral_alto = _decimal(cuerpo, "umbral_alto", config.UMBRAL_ALTO,
                           0.001, 0.999)
    k = _entero(cuerpo, "k_montecarlo", config.K_MONTECARLO, 1, K_MAXIMO)

    if umbral_medio >= umbral_alto:
        raise ErrorDeEntrada("'umbral_medio' debe ser menor que 'umbral_alto'")

    origen = cuerpo.get("origen")
    if origen in (None, "", "sintetica"):
        origen = None
    elif origen == "uci":
        origen = "uci"
    else:
        raise ErrorDeEntrada("'origen' debe ser 'sintetica' o 'uci'")

    salida = {"n": n, "semilla": semilla, "tasa_base": tasa_base,
              "umbral_medio": umbral_medio, "umbral_alto": umbral_alto,
              "k_montecarlo": k}
    if origen is not None:
        salida["origen"] = origen
    return salida


def _booleano_opcional(valor):
    """Lee un filtro booleano de la query string. None si no viene."""
    if valor is None or valor == "":
        return None
    texto = str(valor).strip().lower()
    if texto in ("1", "true", "si", "sí"):
        return True
    if texto in ("0", "false", "no"):
        return False
    raise ErrorDeEntrada("'intervencion' debe ser true o false")


# ------------------------------------------------------------- la app ----
def create_app(ruta_db=None):
    """Crea la aplicacion. 'ruta_db' permite a las pruebas usar otra base."""
    app = Flask(__name__, static_folder=os.path.join(RAIZ, "static"),
                static_url_path="/static")
    app.config["RUTA_DB"] = ruta_db
    app.json.ensure_ascii = False       # tildes legibles en las respuestas
    app.json.sort_keys = False

    db.inicializar(ruta_db)

    def ruta():
        return app.config["RUTA_DB"]

    # ---------------------------------------------------------- pagina --
    @app.get("/")
    def pagina():
        return send_from_directory(app.static_folder, "index.html")

    # ------------------------------------------------------------- API --
    @app.post("/api/simulaciones")
    def crear_simulacion():
        cuerpo = request.get_json(silent=True)
        if cuerpo is None and request.form:
            cuerpo = request.form.to_dict()
        params = leer_parametros(cuerpo)

        simulacion = modelo.simular(**params)
        simulacion_id = db.guardar_simulacion(simulacion, ruta())

        guardada = db.obtener_simulacion(simulacion_id, ruta())
        return jsonify(guardada), 201

    @app.get("/api/simulaciones")
    def historial():
        limite = _entero(request.args, "limite", 50, 1, 500)
        return jsonify({"simulaciones": db.listar_simulaciones(limite, ruta())})

    @app.get("/api/simulaciones/<int:simulacion_id>")
    def detalle_simulacion(simulacion_id):
        simulacion = db.obtener_simulacion(simulacion_id, ruta())
        if simulacion is None:
            return jsonify({"error": "no existe la simulacion %d"
                                     % simulacion_id}), 404
        return jsonify(simulacion)

    @app.get("/api/simulaciones/<int:simulacion_id>/estudiantes")
    def estudiantes_de_simulacion(simulacion_id):
        if db.obtener_simulacion(simulacion_id, ruta()) is None:
            return jsonify({"error": "no existe la simulacion %d"
                                     % simulacion_id}), 404

        nivel = request.args.get("nivel") or None
        if nivel is not None and nivel not in ("bajo", "medio", "alto"):
            raise ErrorDeEntrada("'nivel' debe ser bajo, medio o alto")

        dimension = request.args.get("dimension") or None
        if dimension is not None and dimension not in config.DIMENSIONES:
            raise ErrorDeEntrada("'dimension' debe ser una de %s"
                                 % (", ".join(config.DIMENSIONES),))

        desenlace = request.args.get("desenlace") or None
        if desenlace is not None and desenlace not in db.DESENLACES_VALIDOS:
            raise ErrorDeEntrada("'desenlace' debe ser uno de %s"
                                 % (", ".join(db.DESENLACES_VALIDOS),))

        limite = None
        offset = 0
        if request.args.get("limite") not in (None, ""):
            limite = _entero(request.args, "limite", 50, 1, N_MAXIMO)
        if request.args.get("offset") not in (None, ""):
            offset = _entero(request.args, "offset", 0, 0, 100_000)

        total, estudiantes = db.consultar_estudiantes(
            simulacion_id,
            nivel=nivel,
            intervencion=_booleano_opcional(request.args.get("intervencion")),
            dimension=dimension,
            solo_revision=_booleano_opcional(request.args.get("revision")),
            desenlace=desenlace,
            buscar=request.args.get("buscar"),
            orden=request.args.get("orden", "p"),
            descendente=request.args.get("sentido", "desc") != "asc",
            limite=limite,
            offset=offset,
            ruta=ruta())
        return jsonify({"simulacion_id": simulacion_id,
                        "total": total,
                        "estudiantes": estudiantes})

    @app.get("/api/estudiantes/<int:estudiante_id>")
    def detalle_estudiante(estudiante_id):
        estudiante = db.obtener_estudiante(estudiante_id, ruta())
        if estudiante is None:
            return jsonify({"error": "no existe el estudiante %d"
                                     % estudiante_id}), 404
        return jsonify(estudiante)

    @app.get("/api/config")
    def obtener_configuracion():
        return jsonify(modelo.configuracion_publica())

    @app.post("/api/evaluar")
    def evaluar_individual():
        cuerpo = request.get_json(silent=True)
        if not isinstance(cuerpo, dict):
            raise ErrorDeEntrada("el cuerpo debe ser un objeto JSON")
        if "datos" not in cuerpo:
            raise ErrorDeEntrada("falta el objeto 'datos' del estudiante")

        base_params = {
            "b0": modelo.B0_REFERENCIA_DEFECTO,
            "umbral_medio": config.UMBRAL_MEDIO,
            "umbral_alto": config.UMBRAL_ALTO,
            "k_montecarlo": 250,
            "semilla": config.SEMILLA_POR_DEFECTO,
        }

        if cuerpo.get("simulacion_id") is not None:
            sim_id = _entero(cuerpo, "simulacion_id", 1, 1, 10_000_000)
            sim = db.obtener_simulacion(sim_id, ruta())
            if sim is None:
                return jsonify({"error": "no existe la simulacion %d"
                                         % sim_id}), 404
            p_sim = sim["parametros"]
            base_params["b0"] = p_sim["b0_calibrado"]
            base_params["umbral_medio"] = p_sim["umbral_medio"]
            base_params["umbral_alto"] = p_sim["umbral_alto"]
            base_params["semilla"] = p_sim["semilla"]
            base_params["k_montecarlo"] = min(p_sim["k_montecarlo"], 1000)

        b0 = _decimal(cuerpo, "b0", base_params["b0"],
                      config.CALIBRACION_B0_MIN, config.CALIBRACION_B0_MAX)
        umbral_medio = _decimal(cuerpo, "umbral_medio",
                                base_params["umbral_medio"], 0.001, 0.999)
        umbral_alto = _decimal(cuerpo, "umbral_alto",
                               base_params["umbral_alto"], 0.001, 0.999)
        if umbral_medio >= umbral_alto:
            raise ErrorDeEntrada("'umbral_medio' debe ser menor que 'umbral_alto'")
        k = _entero(cuerpo, "k_montecarlo", base_params["k_montecarlo"],
                    1, K_MAXIMO)
        semilla = _entero(cuerpo, "semilla", base_params["semilla"],
                          0, 2**31 - 1)

        actual = modelo.evaluar_estudiante(
            cuerpo["datos"], b0=b0, umbral_medio=umbral_medio,
            umbral_alto=umbral_alto, k_montecarlo=k, semilla=semilla)

        if "datos_base" in cuerpo and cuerpo["datos_base"] is not None:
            base = modelo.evaluar_estudiante(
                cuerpo["datos_base"], b0=b0, umbral_medio=umbral_medio,
                umbral_alto=umbral_alto, k_montecarlo=k, semilla=semilla)
            actual["comparacion_base"] = base
            if actual["resultado"] and base["resultado"]:
                actual["delta_p"] = (actual["resultado"]["p"]
                                     - base["resultado"]["p"])

        return jsonify(actual)

    # ------------------------------------------------ manejo de errores --
    @app.errorhandler(ErrorDeEntrada)
    def _error_de_entrada(exc):
        return jsonify({"error": str(exc)}), 400

    @app.errorhandler(404)
    def _no_encontrado(_exc):
        return jsonify({"error": "recurso no encontrado"}), 404

    @app.errorhandler(405)
    def _metodo_no_permitido(_exc):
        return jsonify({"error": "metodo no permitido en esta ruta"}), 405

    return app


app = create_app()


if __name__ == "__main__":
    print("Simulador de desercion -> http://127.0.0.1:5000")
    print("Base de datos: %s" % db.RUTA_POR_DEFECTO)
    app.run(host="127.0.0.1", port=5000, debug=False)
