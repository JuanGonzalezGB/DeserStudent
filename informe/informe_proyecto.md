# Informe del proyecto: Portal de Acompañamiento
## Pruebas de estrés del motor de apoyo y Simulador de deserción estudiantil

Universidad Católica de Colombia · Asignatura *Problems & Solution Design with AI*
Fecha del informe: 24-nov-2026

---

## 1. Resumen ejecutivo

El proyecto aborda un problema de permanencia universitaria: **¿a qué estudiantes hay que acompañar y con qué?** Se desarrolló en dos etapas encadenadas:

| Etapa | Qué es | Resultado |
|---|---|---|
| **A. Pruebas de estrés** | Contrato E→S, dataset simulado, oráculo, motor de recomendación (v1 y v2) y biblioteca de prompts | Ronda 1: 14/20. Ronda 2: 20/20. Casos nuevos de Gemini: 14/15 |
| **B. Simulador de deserción (el PMV)** | Aplicación web (Flask + SQLite + JS) que estima la probabilidad de deserción por estudiante con una regresión logística de 4 dimensiones | 351 pruebas automáticas pasan; AUC-ROC 0,8936 sobre dataset real UCI |

**Mensaje central:** un sistema se vuelve confiable cuando se le define un contrato, se le ataca con casos extremos escritos *antes* de mirar la salida, y se documenta honestamente lo que es supuesto y lo que está verificado.

---

## 2. Problema y objetivo

- **Problema:** la deserción universitaria. Según SPADIES 3.0 (MEN, 2024) la tasa de deserción anual universitaria es **8,65 %** (≈ 4,42 % semestral) y la deserción por cohorte acumulada a semestre 10 es **22,61 %**.
- **Simular primero:** al inicio no había histórico real disponible en el curso y los datos (promedio, deuda, ingreso, estrato) son personales y sensibles. Una cohorte sintética permitió construir y validar todo el sistema sin tocar datos de personas.
- **Datos reales después:** se desarrolló `modelo/datos_reales.py`, un adaptador que convierte datasets externos entrantes al contrato de 14 variables del simulador (ver 4.7). Con él, 3.630 estudiantes reales procesan la misma cadena de 3 pasos y se comparan con su desenlace real.
- **Objetivo:** un prototipo que clasifique el riesgo, explique *por qué* es alto (para elegir la intervención correcta) y se pueda reentrenar con datos reales sin cambiar la arquitectura.

---

## 3. Etapa A: pruebas de estrés del motor de apoyo

### 3.1 Sistema evaluado
Motor que, a partir del perfil de un estudiante, propone un plan de apoyo: reestructuración de matrícula (4 cuotas), beca de alimentación, bono de transporte y tipo de tutoría. Se modela como una cadena de tres pasos, cada uno con su contrato de entrada (E) y salida (S):

```
E ─> [Paso 1: Validar perfil] ─> [Paso 2: Clasificar riesgo] ─> [Paso 3: Recomendar plan]
            S1                            S2                              S3
```

- **Paso 1** produce `valido`, `error(...)` (dato mal formado) o `abstener(...)` (falta dato, datos contradictorios o fuera de población). Abstenerse = no generar plan y remitir a un asesor humano.
- **Paso 2** clasifica riesgo financiero y académico (alto / medio / bajo / sin_datos).
- **Paso 3** otorga beneficios según reglas explícitas con umbrales inclusivos (≤ 2 SMMLV, ≥ 5 km).
- **Garantías:** nunca lanza excepción, nunca inventa datos faltantes, nunca otorga beneficios fuera de la población.

Detalle completo: [01_contrato.md](../01_contrato.md).

### 3.2 Metodología
1. **Contrato** escrito primero (E y S por paso).
2. **Dataset** de 20 casos: 5 típicos (R01–R05) y 15 simulados adversariales (S01–S15), cada uno con "por qué es difícil".
3. **Oráculo** ([04_oraculo.json](../04_oraculo.json)): las respuestas esperadas se fijan *antes* de ejecutar.
4. **Motor v1** escrito deliberadamente solo con el camino feliz; **v2** con las correcciones.
5. **Ejecución** con trazas de S1, S2 y S3 en CSV.
6. **Ronda 2** con 15 casos nuevos (A01–A15) generados por Gemini como auditor externo.

### 3.3 Resultados

| Ronda | Motor | Casos | Pasan | Observación |
|---|---|---|---|---|
| 1 | v1 | 20 | **14** | 6 fallos, todos adversariales |
| 2 | v2 | 20 | **20** | Fallos corregidos |
| 2 (Gemini) | v2 | 15 nuevos | **14** | Falla A03: hueco del contrato |

**Los 6 fallos de la ronda 1 (v1):**

| Caso | Qué pasó |
|---|---|
| S06 | Estrato 6 con ingreso < 1 SMMLV recibió beca completa (debía abstenerse) |
| S08 | Estudiante de posgrado recibió plan (fuera de población) |
| S10 | Ingreso exactamente 2 SMMLV: umbral tratado como exclusivo, sin beca |
| S12 | Saldo absurdo (ceros de más) aceptado en vez de error |
| S13 | Promedio como texto lanzó `TypeError` (violaba "nunca lanza excepción") |
| S15 | Primer semestre sin promedio se rechazó como campo faltante, siendo legítimo |

**Hallazgo de la ronda 2 (A03):** estrato 1 con 18 SMMLV recibe beca de alimentación porque la regla es "ingreso ≤ 2 **o** estrato ≤ 2". Es un hueco del **contrato**, no del código. Corrección propuesta: agregar "estrato ≤ 2 con ingreso > 10 SMMLV" como dato contradictorio.

### 3.4 Herramientas entregadas
- CLI reutilizable ([cli/](../cli/README.md)): `ejecutar_pruebas.py` con `--dataset` y `--oraculo`; devuelve código de salida 1 si algún caso falla. Resultados verificados: 5/5, 20/20 y 14/15.
- Biblioteca de prompts ([02](../02_biblioteca_prompts.md), [07](../07_prompt_reutilizable.md), [11](../11_prompt_claude_code_vscode.md)) y comparación con Gemini ([10](../10_prueba_en_gemini.md)).

---

## 4. Etapa B: Simulador de deserción (PMV)

### 4.1 Descripción
Página web que simula la probabilidad de deserción de una cohorte con **cuatro dimensiones** (Académica, Financiera, Laboral, Personal), muestra el índice general, el riesgo y los problemas de cada estudiante, y si requiere intervención. Los datos persisten en SQLite.

### 4.2 Arquitectura

```
E ─> [Paso 1: validar] ─> [Paso 2: riesgo] ─> [Paso 3: intervención]
      validacion.py        riesgo.py            intervencion.py
                              ▲                        
 generador.py (Montecarlo 1: cohorte)   incertidumbre.py (Montecarlo 2: P5–P95)
```

| Capa | Tecnología / archivos |
|---|---|
| Backend | Flask, API JSON (`/api/simulaciones`, `/api/estudiantes/<id>`, `/api/config`, `/api/evaluar`) |
| Persistencia | SQLite (`schema.sql`: simulaciones / estudiantes / resultados), consultas parametrizadas |
| Modelo | paquete `modelo/` (generador, validación, riesgo, incertidumbre, intervención, sensibilidad, datos reales) |
| Frontend | HTML + JS propio + CSS; gráficas en SVG (ROC, tornado, contribución por dimensión), inspector lateral y What-If |
| Parámetros | Todos en `config.py` (un solo lugar) |

### 4.3 Decisión de modelado: por qué regresión logística y no Montecarlo
El proyecto fue rechazado dos veces por plantear "Montecarlo" como modelo. La corrección:

> **Montecarlo no es un modelo de deserción, es un método de muestreo.** Responde *qué pasa si los supuestos se mueven*. La logística responde *por qué este estudiante está en riesgo*.

- **Regresión logística** estima p ∈ (0,1) por estudiante con contribución interpretable por dimensión (bᵈ·sᵈ).
- **Montecarlo** se usa solo en dos lugares acotados: generar la cohorte sintética y propagar la incertidumbre de los coeficientes (K = 1000, bᵈ ~ Normal(bᵈ, 0,25·bᵈ)) para el intervalo P5–P95.
- Alternativas descartadas: reglas deterministas (no dan probabilidad), supervivencia/Markov (exige datos longitudinales) y ML (exige miles de casos etiquetados).

### 4.4 Cómo se calcula el riesgo
Cuatro subpuntajes transparentes en [0,1] (pesos que suman 1), por ejemplo:

`sA = 0,40·(1 − promedio/5) + 0,30·min(perdidas/3, 1) + 0,30·(1 − asistencia/100)`

La logística los combina con coeficientes supuestos expertos (3,0 · 2,5 · 1,5 · 1,2, marcados `[SUPUESTO]`). El intercepto **b₀ no se inventa: se calibra por bisección** para que la probabilidad media iguale la tasa base. Con n = 500 y semilla 42: b₀ = −4,9475, media 0,09000 vs objetivo 0,09 (diferencia 10⁻⁸). Umbrales: riesgo medio ≥ 0,15, alto ≥ 0,35; problema por dimensión ≥ 0,60.

### 4.5 Validación

| Prueba | Resultado |
|---|---|
| Calibración | Media 0,09000 vs 0,09; diferencia 10⁻⁸ (margen ±0,005): **pasa** |
| Sensibilidad (±50 % por coeficiente) | La financiera mueve el índice 10,13 pp; la académica solo 3,22 pp |
| Validez de cara | 3 de 3 perfiles de referencia coinciden |
| Monotonía | 13 de 13 variables: empeorar una nunca baja p |
| **Dataset real UCI** (N = 3.630 con desenlace cerrado) | **AUC-ROC = 0,8936**; 473 tutorías académicas activadas |
| Pruebas automáticas | **351 pasan** (suite pytest ejecutada hoy, 2,65 s) |

**Hallazgo contraintuitivo:** el coeficiente más grande (académico, 3,0) es el que menos mueve el índice, porque la influencia depende del tamaño típico del subpuntaje (s̄F = 0,43 vs s̄A = 0,11). Si se consiguen datos reales, lo primero a estimar bien es **bF**.

### 4.6 Calibración con fuentes oficiales
Documento: [calibracion_desercion_colombia_corregido.md](../Calibracion%20Y%20FUentes/calibracion_desercion_colombia_corregido.md). Convenciones `[OK]` (verificado), `[VERIFICAR]` y `[SUPUESTO]`. Se corrigió un error del informe original que usaba totales del sistema (9,78 %) como si fueran universitarios (8,65 %). La interfaz ofrece un botón de calibración oficial (tasa semestral 0,0442) además de la tasa base supuesta 0,09.

### 4.7 Adaptador de datasets reales (`datos_reales.py`)
Módulo que transforma el dataset público UCI (Realinho et al., 2022; 4.424 estudiantes) al registro E de 14 campos del simulador y calcula métricas empíricas contra el desenlace observado (`Target`). Se activa con `origen = "uci"` en la API o `simular(origen="uci")`. Verificado: carga **3.630** estudiantes con desenlace cerrado (1.421 Dropout / 2.209 Graduate).

| Variable del contrato | Derivación desde el dataset externo |
|---|---|
| promedio (0–5) | Notas de 1.er y 2.º semestre (escala 0–20) ÷ 4 |
| materias_perdidas | Unidades matriculadas − aprobadas, acotado a 0–8 |
| asistencia_pct | Estimada con presentación a evaluaciones y aprobación |
| saldo_pendiente, apoyo financiero | `Debtor`, `Tuition fees up to date`, `Scholarship holder` |
| estrato, ingreso | **Aproximados** desde ocupación de los padres (ISCO) y umbrales DANE 2024 |
| horas de trabajo, desplazamiento, personas a cargo, apoyo familiar, primera generación | Jornada, edad, `Displaced`, estado civil, formación de los padres |

Los registros pasan por la misma validación (Paso 1), riesgo (Paso 2) e intervención (Paso 3). Resultados: AUC-ROC 0,8936; p media 55,15 % en desertores vs 28,85 % en graduados; 473 tutorías académicas activadas (la cohorte sintética casi no las genera).

---

## 5. Limitaciones y riesgos (honestidad metodológica)

1. **Los coeficientes son supuestos expertos**, no estimados con datos; el intervalo P5–P95 solo mide incertidumbre de coeficientes, no error de forma funcional ni ausencia de datos reales.
2. **Los 5 casos "reales" de la Etapa A son perfiles típicos inventados**, no datos reales anonimizados.
3. **El oráculo de la Etapa A lo elaboró una IA**; debe ser revisado y firmado por el equipo.
4. **En la cohorte sintética casi ningún estudiante cruza el umbral académico** (0–3 casos) y no se emiten tutorías: se decidió no retocar distribuciones para forzarlo.
5. **A03** sigue abierto (hueco del contrato).
6. El AUC 0,8936 corresponde al dataset UCI (Portugal), no a población colombiana, y varias variables (estrato, ingreso, horas de trabajo) se aproximan por mapeo, no se observan directamente.
7. Python verificado en 3.13 y 3.14; el mínimo 3.9 no se ha verificado.

## 6. Trabajo futuro
- Cerrar A03 en contrato y código (ronda 3).
- Reemplazar coeficientes por estimación de máxima verosimilitud con histórico anonimizado; errores estándar en lugar del 25 % supuesto; validación con partición temporal.
- Obtener 5 casos reales anonimizados para la etapa A.
- Integración con las pantallas del prototipo en Stitch.

## 7. Cómo reproducir

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r simulador-desercion/requirements.txt
cd simulador-desercion && pytest -q      # 351 passed
python app.py                            # http://127.0.0.1:5000  -> pulsar "Simular"

# Etapa A
cd .. && python3 ejecutar_pruebas.py     # rondas 1 y 2
cd cli && python ejecutar_pruebas.py --dataset ../03_dataset.json --oraculo ../04_oraculo.json
```

## 8. Mapa del repositorio

| Ruta | Contenido |
|---|---|
| `01_contrato.md` … `11_*.md` | Contrato, prompts, dataset, oráculo, resultados, diagrama, ronda 2, Gemini |
| `motor.py`, `ejecutar_pruebas.py`, `generar_*.py` | Motor v1/v2 y scripts |
| `cli/` | CLI reutilizable de pruebas |
| `simulador-desercion/` | **PMV**: app, modelo, pruebas (351), docs |
| `Calibracion Y FUentes/` | Calibración y fuentes de datasets |
| `presentacion/` | Presentaciones HTML |
