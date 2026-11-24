"""
Pruebas de la API y de la persistencia en SQLite.

Cubren crear, listar y consultar, los filtros de la tabla, los errores 400/404
y -- lo mas importante para la entrega -- que la simulacion siga ahi despues
de cerrar y reabrir la base de datos, como cuando se reinicia el servidor.
"""

import json
import sqlite3

import pytest

import app as modulo_app
import config
import db
import modelo


# Simulaciones pequenas: la API se prueba por su comportamiento, no por su
# tamano. K bajo para que las pruebas corran rapido.
CUERPO_CHICO = {"n": 40, "semilla": 42, "k_montecarlo": 30}


def crear(cliente, **cambios):
    """POST /api/simulaciones con los parametros de prueba."""
    cuerpo = dict(CUERPO_CHICO)
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/simulaciones", json=cuerpo)
    return respuesta


# ------------------------------------------------------------- crear ----
def test_crear_simulacion_devuelve_201_y_el_resumen(cliente):
    respuesta = crear(cliente)
    assert respuesta.status_code == 201

    datos = respuesta.get_json()
    assert datos["id"] >= 1
    assert datos["n"] == 40
    assert datos["semilla"] == 42
    assert set(datos) >= {"id", "fecha", "semilla", "n", "tasa_base",
                          "b0_calibrado", "indice_general", "pct_bajo",
                          "pct_medio", "pct_alto", "pct_intervencion",
                          "parametros", "resumen", "validacion_modelo"}


def test_la_simulacion_creada_viene_calibrada(cliente):
    datos = crear(cliente).get_json()
    calibracion = datos["validacion_modelo"]["calibracion"]
    assert calibracion["ok"] is True
    assert abs(datos["indice_general"] - datos["tasa_base"]) <= \
        config.CALIBRACION_MARGEN_OK


def test_los_porcentajes_de_nivel_suman_cien(cliente):
    datos = crear(cliente).get_json()
    total = datos["pct_bajo"] + datos["pct_medio"] + datos["pct_alto"]
    assert total == pytest.approx(100.0)


def test_crear_sin_cuerpo_usa_los_valores_por_defecto(cliente):
    respuesta = cliente.post("/api/simulaciones", json={"n": 20,
                                                        "k_montecarlo": 10})
    datos = respuesta.get_json()
    assert respuesta.status_code == 201
    assert datos["semilla"] == config.SEMILLA_POR_DEFECTO
    assert datos["tasa_base"] == config.TASA_BASE_SEMESTRAL
    assert datos["parametros"]["umbral_medio"] == config.UMBRAL_MEDIO
    assert datos["parametros"]["umbral_alto"] == config.UMBRAL_ALTO


def test_la_misma_semilla_da_el_mismo_resultado_por_la_api(cliente):
    primera = crear(cliente).get_json()
    segunda = crear(cliente).get_json()
    assert primera["id"] != segunda["id"]
    assert primera["b0_calibrado"] == segunda["b0_calibrado"]
    assert primera["indice_general"] == segunda["indice_general"]
    assert primera["pct_alto"] == segunda["pct_alto"]


def test_semillas_distintas_dan_resultados_distintos(cliente):
    a = crear(cliente, semilla=1).get_json()
    b = crear(cliente, semilla=2).get_json()
    assert a["b0_calibrado"] != b["b0_calibrado"]


# -------------------------------------------- errores de entrada (400) --
@pytest.mark.parametrize("cuerpo,fragmento", [
    ({"n": 0}, "n"),
    ({"n": -5}, "n"),
    ({"n": 999999}, "n"),
    ({"n": "muchos"}, "entero"),
    ({"n": 1.5}, "entero"),
    ({"tasa_base": 0}, "tasa_base"),
    ({"tasa_base": 1.5}, "tasa_base"),
    ({"tasa_base": "alta"}, "numerico"),
    ({"umbral_medio": 0.5, "umbral_alto": 0.2}, "menor"),
    ({"umbral_medio": 0.4, "umbral_alto": 0.4}, "menor"),
    ({"k_montecarlo": 0}, "k_montecarlo"),
    ({"semilla": -1}, "semilla"),
])
def test_parametros_invalidos_responden_400(cliente, cuerpo, fragmento):
    completo = dict(CUERPO_CHICO)
    completo.update(cuerpo)
    respuesta = cliente.post("/api/simulaciones", json=completo)
    assert respuesta.status_code == 400
    assert fragmento in respuesta.get_json()["error"]


def test_un_cuerpo_que_no_es_objeto_responde_400(cliente):
    respuesta = cliente.post("/api/simulaciones", json=[1, 2, 3])
    assert respuesta.status_code == 400
    assert "objeto JSON" in respuesta.get_json()["error"]


# ------------------------------------------------------------ listar ---
def test_el_historial_empieza_vacio(cliente):
    datos = cliente.get("/api/simulaciones").get_json()
    assert datos["simulaciones"] == []


def test_el_historial_lista_lo_creado_mas_reciente_primero(cliente):
    crear(cliente, semilla=1)
    crear(cliente, semilla=2)
    crear(cliente, semilla=3)

    datos = cliente.get("/api/simulaciones").get_json()
    assert len(datos["simulaciones"]) == 3
    ids = [s["id"] for s in datos["simulaciones"]]
    assert ids == sorted(ids, reverse=True)
    assert datos["simulaciones"][0]["semilla"] == 3


def test_el_limite_del_historial_se_respeta(cliente):
    for semilla in range(4):
        crear(cliente, semilla=semilla)
    datos = cliente.get("/api/simulaciones?limite=2").get_json()
    assert len(datos["simulaciones"]) == 2


def test_limite_invalido_responde_400(cliente):
    respuesta = cliente.get("/api/simulaciones?limite=0")
    assert respuesta.status_code == 400


# ---------------------------------------------------------- consultar --
def test_consultar_una_simulacion_trae_la_validacion_del_modelo(cliente):
    creada = crear(cliente).get_json()
    datos = cliente.get("/api/simulaciones/%d" % creada["id"]).get_json()

    validacion = datos["validacion_modelo"]
    assert set(validacion) == {"calibracion", "sensibilidad",
                               "validez_de_cara", "monotonia", "ok"}
    assert len(validacion["sensibilidad"]["filas"]) == 4
    assert len(validacion["validez_de_cara"]["perfiles"]) == 3
    assert validacion["monotonia"]["n_variables"] == 13
    assert validacion["ok"] is True


def test_el_resumen_trae_las_probabilidades_para_el_histograma(cliente):
    creada = crear(cliente).get_json()
    datos = cliente.get("/api/simulaciones/%d" % creada["id"]).get_json()
    probabilidades = datos["resumen"]["probabilidades"]
    assert len(probabilidades) == datos["n_validos"]
    assert probabilidades == sorted(probabilidades)
    assert all(0.0 <= p <= 1.0 for p in probabilidades)


def test_simulacion_inexistente_responde_404(cliente):
    respuesta = cliente.get("/api/simulaciones/9999")
    assert respuesta.status_code == 404
    assert "no existe" in respuesta.get_json()["error"]


def test_estudiante_inexistente_responde_404(cliente):
    respuesta = cliente.get("/api/estudiantes/9999")
    assert respuesta.status_code == 404


# ------------------------------------------------ tabla de estudiantes --
def test_listar_estudiantes_trae_toda_la_cohorte(cliente):
    creada = crear(cliente).get_json()
    datos = cliente.get(
        "/api/simulaciones/%d/estudiantes" % creada["id"]).get_json()
    assert datos["total"] == 40
    assert len(datos["estudiantes"]) == 40


def test_los_estudiantes_vienen_ordenados_por_p_descendente(cliente):
    creada = crear(cliente).get_json()
    datos = cliente.get(
        "/api/simulaciones/%d/estudiantes" % creada["id"]).get_json()
    ps = [e["resultado"]["p"] for e in datos["estudiantes"] if e["resultado"]]
    assert ps == sorted(ps, reverse=True)


def test_orden_ascendente_por_p(cliente):
    creada = crear(cliente).get_json()
    datos = cliente.get("/api/simulaciones/%d/estudiantes?sentido=asc"
                        % creada["id"]).get_json()
    ps = [e["resultado"]["p"] for e in datos["estudiantes"] if e["resultado"]]
    assert ps == sorted(ps)


@pytest.mark.parametrize("nivel", ["bajo", "medio", "alto"])
def test_filtro_por_nivel(cliente, nivel):
    creada = crear(cliente, n=200).get_json()
    datos = cliente.get("/api/simulaciones/%d/estudiantes?nivel=%s"
                        % (creada["id"], nivel)).get_json()
    for est in datos["estudiantes"]:
        assert est["resultado"]["nivel"] == nivel


def test_filtro_por_intervencion(cliente):
    creada = crear(cliente, n=200).get_json()

    con = cliente.get("/api/simulaciones/%d/estudiantes?intervencion=true"
                      % creada["id"]).get_json()
    sin = cliente.get("/api/simulaciones/%d/estudiantes?intervencion=false"
                      % creada["id"]).get_json()

    assert all(e["resultado"]["requiere_intervencion"]
               for e in con["estudiantes"])
    assert all(not e["resultado"]["requiere_intervencion"]
               for e in sin["estudiantes"])
    # Juntos deben dar todos los estudiantes validos.
    assert con["total"] + sin["total"] == creada["n_validos"]


def test_filtro_por_dimension_problematica(cliente):
    creada = crear(cliente, n=200).get_json()
    datos = cliente.get("/api/simulaciones/%d/estudiantes?dimension=financiera"
                        % creada["id"]).get_json()
    assert datos["total"] > 0
    for est in datos["estudiantes"]:
        assert "financiera" in est["resultado"]["problemas"]


def test_filtro_de_revision_humana(cliente):
    creada = crear(cliente, n=200).get_json()
    datos = cliente.get("/api/simulaciones/%d/estudiantes?revision=true"
                        % creada["id"]).get_json()
    assert datos["total"] == creada["n_revision_humana"]
    for est in datos["estudiantes"]:
        assert est["valido"] is False
        assert est["resultado"] is None
        assert est["motivo_revision"]


def test_filtros_invalidos_responden_400(cliente):
    creada = crear(cliente).get_json()
    base = "/api/simulaciones/%d/estudiantes?" % creada["id"]
    assert cliente.get(base + "nivel=altisimo").status_code == 400
    assert cliente.get(base + "dimension=deportiva").status_code == 400
    assert cliente.get(base + "intervencion=quizas").status_code == 400


def test_estudiantes_de_una_simulacion_inexistente_responde_404(cliente):
    assert cliente.get("/api/simulaciones/9999/estudiantes").status_code == 404


# ---------------------------------------------- detalle del estudiante --
def test_detalle_de_un_estudiante_valido(cliente):
    creada = crear(cliente).get_json()
    lista = cliente.get("/api/simulaciones/%d/estudiantes?intervencion=true"
                        % creada["id"]).get_json()["estudiantes"]
    assert lista, "la simulacion de prueba deberia tener intervenciones"

    detalle = cliente.get("/api/estudiantes/%d" % lista[0]["id"]).get_json()
    resultado = detalle["resultado"]

    assert detalle["simulacion_id"] == creada["id"]
    assert detalle["valido"] is True
    assert set(detalle["datos"]) == set(config.CAMPOS_OBLIGATORIOS)
    assert set(resultado["subpuntajes"]) == set(config.DIMENSIONES)
    assert 0.0 <= resultado["p5"] <= resultado["p95"] <= 1.0
    assert resultado["p5"] <= resultado["p"] <= resultado["p95"]
    assert resultado["nivel"] in ("bajo", "medio", "alto")
    assert resultado["intervenciones"]
    assert resultado["intervenciones"][0]["prioridad"] == 1


def test_detalle_de_un_estudiante_en_revision_no_trae_probabilidad(cliente):
    creada = crear(cliente, n=200).get_json()
    lista = cliente.get("/api/simulaciones/%d/estudiantes?revision=true"
                        % creada["id"]).get_json()["estudiantes"]
    assert lista, "con n=200 debe haber registros danados a proposito"

    detalle = cliente.get("/api/estudiantes/%d" % lista[0]["id"]).get_json()
    assert detalle["resultado"] is None
    assert detalle["motivo_revision"] in (
        "campo_faltante", "tipo_invalido", "fuera_de_rango",
        "datos_contradictorios")


# ------------------------------------------------------- la pagina -----
def test_la_raiz_sirve_la_pagina(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_data(as_text=True)
    assert "Simulador de probabilidad de deserción" in cuerpo
    assert "/static/app.js" in cuerpo


def test_los_estaticos_se_sirven(cliente):
    for ruta in ("/static/app.js", "/static/styles.css"):
        assert cliente.get(ruta).status_code == 200


def test_una_ruta_que_no_existe_responde_json(cliente):
    respuesta = cliente.get("/api/lo-que-sea")
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"]


# ======================================================= PERSISTENCIA ===
def test_la_simulacion_sobrevive_al_reinicio_del_servidor(ruta_db):
    """Lo que pide la entrega: los datos persisten en la base SQL.

    Se crea una simulacion con una aplicacion, se tira esa aplicacion y se
    levanta otra nueva sobre el mismo archivo .db, igual que al reiniciar el
    servidor.
    """
    primera = modulo_app.create_app(ruta_db=ruta_db)
    with primera.test_client() as cliente:
        creada = cliente.post("/api/simulaciones", json=CUERPO_CHICO).get_json()
        simulacion_id = creada["id"]
        total_estudiantes = cliente.get(
            "/api/simulaciones/%d/estudiantes" % simulacion_id
        ).get_json()["total"]

    # Nueva aplicacion, nueva conexion: solo queda el archivo en disco.
    segunda = modulo_app.create_app(ruta_db=ruta_db)
    with segunda.test_client() as cliente:
        historial = cliente.get("/api/simulaciones").get_json()["simulaciones"]
        assert [s["id"] for s in historial] == [simulacion_id]

        recuperada = cliente.get("/api/simulaciones/%d" % simulacion_id).get_json()
        assert recuperada["indice_general"] == creada["indice_general"]
        assert recuperada["b0_calibrado"] == creada["b0_calibrado"]
        assert recuperada["validacion_modelo"]["ok"] is True

        estudiantes = cliente.get(
            "/api/simulaciones/%d/estudiantes" % simulacion_id).get_json()
        assert estudiantes["total"] == total_estudiantes


def test_varias_simulaciones_conviven_en_la_base(ruta_db):
    db.inicializar(ruta_db)
    ids = []
    for semilla in (1, 2, 3):
        simulacion = modelo.simular(n=20, semilla=semilla, k_montecarlo=10)
        ids.append(db.guardar_simulacion(simulacion, ruta_db))

    assert len(set(ids)) == 3
    for simulacion_id in ids:
        recuperada = db.obtener_simulacion(simulacion_id, ruta_db)
        assert recuperada is not None
        assert len(db.listar_estudiantes(simulacion_id, ruta=ruta_db)) == 20


def test_cada_estudiante_guardado_conserva_su_entrada_y_su_salida(ruta_db):
    db.inicializar(ruta_db)
    simulacion = modelo.simular(n=30, semilla=42, k_montecarlo=20)
    simulacion_id = db.guardar_simulacion(simulacion, ruta_db)

    guardados = {e["codigo"]: e
                 for e in db.listar_estudiantes(simulacion_id, ruta=ruta_db)}
    for original in simulacion["estudiantes"]:
        recuperado = guardados[original["codigo"]]
        assert recuperado["datos"] == original["datos"]
        assert recuperado["valido"] == original["valido"]

        if original["resultado"] is None:
            assert recuperado["resultado"] is None
            continue
        assert recuperado["resultado"]["p"] == pytest.approx(
            original["resultado"]["p"])
        assert recuperado["resultado"]["nivel"] == original["resultado"]["nivel"]
        assert recuperado["resultado"]["problemas"] == \
            original["resultado"]["problemas"]


def test_los_invalidos_no_tienen_fila_en_resultados(ruta_db):
    """Por contrato, un registro invalido no recibe probabilidad."""
    db.inicializar(ruta_db)
    simulacion = modelo.simular(n=100, semilla=42, k_montecarlo=10)
    simulacion_id = db.guardar_simulacion(simulacion, ruta_db)

    con = sqlite3.connect(ruta_db)
    try:
        invalidos = con.execute(
            """SELECT COUNT(*) FROM estudiantes e
                 LEFT JOIN resultados r ON r.estudiante_id = e.id
                WHERE e.simulacion_id = ? AND e.valido = 0
                  AND r.estudiante_id IS NOT NULL""",
            (simulacion_id,)).fetchone()[0]
        total_resultados = con.execute(
            """SELECT COUNT(*) FROM resultados r
                 JOIN estudiantes e ON e.id = r.estudiante_id
                WHERE e.simulacion_id = ?""", (simulacion_id,)).fetchone()[0]
    finally:
        con.close()

    assert invalidos == 0
    assert total_resultados == simulacion["resumen"]["n_validos"]


def test_inicializar_es_idempotente(ruta_db):
    db.inicializar(ruta_db)
    db.inicializar(ruta_db)
    assert db.listar_simulaciones(ruta=ruta_db) == []


def test_una_dimension_invalida_en_db_lanza_value_error(ruta_db):
    """db.py no acepta un nombre de dimension arbitrario en el filtro."""
    db.inicializar(ruta_db)
    with pytest.raises(ValueError):
        db.listar_estudiantes(1, dimension="'; DROP TABLE estudiantes; --",
                              ruta=ruta_db)


def test_el_orden_solo_admite_columnas_de_la_lista_blanca(ruta_db):
    """Un 'orden' desconocido cae al orden por defecto, no se interpola."""
    db.inicializar(ruta_db)
    simulacion = modelo.simular(n=20, semilla=42, k_montecarlo=10)
    simulacion_id = db.guardar_simulacion(simulacion, ruta_db)

    estudiantes = db.listar_estudiantes(
        simulacion_id, orden="p; DROP TABLE resultados", ruta=ruta_db)
    assert len(estudiantes) == 20
    # La tabla sigue viva.
    assert db.obtener_simulacion(simulacion_id, ruta_db) is not None


def test_los_json_guardados_son_json_valido(ruta_db):
    db.inicializar(ruta_db)
    simulacion = modelo.simular(n=20, semilla=42, k_montecarlo=10)
    simulacion_id = db.guardar_simulacion(simulacion, ruta_db)

    con = sqlite3.connect(ruta_db)
    try:
        fila = con.execute(
            """SELECT parametros_json, resumen_json, validacion_json
                 FROM simulaciones WHERE id = ?""",
            (simulacion_id,)).fetchone()
    finally:
        con.close()

    for texto in fila:
        assert isinstance(json.loads(texto), dict)


# =========================================== MEJORAS DE BACKEND Y API ===
def test_migracion_idempotente_de_esquema_anterior(tmp_path):
    """Una base creada con el esquema viejo gana las columnas nuevas sola."""
    ruta_vieja = str(tmp_path / "vieja.db")
    con = sqlite3.connect(ruta_vieja)
    con.executescript("""
        CREATE TABLE simulaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL,
            semilla INTEGER NOT NULL, n INTEGER NOT NULL, tasa_base REAL NOT NULL,
            parametros_json TEXT NOT NULL, b0_calibrado REAL NOT NULL,
            indice_general REAL NOT NULL, pct_bajo REAL NOT NULL,
            pct_medio REAL NOT NULL, pct_alto REAL NOT NULL,
            pct_intervencion REAL NOT NULL, n_validos INTEGER NOT NULL,
            n_revision_humana INTEGER NOT NULL, resumen_json TEXT NOT NULL,
            validacion_json TEXT NOT NULL
        );
        CREATE TABLE estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simulacion_id INTEGER NOT NULL, codigo TEXT NOT NULL,
            datos_json TEXT NOT NULL, valido INTEGER NOT NULL,
            motivo_revision TEXT, campo_revision TEXT, error_inyectado TEXT
        );
        CREATE TABLE resultados (
            estudiante_id INTEGER PRIMARY KEY,
            s_academico REAL NOT NULL, s_financiero REAL NOT NULL,
            s_laboral REAL NOT NULL, s_personal REAL NOT NULL,
            p REAL NOT NULL, p5 REAL NOT NULL, p95 REAL NOT NULL,
            nivel TEXT NOT NULL, factor_principal TEXT NOT NULL,
            problemas_json TEXT NOT NULL, requiere_intervencion INTEGER NOT NULL,
            intervenciones_json TEXT NOT NULL, contribuciones_json TEXT NOT NULL
        );
    """)
    con.close()

    db.inicializar(ruta_vieja)
    sim = modelo.simular(n=25, semilla=42, k_montecarlo=10)
    sim_id = db.guardar_simulacion(sim, ruta_vieja)
    lista = db.listar_estudiantes(sim_id, ruta=ruta_vieja)
    assert len(lista) == 25


def test_persiste_mensaje_revision_y_desenlace_real_uci(cliente):
    sim_sint = crear(cliente, n=120).get_json()
    rev = cliente.get(
        "/api/simulaciones/%d/estudiantes?revision=true" % sim_sint["id"]
    ).get_json()["estudiantes"]
    assert rev
    assert rev[0]["mensaje_revision"]

    sim_uci = cliente.post(
        "/api/simulaciones",
        json={"origen": "uci", "n": 60, "semilla": 42,
              "tasa_base": 0.3915, "k_montecarlo": 20}
    ).get_json()
    assert "curva_roc" in sim_uci["resumen"]["evaluacion_real"]
    assert len(sim_uci["resumen"]["evaluacion_real"]["curva_roc"]) >= 2

    est_uci = cliente.get(
        "/api/simulaciones/%d/estudiantes?desenlace=Dropout" % sim_uci["id"]
    ).get_json()
    assert est_uci["total"] > 0
    assert all(e["desenlace_real"] == "Dropout" for e in est_uci["estudiantes"])

    detalle = cliente.get(
        "/api/estudiantes/%d" % est_uci["estudiantes"][0]["id"]
    ).get_json()
    assert detalle["desenlace_real"] == "Dropout"


def test_submuestreo_uci_es_reproducible_con_semilla():
    from modelo import datos_reales

    a1 = datos_reales.cargar_cohorte_uci(n=40, semilla=10)
    a2 = datos_reales.cargar_cohorte_uci(n=40, semilla=10)
    b = datos_reales.cargar_cohorte_uci(n=40, semilla=99)
    assert a1 == a2
    assert a1 != b


def test_orden_por_severidad_de_nivel_y_nulos_al_final(cliente):
    sim = crear(cliente, n=250).get_json()
    desc = cliente.get(
        "/api/simulaciones/%d/estudiantes?orden=nivel&sentido=desc" % sim["id"]
    ).get_json()["estudiantes"]
    pesos = {"alto": 3, "medio": 2, "bajo": 1}
    validos_desc = [pesos[e["resultado"]["nivel"]]
                    for e in desc if e["resultado"] is not None]
    assert validos_desc == sorted(validos_desc, reverse=True)
    # Los invalidos quedan al final tanto en DESC como en ASC.
    assert desc[-1]["resultado"] is None

    asc = cliente.get(
        "/api/simulaciones/%d/estudiantes?orden=p&sentido=asc" % sim["id"]
    ).get_json()["estudiantes"]
    assert asc[0]["resultado"] is not None
    assert asc[-1]["resultado"] is None


def test_paginacion_y_busqueda_en_estudiantes(cliente):
    sim = crear(cliente, n=50).get_json()
    pag = cliente.get(
        "/api/simulaciones/%d/estudiantes?limite=15&offset=10" % sim["id"]
    ).get_json()
    assert pag["total"] == 50
    assert len(pag["estudiantes"]) == 15

    busq = cliente.get(
        "/api/simulaciones/%d/estudiantes?buscar=UNA-0005" % sim["id"]
    ).get_json()
    assert busq["total"] == 1
    assert busq["estudiantes"][0]["codigo"] == "UNA-0005"


def test_endpoint_config_expone_contrato_oficial(cliente):
    cfg = cliente.get("/api/config").get_json()
    assert cfg["dimensiones"] == list(config.DIMENSIONES)
    assert set(cfg["campos_obligatorios"]) == set(config.CAMPOS_OBLIGATORIOS)
    assert cfg["coeficientes"] == dict(config.COEFICIENTES)
    assert set(cfg["intervenciones"]) == set(config.DIMENSIONES)


def test_endpoint_evaluar_individual_y_comparacion_whatif(cliente, registro):
    sim = crear(cliente, n=80, k_montecarlo=50).get_json()
    est_ref = cliente.get(
        "/api/simulaciones/%d/estudiantes?limite=1" % sim["id"]
    ).get_json()["estudiantes"][0]

    # Evaluar el mismo registro contra la simulacion activa reproduce p, p5 y p95
    resp = cliente.post("/api/evaluar", json={
        "simulacion_id": sim["id"],
        "k_montecarlo": 50,
        "datos": est_ref["datos"],
    })
    assert resp.status_code == 200
    ev = resp.get_json()
    assert ev["valido"] is True
    assert ev["resultado"]["p"] == pytest.approx(est_ref["resultado"]["p"])
    assert ev["resultado"]["p5"] == pytest.approx(est_ref["resultado"]["p5"])
    assert ev["resultado"]["p95"] == pytest.approx(est_ref["resultado"]["p95"])

    # Comparacion antes vs despues (reduciendo saldo y dando apoyo financiero)
    mejorado = dict(registro, saldo_pendiente_cop=0, tiene_apoyo_financiero=True)
    comp = cliente.post("/api/evaluar", json={
        "datos": mejorado,
        "datos_base": registro,
        "k_montecarlo": 40,
    }).get_json()
    assert comp["delta_p"] < 0

    # Caso invalido (A03): devuelve valido=False con mensaje legible, no 400/500
    invalido = dict(registro, estrato=1, ingreso_hogar_smmlv=15.0)
    rechazo = cliente.post("/api/evaluar", json={"datos": invalido}).get_json()
    assert rechazo["valido"] is False
    assert rechazo["motivo_revision"] == "datos_contradictorios"
    assert rechazo["mensaje_revision"]


@pytest.mark.parametrize("escenario", [
    {"n": 500, "semilla": 42, "tasa_base": 0.09, "umbral_medio": 0.15, "umbral_alto": 0.35, "k_montecarlo": 20},
    {"n": 500, "semilla": 42, "tasa_base": 0.0442, "umbral_medio": 0.08, "umbral_alto": 0.20, "k_montecarlo": 20},
    {"origen": "uci", "n": 3630, "semilla": 42, "tasa_base": 0.3915, "umbral_medio": 0.35, "umbral_alto": 0.65, "k_montecarlo": 20},
    {"origen": "uci", "n": 500, "semilla": 42, "tasa_base": 0.0442, "umbral_medio": 0.05, "umbral_alto": 0.15, "k_montecarlo": 20},
])
def test_los_cuatro_escenarios_pasan_toda_la_validacion_incluida_cara(escenario):
    sim = modelo.simular(**escenario)
    assert sim["validacion_modelo"]["calibracion"]["ok"] is True
    assert sim["validacion_modelo"]["validez_de_cara"]["ok"] is True
    assert sim["validacion_modelo"]["monotonia"]["ok"] is True
    assert sim["validacion_modelo"]["ok"] is True
