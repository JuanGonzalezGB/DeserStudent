# Contrato del sistema: simulador de deserción del Portal de Acompañamiento

El sistema recibe el registro de un estudiante (E) y produce una probabilidad
de deserción semestral con su plan de intervención. Igual que el motor de la
entrega anterior, el sistema es una cadena de pasos y **cada paso tiene su
propio contrato de entrada (E) y salida (S)**:

```
E ──> [ Paso 1: Validar registro ] ──> [ Paso 2: Calcular riesgo ] ──> [ Paso 3: Intervenir ]
            │ S1                              │ S2                           │ S3
```

Alrededor de la cadena hay dos usos de Montecarlo que **no** son pasos del
contrato: la generación de la cohorte sintética (produce las E) y la
propagación de la incertidumbre de los coeficientes (enriquece S2 con el
intervalo P5–P95).

## Entrada E (registro del estudiante)

Las cuatro dimensiones, **todos los campos obligatorios**:

| Campo | Tipo | Rango / valores permitidos | Dimensión |
|---|---|---|---|
| promedio | decimal | 0.0 a 5.0 | Académica |
| materias_perdidas | entero | 0 a 8 | Académica |
| asistencia_pct | decimal | 0 a 100 | Académica |
| semestre | entero | 1 a 12 | Académica |
| saldo_pendiente_cop | entero (COP) | 0 a 20.000.000 | Financiera |
| ingreso_hogar_smmlv | decimal | 0 a 20 salarios mínimos | Financiera |
| estrato | entero | 1 a 6 | Financiera |
| tiene_apoyo_financiero | booleano | `true` / `false` | Financiera |
| horas_trabajo_semana | decimal | 0 a 60 | Laboral |
| trabaja_en_area_de_estudio | booleano | `true` / `false` | Laboral |
| tiempo_desplazamiento_min | entero | 0 a 240 | Personal |
| personas_a_cargo | entero | 0 a 6 | Personal |
| apoyo_familiar | entero | 1 a 5 | Personal |
| primera_generacion_universitaria | booleano | `true` / `false` | Personal |

Los rangos son **cerrados**: el mínimo y el máximo exactos son válidos.
Los tipos son **estrictos**: `"4.5"` no es un decimal, `4.0` no es un entero y
`1` no es un booleano. `bool` no cuenta como entero, aunque en Python sea
subclase de `int`.

## Paso 1: Validar registro

- **E:** el registro crudo.
- **S1:** `valido` con el registro, o una salida terminal
  `requiere_revision_humana` con su motivo:

| Motivo | Cuándo |
|---|---|
| `campo_faltante` | falta un campo obligatorio, o viene `None` o en blanco |
| `tipo_invalido` | el tipo no corresponde, o el decimal no es finito (`NaN`, `±inf`) |
| `fuera_de_rango` | el valor no cabe en el rango de la tabla |
| `datos_contradictorios` | la combinación de valores es imposible (ver abajo) |

**Orden de evaluación** (el primero que aplique gana):
`campo_faltante` → `tipo_invalido` → `fuera_de_rango` → `datos_contradictorios`.

**Contradicciones:**

| Regla | Campo reportado |
|---|---|
| estrato ≥ 5 con ingreso < 1 SMMLV | `estrato_ingreso` |
| estrato ≤ 2 con ingreso > 10 SMMLV — **caso A03, hueco cerrado** | `estrato_ingreso` |
| materias perdidas > 0 con promedio = 5.0 | `promedio_materias_perdidas` |

Los umbrales de contradicción son **estrictos**: estrato 5 con exactamente
1 SMMLV es válido, y estrato 2 con exactamente 10 SMMLV también.

**Requerir revisión humana** significa: no calcular ninguna probabilidad y
remitir el caso a un asesor humano del comité de apoyo. El estudiante queda
registrado en la base de datos con su motivo, **sin fila en `resultados`**.

## Paso 2: Calcular riesgo

- **E:** registro válido (S1).
- **S2:** subpuntajes, probabilidad con su intervalo, nivel, contribuciones,
  factor principal y problemas.

**2a. Subpuntaje por dimensión**, `sᵈ ∈ [0, 1]` (0 = sin riesgo, 1 = máximo).
Los pesos de cada dimensión suman 1.0:

| Dimensión | Fórmula |
|---|---|
| sA | `0.40·(1 − promedio/5) + 0.30·min(perdidas/3, 1) + 0.30·(1 − asistencia/100)` |
| sF | `0.35·min(saldo/8.000.000, 1) + 0.30·(1 − min(ingreso/4, 1)) + 0.20·((6 − estrato)/5) + 0.15·(0 si apoyo, 1 si no)` |
| sL | `0.70·i + 0.30·i·(0 si trabaja en su área, 1 si no)`, con `i = min(horas/40, 1)` |
| sP | `0.30·min(desplazamiento/120, 1) + 0.25·min(personas/3, 1) + 0.30·((5 − apoyo_familiar)/4) + 0.15·(1 si primera generación, 0 si no)` |

**2b. Probabilidad de deserción semestral** (regresión logística):

```
p = 1 / (1 + exp(-(b₀ + bA·sA + bF·sF + bL·sL + bP·sP)))
```

Coeficientes por defecto: `bA = 3.0, bF = 2.5, bL = 1.5, bP = 1.2`.
`b₀` **no se inventa**: se calibra por bisección para que la probabilidad
media de la cohorte válida sea igual a `tasa_base_semestral` (0.09 por
defecto).

**2c. Contribución** de cada dimensión al logit: `bᵈ · sᵈ`.
El **factor principal** es la dimensión con la mayor contribución; en caso de
empate, gana el orden académica → financiera → laboral → personal.

**2d. Problemas** del estudiante: las dimensiones con `sᵈ ≥ 0.60`, ordenadas
de mayor a menor subpuntaje. El umbral es **inclusivo**: 0.60 exacto cuenta.

**Intervalo de incertidumbre:** se repite el cálculo K = 1000 veces muestreando
`bᵈ ~ Normal(bᵈ, 0.25·bᵈ)` y se reportan los percentiles **P5** y **P95**.
`p` es la estimación puntual con los coeficientes nominales, y `b₀` se
mantiene fijo en su valor calibrado. Los K vectores de coeficientes se
muestrean una sola vez por simulación y se reutilizan para todos los
estudiantes (números aleatorios comunes), de modo que dos estudiantes con el
mismo perfil obtienen el mismo intervalo.

**Nivel:**

| Nivel | Regla |
|---|---|
| bajo | p < 0.15 |
| medio | 0.15 ≤ p < 0.35 |
| alto | p ≥ 0.35 |

Los umbrales son inclusivos por abajo y configurables por simulación.

## Paso 3: Intervenir

- **E:** nivel, problemas y factor principal (S2).
- **S3:** `requiere_intervencion` y la lista priorizada de intervenciones.

```
requiere_intervencion = (nivel = alto)  o  (nivel = medio y al menos un problema)
```

Un estudiante de nivel **bajo nunca** requiere intervención, aunque tenga una
dimensión problemática.

| Dimensión problemática | Intervención | Acciones |
|---|---|---|
| Académica | `tutoria_academica` | tutoría par en las materias perdidas; plan de recuperación con el docente guía |
| Financiera | `apoyo_financiero` | reestructuración de matrícula en 4 cuotas sin intereses; beca de alimentación; bono de transporte mensual |
| Laboral | `flexibilidad_laboral` | reubicación de horario de clases; oferta de asignaturas en jornada nocturna |
| Personal | `bienestar_universitario` | cita con bienestar universitario; red de apoyo entre pares |

**Prioridad:** la intervención del **factor principal** va primero
(`prioridad = 1`); detrás siguen las demás dimensiones problemáticas en su
orden por subpuntaje.

**Caso de borde:** un estudiante de nivel alto con el riesgo repartido puede
no tener **ninguna** dimensión por encima de 0.60. Requiere intervención pero
su lista de problemas está vacía: en ese caso se le asigna la intervención de
su factor principal, para que nunca quede "requiere intervención" con plan
vacío. Si el factor principal no está entre los problemas pero sí hay otros
problemas, se atienden solo esos: no se inventa una intervención extra.

## Garantías del contrato

1. **Nunca lanza una excepción:** toda entrada termina en `valido` (y recorre
   los Pasos 2 y 3) o en `requiere_revision_humana` con su motivo.
2. **Nunca inventa datos que faltan:** no asume promedio 0, ni saldo 0, ni
   asistencia 100.
3. **Un registro inválido nunca recibe probabilidad.** No se le asigna p = 0
   ni nivel "bajo": no tiene fila en `resultados`.
4. `sᵈ ∈ [0, 1]` y `p ∈ [0, 1]` para cualquier entrada válida, por extrema
   que sea. Garantizado por construcción (pesos que suman 1.0, función
   logística) y probado sobre la cohorte completa.
5. **Monotonía:** empeorar cualquier variable de riesgo nunca baja p.
6. **Calibración:** la probabilidad media de la cohorte válida coincide con la
   tasa base dentro de ± 0.005.
7. **Reproducibilidad:** la misma semilla produce exactamente la misma
   cohorte, el mismo b₀ y los mismos intervalos.
8. **Requiere intervención ⇒ plan no vacío.**
9. Los umbrales son inclusivos tal como están escritos (≥ 0.60 es problema,
   ≥ 0.15 es medio, ≥ 0.35 es alto) y los rangos de E son cerrados.
10. **Nunca hay datos de personas reales:** toda la cohorte es sintética.

## Contrato de la API

| Método y ruta | Entrada | Salida |
|---|---|---|
| `POST /api/simulaciones` | `n` (1–5000), `semilla`, `tasa_base` (0.001–0.999), `umbral_medio`, `umbral_alto`, `k_montecarlo` (1–5000). Todos opcionales | `201` con la simulación guardada |
| `GET /api/simulaciones` | `limite` (1–500) | historial, el más reciente primero |
| `GET /api/simulaciones/<id>` | — | resumen, parámetros y validación del modelo |
| `GET /api/simulaciones/<id>/estudiantes` | `nivel`, `intervencion`, `dimension`, `revision`, `orden`, `sentido` | lista filtrada |
| `GET /api/estudiantes/<id>` | — | detalle con E, subpuntajes, p, P5–P95 y plan |

Garantías de la API:

- Un parámetro mal formado responde **400** con el motivo en
  `{"error": "..."}`, nunca una traza. Es el Paso 1 aplicado a la frontera
  HTTP: `umbral_medio ≥ umbral_alto` se rechaza, igual que `n = 0`.
- Un recurso inexistente responde **404** con JSON.
- Todas las consultas SQL son **parametrizadas**. Los únicos textos que se
  interpolan en el SQL son nombres de columna de una lista blanca cerrada;
  un `orden` desconocido cae al orden por defecto y una `dimension`
  desconocida lanza error antes de tocar la base.
- Las simulaciones **persisten** en `data/simulador.db` y siguen disponibles
  al reiniciar el servidor.
