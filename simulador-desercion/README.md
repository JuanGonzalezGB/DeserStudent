# Simulador de probabilidad de deserción

Portal de Acompañamiento — Universidad Católica de Colombia
Entrega del 3.er corte · asignatura *Problems & Solution Design with AI*

Página web que simula la probabilidad de deserción de una cohorte de
estudiantes usando **cuatro dimensiones** (Académica, Financiera, Laboral y
Personal), muestra el índice de riesgo general, el riesgo y los problemas de
cada estudiante, y si requiere intervención. Los datos persisten en SQLite.

**El modelo de riesgo es una regresión logística.** Montecarlo se usa en dos
lugares acotados: generar la cohorte sintética y propagar la incertidumbre de
los coeficientes. La justificación completa está en
[`docs/justificacion_modelo.md`](docs/justificacion_modelo.md).

---

## Cómo ejecutarlo

Desde la **raíz del proyecto** (`practica-pruebas-estres/`, la carpeta que
contiene `simulador-desercion/`), donde se creará el entorno virtual `.venv`.

Requiere **Python 3** con `venv` y `pip` (probado en 3.13.1 y 3.14.8; el
mínimo 3.9 **no** se ha verificado). En Windows, instalar Python desde
python.org marcando la opción del lanzador `py`.

### Windows (PowerShell)

```powershell
# 1. Crear el entorno virtual (solo la primera vez)
py -3 -m venv .venv

# 2. Activarlo
.\.venv\Scripts\Activate.ps1
# Si PowerShell bloquea la activación, solo para esta sesión:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Instalar dependencias (solo la primera vez)
pip install -r simulador-desercion\requirements.txt

# 4. Correr las pruebas  -> 340 passed
cd simulador-desercion
pytest -q

# 5. Arrancar el servidor
python app.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r simulador-desercion/requirements.txt
cd simulador-desercion
pytest -q
python app.py
```

> El entorno virtual **no viene en la entrega**: un `.venv` guarda rutas
> absolutas de la máquina donde se creó y no funciona al copiarlo. Por eso se
> recrea con los pasos de arriba, que es para lo que existe
> `requirements.txt`. La base de datos `data/simulador.db` sí viene, con una
> simulación de referencia ya cargada; si se borra, se crea sola.

Luego abrir **http://127.0.0.1:5000** y pulsar **Simular**.
Para detener el servidor: `Ctrl + C`.

---

## Estructura

```
simulador-desercion/
├── app.py                  Backend Flask: API JSON + sirve la página
├── db.py                   SQLite (sqlite3), consultas parametrizadas
├── schema.sql              simulaciones / estudiantes / resultados
├── config.py               TODOS los parámetros del modelo, en un solo lugar
├── conftest.py             sys.path y fixtures de pytest
├── requirements.txt        flask, pytest (y nada más)
├── modelo/
│   ├── __init__.py         orquesta la cadena completa: simular()
│   ├── generador.py        Montecarlo 1: cohorte sintética
│   ├── datos_reales.py     cargador del dataset real UCI + validación AUC-ROC
│   ├── validacion.py       Paso 1: validar el registro
│   ├── riesgo.py           Paso 2: subpuntajes + logística + calibración de b₀
│   ├── incertidumbre.py    Montecarlo 2: intervalo P5–P95
│   ├── intervencion.py     Paso 3: decide intervención y prioridad
│   └── sensibilidad.py     validación del modelo (4 comprobaciones)
├── static/
│   ├── index.html          una sola página, en español
│   ├── app.js              JavaScript propio; gráficas en SVG
│   └── styles.css
├── tests/                  340 pruebas, sin skip ni xfail
│   ├── test_validacion.py  cada tipo de error y cada contradicción (A03)
│   ├── test_riesgo.py      rangos, monotonía, calibración
│   ├── test_generador.py   reproducibilidad, dependencias, errores inyectados
│   ├── test_intervencion.py cada regla y la prioridad
│   ├── test_api.py         crear/listar/consultar + persistencia tras reinicio
│   └── test_estres.py      15 registros adversariales
├── docs/
│   ├── justificacion_modelo.md   por qué logística y no Montecarlo
│   ├── contrato_simulador.md     E → S1 → S2 → S3
│   ├── guia_sustentacion.md      guion de 5 puntos para el profesor
│   └── manual_de_estudio.md      manual completo del proyecto y ejemplos
└── data/
    └── simulador.db        se crea solo en la primera ejecución
```

---

## El modelo en una pantalla

```
E ──> [ Paso 1: validar ] ──> [ Paso 2: riesgo ] ──> [ Paso 3: intervención ]
          validacion.py           riesgo.py              intervencion.py
                                incertidumbre.py
```

**Paso 1.** Campo faltante, tipo inválido (incluido `NaN`), fuera de rango o
dato contradictorio → el estudiante **no recibe probabilidad** y queda como
`requiere_revision_humana` con su motivo. Nunca se inventa un dato.

**Paso 2.** Cuatro subpuntajes `sᵈ ∈ [0,1]` con fórmulas transparentes, y

```
p = 1 / (1 + exp(-(b₀ + 3.0·sA + 2.5·sF + 1.5·sL + 1.2·sP)))
```

`b₀` **no se inventa**: se calibra por bisección para que la probabilidad
media de la cohorte sea igual a la tasa base semestral (0.09 por defecto).
El intervalo **P5–P95** sale de repetir el cálculo K = 1000 veces muestreando
`bᵈ ~ Normal(bᵈ, 0.25·bᵈ)`.

**Paso 3.** `requiere_intervencion` = nivel alto, o nivel medio con al menos
una dimensión problemática (`sᵈ ≥ 0.60`). Una intervención por dimensión
problemática, con el factor principal de primero.

---

## Resultado de referencia (n = 500, semilla = 42)

| Medida | Valor |
|---|---|
| b₀ calibrado | −4.947534 |
| Índice de riesgo general | 9.00% (objetivo 9.00%, diferencia 10⁻⁸) |
| Riesgo bajo / medio / alto | 83.92% / 13.61% / 2.47% |
| Requieren intervención | 15.26% (74 de 485) |
| En revisión humana | 15 de 500 (3% inyectado a propósito) |
| Validación del modelo | calibración ✔ · validez de cara 3/3 ✔ · monotonía 13/13 ✔ |

---

## API

| Método y ruta | Para qué |
|---|---|
| `POST /api/simulaciones` | crea una simulación (`n`, `semilla`, `tasa_base`, umbrales, `k_montecarlo`) |
| `GET /api/simulaciones` | historial |
| `GET /api/simulaciones/<id>` | resumen + validación del modelo |
| `GET /api/simulaciones/<id>/estudiantes` | tabla, con filtros `nivel`, `intervencion`, `dimension`, `revision` |
| `GET /api/estudiantes/<id>` | detalle: subpuntajes, p, intervalo y plan |

Ejemplo:

```bash
curl -X POST http://127.0.0.1:5000/api/simulaciones \
     -H "Content-Type: application/json" \
     -d '{"n": 500, "semilla": 42, "tasa_base": 0.09}'
```

---

## Notas

- **Dependencias:** solo `flask` y `pytest`. Sin pandas, sin numpy, sin ORM.
  Las gráficas son SVG dibujado con JavaScript propio, así que la página
  funciona sin internet.
- **Datos sintéticos:** ningún registro corresponde a una persona real.
- **Reproducibilidad:** la misma semilla da exactamente la misma cohorte, el
  mismo b₀ y los mismos intervalos.
- **Revisar antes de entregar:** las marcas `[SUPUESTO]` y `[VERIFICAR]` están
  reunidas en la sección 8 de `docs/justificacion_modelo.md`.
- Este simulador **no modifica nada** del proyecto de la entrega anterior.
