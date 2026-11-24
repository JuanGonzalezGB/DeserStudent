-- Esquema del simulador de desercion (SQLite).
--
-- Tres tablas que siguen la cadena del modelo:
--   simulaciones -> una corrida completa con sus parametros y su indice general
--   estudiantes  -> la entrada E de cada estudiante y el veredicto del Paso 1
--   resultados   -> la salida de los Pasos 2 y 3 de los estudiantes validos
--
-- Un estudiante que no pasa el Paso 1 existe en 'estudiantes' con valido = 0 y
-- su motivo, y NO tiene fila en 'resultados': el contrato dice que un registro
-- invalido no recibe probabilidad. Esa es la razon de separar las dos tablas.
--
-- Los campos *_json guardan estructuras (el registro de entrada, la lista de
-- problemas, el plan de intervencion) serializadas con json.dumps.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS simulaciones (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha              TEXT    NOT NULL,   -- ISO-8601 local
    semilla            INTEGER NOT NULL,
    n                  INTEGER NOT NULL,
    tasa_base          REAL    NOT NULL,
    parametros_json    TEXT    NOT NULL,   -- umbrales, coeficientes, K, ...
    b0_calibrado       REAL    NOT NULL,
    indice_general     REAL    NOT NULL,   -- probabilidad media de la cohorte
    pct_bajo           REAL    NOT NULL,
    pct_medio          REAL    NOT NULL,
    pct_alto           REAL    NOT NULL,
    pct_intervencion   REAL    NOT NULL,
    n_validos          INTEGER NOT NULL,
    n_revision_humana  INTEGER NOT NULL,
    resumen_json       TEXT    NOT NULL,   -- promedios por dimension, conteos
    validacion_json    TEXT    NOT NULL    -- calibracion, sensibilidad, cara, monotonia
);

CREATE TABLE IF NOT EXISTS estudiantes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    simulacion_id    INTEGER NOT NULL,
    codigo           TEXT    NOT NULL,
    datos_json       TEXT    NOT NULL,     -- la entrada E tal como se genero
    valido           INTEGER NOT NULL,     -- 1 / 0
    motivo_revision  TEXT,                 -- NULL si es valido
    campo_revision   TEXT,
    error_inyectado  TEXT,                 -- tipo de error metido a proposito
    FOREIGN KEY (simulacion_id) REFERENCES simulaciones (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resultados (
    estudiante_id          INTEGER PRIMARY KEY,
    s_academico            REAL    NOT NULL,
    s_financiero           REAL    NOT NULL,
    s_laboral              REAL    NOT NULL,
    s_personal             REAL    NOT NULL,
    p                      REAL    NOT NULL,
    p5                     REAL    NOT NULL,
    p95                    REAL    NOT NULL,
    nivel                  TEXT    NOT NULL,   -- bajo / medio / alto
    factor_principal       TEXT    NOT NULL,
    problemas_json         TEXT    NOT NULL,
    requiere_intervencion  INTEGER NOT NULL,   -- 1 / 0
    intervenciones_json    TEXT    NOT NULL,
    contribuciones_json    TEXT    NOT NULL,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes (id) ON DELETE CASCADE
);

-- Indices para los filtros de la tabla de estudiantes de la pagina.
CREATE INDEX IF NOT EXISTS idx_estudiantes_simulacion
    ON estudiantes (simulacion_id);
CREATE INDEX IF NOT EXISTS idx_resultados_nivel
    ON resultados (nivel);
CREATE INDEX IF NOT EXISTS idx_resultados_p
    ON resultados (p DESC);
