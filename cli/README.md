# Motor + CLI + pytest: guía de ejecución

| Archivo | Qué hace |
|---|---|
| `motor.py` | `ejecutar_paso1`, `ejecutar_paso2`, `ejecutar_paso3` y `procesar_estudiante` (nunca lanza excepciones) |
| `ejecutar_pruebas.py` | CLI: corre un dataset contra un oráculo, imprime la tabla PASA/FALLA y exporta CSV |
| `test_motor.py` | 89 pruebas `pytest`: típicos, bordes, tipos, nulos, rangos, contradicciones, población y cortocircuito |
| `03_dataset_ejemplo.json` | 5 casos rápidos (R01, R02, S06, S13, S15) |
| `04_oraculo_ejemplo.json` | Respuestas esperadas S1, S2 y S3 de esos 5 casos |

Orden de validación del paso 1 (gana el primero que aplique): campo faltante → tipo inválido → fuera de población → valor no permitido → fuera de rango → datos contradictorios. Un `id_estudiante` vacío o solo con espacios cuenta como campo faltante.

## 1. Crear y activar el entorno virtual

Desde esta carpeta (`cli`):

```bash
# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

## 2. Instalar dependencias

```bash
pip install pytest
```

## 3. Ejecutar las pruebas unitarias

```bash
pytest -v
```

Resultado esperado: `89 passed`.

## 4. Ejecutar la CLI

```bash
# 5 casos de ejemplo (compara S1, S2 y S3)
python ejecutar_pruebas.py --dataset 03_dataset_ejemplo.json --oraculo 04_oraculo_ejemplo.json

# Los 20 casos de la ronda 1 (compara la salida final)
python ejecutar_pruebas.py --dataset ../03_dataset.json --oraculo ../04_oraculo.json --salida resultados_ronda1.csv

# Los 15 casos de Gemini (A01 a A15)
python ejecutar_pruebas.py --dataset ../07_dataset_ronda2.json --oraculo ../08_oraculo_ronda2.json --salida resultados_ronda2.csv
```

Resultados obtenidos al ejecutarlo: 5/5, 20/20 y 14/15. El caso que falla, A03 (estrato 1 con 18 SMMLV), es el hueco conocido del contrato. La CLI devuelve código de salida 1 cuando algún caso falla.

## 5. Ver los resultados en CSV

```bash
# Windows
type resultados_ejecucion.csv
# macOS / Linux
cat resultados_ejecucion.csv
```

O ábrelo en Excel. Columnas: `id`, `estado`, `obtenido`, `motivo_falla` y `salida_completa` (S1, S2 y S3 en JSON).
