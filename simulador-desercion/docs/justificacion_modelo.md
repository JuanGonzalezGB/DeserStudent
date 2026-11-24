# Justificación del modelo de simulación

Simulador de probabilidad de deserción — Portal de Acompañamiento
Universidad Católica de Colombia · Entrega del 3.er corte

> Las marcas **[SUPUESTO]** y **[VERIFICAR]** señalan todo lo que no está
> respaldado por un dato real y que debe confirmarse antes de la entrega.
> Están reunidas en la sección 8.

---

## 1. El problema y por qué hay que simular

El Portal de Acompañamiento necesita responder una pregunta operativa:
**¿a qué estudiantes hay que acompañar este semestre, y con qué?** Para eso
hace falta estimar, por estudiante, la probabilidad de que abandone sus
estudios, y saber *por qué* es alta, porque la intervención depende de la
causa: una tutoría no resuelve una deuda de matrícula.

Hay dos razones por las que esto se **simula** en lugar de calcularse con
datos reales:

1. **No hay datos reales disponibles.** No existe en el curso un histórico de
   matrícula, notas y retiros de la universidad con el que entrenar nada. Sin
   datos, un modelo aprendido no se puede estimar: solo se puede *especificar*.
2. **Privacidad de los estudiantes.** Los datos que el modelo necesita —
   promedio, deuda, ingreso del hogar, estrato, personas a cargo — son datos
   personales sensibles. Trabajar con registros reales exigiría consentimiento
   y anonimización. Una cohorte sintética permite construir y validar todo el
   sistema sin tocar un solo dato de una persona real.

La simulación cumple entonces dos funciones: **generar una población de
prueba** plausible y **ejercitar el modelo de riesgo** de punta a punta para
poder validarlo antes de que existan datos reales.

---

## 2. Modelos considerados

| Criterio | Reglas deterministas | Montecarlo puro | **Regresión logística** | Supervivencia / Markov por semestre | ML (random forest, redes) |
|---|---|---|---|---|---|
| **Interpretabilidad** | Muy alta: son `if`. Pero no dice cuánto pesa cada factor | Baja: no hay un modelo que interpretar, solo un muestreador | **Alta: cada coeficiente dice cuánto pesa cada dimensión** | Media: pesos interpretables, más la forma del riesgo en el tiempo | Baja: requiere explicadores externos (SHAP) |
| **Datos que necesita** | Ninguno: se escriben a mano | Distribuciones supuestas | **Ninguno para especificarlo; reentrenable con histórico** | Historias completas por estudiante, con el semestre del retiro | Miles de casos etiquetados |
| **Salida probabilística** | No: devuelve una etiqueta (alto/medio/bajo) | Sí, pero es la distribución que se le metió | **Sí: p ∈ (0,1) por estudiante** | Sí: p por semestre y curva de supervivencia | Sí, pero mal calibrada sin ajuste |
| **Explicación para intervenir** | Débil: la regla que disparó, sin magnitud | Nula | **Directa: contribución bᵈ·sᵈ por dimensión** | Buena | Indirecta |
| **Facilidad de validar** | Trivial pero vacía: se valida contra sí misma | No hay qué calibrar | **Calibrable contra la tasa base; sensibilidad y monotonía comprobables** | Validable, pero exige datos longitudinales | Exige partición train/test, que aquí no hay |
| **Veredicto** | Insuficiente: no da probabilidad | **No es un modelo de deserción** (ver sección 4) | **ELEGIDO** | Sobredimensionado: pide datos que no existen | Imposible: no hay datos para entrenar |

---

## 3. Modelo elegido: regresión logística

El riesgo se estima con una **regresión logística** sobre cuatro subpuntajes
de dimensión:

```
sA, sF, sL, sP ∈ [0, 1]          (subpuntajes por dimensión)

p = 1 / (1 + exp(-(b₀ + bA·sA + bF·sF + bL·sL + bP·sP)))
```

Cuatro razones:

1. **Es interpretable por construcción.** Cada coeficiente responde "¿cuánto
   pesa esta dimensión?" en una sola cifra, y la contribución `bᵈ · sᵈ` dice,
   para *este* estudiante, qué dimensión está empujando su riesgo. Eso es
   exactamente lo que el Paso 3 necesita para decidir la intervención.
2. **Devuelve una probabilidad entre 0 y 1**, no una etiqueta. La función
   logística garantiza ese rango para cualquier combinación de entradas, por
   extrema que sea — y está probado (`test_riesgo.py`).
3. **Es el enfoque más común en la literatura de predicción de deserción**
   universitaria, por su interpretabilidad y porque la variable respuesta es
   binaria (deserta / no deserta) en un horizonte fijo (un semestre). Tres
   estudios empíricos verificados (`[OK]`) en Colombia y América Latina que
   emplean modelos logit / multinomiales sobre deserción universitaria son:
   - **Tapasco-Alzate, O. A., Ruiz-Ortega, F. J., Osorio-García, D., & Ramírez-Ramírez, D. (2019).**
     *Deserción estudiantil: incidencia de factores institucionales relacionados con los procesos de admisión.*
     Educación y Educadores, 22(1), 81–100. https://doi.org/10.5294/edu.2019.22.1.5
     (Universidad de Caldas, cohortes 2010–2012, $N = 6.421$, deserción 41,7%;
     reporta *Odds Ratios* significativos para admisión en segunda opción OR = 2,99,
     puntaje ICFES ponderado OR = 0,97 y edad de ingreso OR = 1,03).
   - **Arismendy Fuentes, C. A., Morales Parrado, N. L., & Díaz Castro, J. (2020).**
     *Análisis de la deserción temprana y sus factores explicativos en la Universidad de los Llanos con datos de ingreso, 2015-2.*
     Investigaciones Andina, 22(40), 99–121. https://www.redalyc.org/articulo.oa?id=239075120007
     (Universidad de los Llanos, $N = 574$; coeficientes logit para puntaje Saber 11
     $\beta = -0,0755$, repitencia escolar $\beta = +0,727$ [OR = 2,07] y padres
     separados $\beta = +0,486$ [OR = 1,63]).
   - **Jordana Schmidt, B., Boero, P., & Méndez Vera, J. A. (2023).**
     *Factores que influyen en la deserción universitaria: El caso de una universidad estatal chilena.*
     Revista Portuguesa de Educação, 36(1), e23002. https://doi.org/10.21814/rpe.23401
     (Universidad de La Frontera, $N = 2.222$; identifica promedio general acumulado
     PGA, programa de apoyo académico PAAU [OR = 0,505] y preferencia de carrera
     [OR = 0,639] como predictores determinantes).
   - Adicionalmente, en `data/Factors Associated with Dropout and Graduation Amo/Tabla_3_estimacion_del_modelo.xlsx`
     (Mendeley Data, `9rw37dmx6s`, universidad pública en Cúcuta, Colombia) se
     dispone de la estimación de riesgo relativo (RRR) donde tener `Promedio < 3.0`
     arroja $\beta = 2,218$ ($\text{RRR ajustado} = 9,188, p < 0,001$), `< 100% créditos aprobados`
     arroja $\beta = 0,599$ ($\text{RRR} = 1,820$) y `Jornada nocturna` arroja
     $\beta = 0,710$ ($\text{RRR} = 2,034$).
4. **Se puede reentrenar con datos reales cuando existan.** Hoy los
   coeficientes son supuestos expertos; el día que la universidad entregue
   histórico anonimizado, se estiman por máxima verosimilitud **sin cambiar
   nada más del sistema**: ni la estructura de 3 pasos, ni la base de datos,
   ni la página. Es la propiedad que ningún otro candidato de la tabla ofrece
   al mismo costo.

### 3.1 Las cuatro fórmulas de subpuntaje

Cada subpuntaje es un promedio ponderado de variables normalizadas a [0,1],
donde 0 = sin riesgo y 1 = riesgo máximo. **Los pesos de cada dimensión suman
exactamente 1.0**, lo que garantiza `sᵈ ∈ [0,1]` sin recortes artificiales
(probado en `test_riesgo.py::test_los_pesos_de_cada_dimension_suman_uno`).
Todos los pesos y saturaciones están en `config.py`.

**Académica**
```
sA = 0.40·(1 − promedio/5)
   + 0.30·min(materias_perdidas/3, 1)
   + 0.30·(1 − asistencia/100)
```

**Financiera**
```
sF = 0.35·min(saldo/8.000.000, 1)
   + 0.30·(1 − min(ingreso_SMMLV/4, 1))
   + 0.20·((6 − estrato)/5)
   + 0.15·(0 si tiene apoyo financiero, 1 si no)
```

**Laboral**
```
intensidad = min(horas_trabajo/40, 1)
sL = 0.70·intensidad + 0.30·intensidad·(0 si trabaja en su área, 1 si no)
```
La desalineación se multiplica por la intensidad a propósito: a quien trabaja
0 horas no se le puede penalizar por "no trabajar en su área". Sin ese
factor, un estudiante que no trabaja tendría sL = 0.30.

**Personal**
```
sP = 0.30·min(desplazamiento_min/120, 1)
   + 0.25·min(personas_a_cargo/3, 1)
   + 0.30·((5 − apoyo_familiar)/4)
   + 0.15·(1 si es primera generación, 0 si no)
```

### 3.2 b₀ no se inventa: se calibra

Los coeficientes de dimensión son supuestos expertos **[SUPUESTO]**:

| Coeficiente | Valor | Lectura |
|---|---|---|
| bA (académica) | 3.0 | la dimensión de mayor peso unitario |
| bF (financiera) | 2.5 | |
| bL (laboral) | 1.5 | |
| bP (personal) | 1.2 | |

El intercepto **b₀ no es un supuesto**: se despeja por **bisección** para que
la probabilidad media de la cohorte sea igual a la tasa base de deserción
semestral (`tasa_base_semestral`, por defecto 0.09). La probabilidad media
crece de forma monótona con b₀, así que la bisección converge siempre.

Esto es lo que ancla el modelo a la realidad: los coeficientes dicen cómo se
**reparte** el riesgo entre estudiantes, y b₀ fija el **nivel** global para
que coincida con la tasa observada. Sin esta calibración, el modelo produciría
probabilidades cuyo promedio no significaría nada.

> **[OK] Verificación en SPADIES 3.0 (MEN, 2024):** En las estadísticas oficiales
> de **SPADIES 3.0** (subsistema integrado al SNIES del Ministerio de Educación
> Nacional, corte 2024 publicado en sep-2026), la **Tasa de Deserción Anual (TDA)**
> para el **nivel universitario** es **8,65%** (2023: 7,82%; total del sistema
> incluyendo TyT: 9,78%), y la deserción acumulada por cohorte a semestre 10 es
> **22,61%**. Bajo riesgo semestral constante, $\text{TDA} = 8,65\%$ equivale a
> $p_{\text{sem}} = 1 - \sqrt{1 - 0,0865} \approx \mathbf{0,0442}$ (**4,42%**).
> Sin embargo, en el primer semestre el riesgo observado ronda el **~9,7%**
> (Informe LEE 74, PUJ). Por ello, el simulador conserva `0.09` como valor por
> defecto de la simulación de referencia `[SUPUESTO]` (representativo de primer
> año / alerta temprana) e incluye en la interfaz el botón directo de
> **Calibración oficial SPADIES 3.0 (`tasa_base = 0.0442`)**.

---

## 4. Respuesta a la pregunta del profesor sobre Montecarlo

> *"¿De verdad Montecarlo es adecuado para esto?"*

**No, si se usa como modelo de deserción. Sí, en los dos lugares donde se usa
aquí.** La confusión de la entrega anterior fue tratar a Montecarlo como si
fuera el modelo.

**Montecarlo no es un modelo: es un método de muestreo.** Consiste en estimar
una cantidad repitiendo un sorteo aleatorio muchas veces y promediando. No
contiene ninguna teoría sobre la deserción. Por sí solo **no puede explicar
por qué un estudiante deserta**, y por lo tanto no puede decir qué
intervención le sirve — que es justamente lo que el portal necesita decidir.
Un Montecarlo "a secas" solo devuelve la distribución que se le metió por
dentro: si se supone que el 9% deserta, devolverá el 9%, sin aportar nada.

En este simulador, **el modelo que explica el riesgo es la regresión
logística**, y Montecarlo aparece en dos usos concretos y acotados, cada uno
en su propio módulo:

| # | Dónde | Qué muestrea | Para qué | Módulo |
|---|---|---|---|---|
| 1 | Generación de la cohorte | Las variables de entrada E de cada estudiante (estrato, ingreso, horas de trabajo, asistencia, promedio…) | Construir una población de prueba plausible cuando no hay datos reales | `modelo/generador.py` |
| 2 | Propagación de la incertidumbre | Los coeficientes `bᵈ ~ Normal(bᵈ, 0.25·bᵈ)`, K = 1000 veces | Reportar P5–P95 junto a cada p, para no vender como exacto algo que no lo es | `modelo/incertidumbre.py` |

En los dos casos el problema **es** de muestreo, y por eso Montecarlo es la
herramienta correcta. En ninguno de los dos Montecarlo decide quién deserta:
el uso 1 produce las entradas, el uso 2 produce las barras de error. La
estimación puntual la produce la logística.

Una frase para la sustentación:

> *"Montecarlo responde 'qué pasa si los supuestos se mueven'.
> La regresión logística responde 'por qué este estudiante está en riesgo'.
> Son preguntas distintas y por eso están en módulos distintos."*

**Nota honesta sobre el alcance del uso 2.** El intervalo P5–P95 cuantifica
únicamente la incertidumbre *de los coeficientes*, bajo el supuesto de que su
desviación es del 25%. **No** cuantifica el error por no tener datos reales,
ni el error por haber elegido esta forma funcional. Un intervalo estrecho no
significa que el modelo sea correcto. Eso no se arregla muestreando: se
arregla con datos (sección 7).

---

## 5. Marco teórico de las cuatro dimensiones

Las cuatro dimensiones no son arbitrarias: corresponden a los dos marcos
clásicos de la literatura de deserción, más el sistema de medición oficial
colombiano.

**Tinto (1975) — modelo de integración estudiantil.** La permanencia depende
del grado de **integración académica** (rendimiento, compromiso con el
estudio) e **integración social** del estudiante en la institución. De aquí
salen la **dimensión académica** (promedio, materias perdidas, asistencia) y
parte de la **dimensión personal** (apoyo familiar, condición de primera
generación, que afecta la integración).
**[OK]** Referencia verificada (APA 7):
Tinto, V. (1975). Dropout from higher education: A theoretical synthesis of
recent research. *Review of Educational Research*, *45*(1), 89–125.
https://doi.org/10.3102/00346543045001089

**Bean y Metzner (1985) — modelo de desgaste del estudiante no tradicional.**
Para estudiantes que trabajan, mayores o que no viven en el campus, los
**factores externos** al aula (empleo, finanzas, responsabilidades
familiares, tiempo de desplazamiento) pesan más que la integración social. De
aquí salen la **dimensión financiera**, la **dimensión laboral** y el resto de
la **dimensión personal**. Este marco es el que justifica que el simulador
mire horas de trabajo y personas a cargo, y no solo notas.
**[OK]** Referencia verificada (APA 7):
Bean, J. P., & Metzner, B. S. (1985). A conceptual model of nontraditional
undergraduate student attrition. *Review of Educational Research*, *55*(4),
485–540. https://doi.org/10.3102/00346543055004485

**SPADIES 3.0 (Ministerio de Educación Nacional de Colombia)** — *Sistema para la
Prevención y Análisis de la Deserción en las Instituciones de Educación Superior*,
subsistema integrado al SNIES que mide y reporta oficialmente la deserción en el
país (definición: estudiante sin matrícula durante dos o más periodos consecutivos,
no graduado ni retirado por motivos disciplinarios).
**[OK]** Cifras oficiales verificadas (indicadores 2024, nivel universitario):
- **Tasa de deserción anual (TDA) universitaria:** **8,65%** (conversión a tasa
  semestral bajo riesgo constante: $p_{\text{sem}} = 1 - \sqrt{1 - 0,0865} \approx \mathbf{0,0442}$).
- **Tasa de ausencia intersemestral (TAI) universitaria:** **12,08%** (no debe
  usarse como tasa de deserción porque incluye ausentes temporales que reingresan).
- **Deserción acumulada por cohorte (semestre 10):** **22,61%**.
- **Deserción por estrato (Informe LEE 74, PUJ, 2021-2):** E1 13,3%, E2 13,5%,
  E3 12,5%, E4 9,6%, E5 8,3%, E6 7,1%.

| Dimensión | Variables de entrada | Marco teórico |
|---|---|---|
| Académica | promedio, materias perdidas, asistencia, semestre | Tinto (1975) |
| Financiera | saldo pendiente, ingreso del hogar (SMMLV), estrato, apoyo financiero | Bean y Metzner (1985); variables socioeconómicas SPADIES 3.0 / DANE |
| Laboral | horas de trabajo/semana, si trabaja en su área | Bean y Metzner (1985); Chaparro & Briceño (2025) |
| Personal | desplazamiento, personas a cargo, apoyo familiar, primera generación | Tinto (1975) + Bean y Metzner (1985) |

---

## 6. Validación realizada

Las cuatro comprobaciones se calculan en `modelo/sensibilidad.py`, se
muestran en la pestaña "Validación del modelo" de la página y se guardan en
la base de datos con cada simulación. **Los números de abajo son los
obtenidos realmente** al ejecutar `n = 500`, `semilla = 42`,
`tasa_base = 0.09`, `K = 1000`.

### 6.1 Calibración

| Medida | Valor |
|---|---|
| Tasa base objetivo | 0.09000 |
| Probabilidad media obtenida | 0.09000 |
| Diferencia | 1 × 10⁻⁸ |
| Margen aceptado | ± 0.005 |
| b₀ calibrado | **−4.947534** |
| **Veredicto** | **PASA** |

La bisección deja la media en la tasa base con una diferencia seis órdenes de
magnitud por debajo del margen exigido.

### 6.2 Sensibilidad (cada coeficiente ±50%)

| Dimensión | b base | Índice con −50% | Índice base | Índice con +50% | Amplitud |
|---|---|---|---|---|---|
| **Financiera** | 2.5 | 5.05% | 9.00% | 15.19% | **10.13 pp** |
| Laboral | 1.5 | 6.84% | 9.00% | 11.84% | 5.00 pp |
| Personal | 1.2 | 7.28% | 9.00% | 11.08% | 3.79 pp |
| Académica | 3.0 | 7.53% | 9.00% | 10.74% | 3.22 pp |

**Lectura, y es un resultado contraintuitivo que conviene tener listo para la
sustentación:** el supuesto más influyente **no** es el coeficiente más
grande. bA = 3.0 es el mayor de los cuatro, pero la dimensión académica es la
que menos mueve el índice general (3.22 pp), mientras que la financiera lo
mueve el triple (10.13 pp).

La razón es que **la influencia de un coeficiente depende del tamaño típico de
su subpuntaje en la cohorte**, no solo de su valor:

| Dimensión | b | s̄ (media en la cohorte) | Contribución media b·s̄ |
|---|---|---|---|
| Académica | 3.0 | 0.114 | 0.341 |
| **Financiera** | 2.5 | **0.430** | **1.076** |
| Laboral | 1.5 | 0.276 | 0.414 |
| Personal | 1.2 | 0.372 | 0.446 |

Equivocarse en bA importa poco porque sA es casi siempre pequeño; equivocarse
en bF importa mucho porque sF es grande en buena parte de la cohorte. **La
prioridad al conseguir datos reales es, entonces, estimar bien bF.**

### 6.3 Validez de cara (3 perfiles de referencia)

| Perfil | sA / sF / sL / sP | p | Esperado | Obtenido | ¿Coincide? |
|---|---|---|---|---|---|
| `sin_riesgo` | 0.02 / 0.04 / 0.00 / 0.03 | 0.0086 | bajo, sin intervención | bajo, sin intervención | **sí** |
| `riesgo_solo_financiero` | 0.26 / 0.96 / 0.30 / 0.27 | 0.2699 | medio, intervención financiera | medio, intervención financiera, único problema `financiera` | **sí** |
| `todo_alto` | 0.86 / 0.98 / 1.00 / 1.00 | 0.9405 | alto, con intervención | alto, los 4 problemas, prioridad `tutoria_academica` | **sí** |

Nota sobre el segundo perfil: está construido con la dimensión financiera en
su extremo (sF = 0.96) y las otras tres en valores **típicos de la cohorte**,
no en cero. Con las otras tres en cero, un problema financiero máximo da
p ≈ 0.08 (nivel bajo): 2.5 · 1.0 = 2.5 no alcanza a compensar b₀ = −4.95.
Es decir, **el modelo exige riesgo en más de una dimensión para marcar a un
estudiante como medio o alto**, lo cual es coherente con los dos marcos
teóricos, pero hay que saberlo y poder defenderlo.

### 6.4 Monotonía

**13 de 13 variables monótonas. PASA.** Para cada variable se recorre una
secuencia de valores de mejor a peor (por ejemplo promedio 5.0 → 4.0 → 3.0 →
2.0 → 1.0 → 0.0) verificando que p nunca baje, y se comprueba además que cada
paso intermedio siga siendo un registro válido según el Paso 1.

Las 13 variables: `promedio`, `materias_perdidas`, `asistencia_pct`,
`saldo_pendiente_cop`, `ingreso_hogar_smmlv`, `estrato`,
`tiene_apoyo_financiero`, `horas_trabajo_semana`,
`trabaja_en_area_de_estudio`, `tiempo_desplazamiento_min`,
`personas_a_cargo`, `apoyo_familiar`, `primera_generacion_universitaria`.

### 6.5 Resultado de la cohorte de referencia

| Medida | Valor |
|---|---|
| Estudiantes generados | 500 |
| Válidos (pasan el Paso 1) | 485 |
| En revisión humana | 15 (3%: 5 campo faltante, 5 fuera de rango, 5 contradicción) |
| Índice de riesgo general | 9.00% |
| Riesgo bajo | 83.92% (407) |
| Riesgo medio | 13.61% (66) |
| Riesgo alto | 2.47% (12) |
| Requieren intervención | 15.26% (74) |

### 6.6 Dos hallazgos de la validación que NO son errores de implementación

**(a) Ningún estudiante de la cohorte tiene problema académico.** Con
`n = 500, semilla = 42` hay 101 problemas financieros, 86 laborales, 44
personales y **0 académicos**, de modo que en la demo **no se emite ninguna
tutoría académica** (se emiten 51 planes financieros, 50 de flexibilidad
laboral y 18 de bienestar).

La causa es estructural, no un error: cruzar `sA ≥ 0.60` exige fallar
*simultáneamente* en promedio, materias perdidas y asistencia, porque los tres
componentes pesan 0.40 / 0.30 / 0.30. Con una cohorte plausible —en la que la
asistencia ronda el 85% y el promedio está correlacionado con ella— esa
coincidencia casi no ocurre: el sA máximo observado es 0.556. Se comprobó que
ampliar la dispersión del promedio (σ de 0.45 a 0.75) y de la asistencia (σ de
6 a 14) **no** resuelve el asunto: sigue habiendo 0–3 casos.

La fórmula sí alcanza 1.0 (está probado con un registro extremo), y la regla
de intervención académica funciona (probada en `test_intervencion.py`). Lo que
no ocurre es que el generador produzca ese perfil por azar. **Decisión
tomada:** no se retocaron las distribuciones para forzar que aparecieran
tutorías, porque ajustar los supuestos de entrada hasta obtener la salida
deseada es precisamente lo que no se puede defender ante el profesor. Queda
reportado como limitación (sección 7).

**(b) El umbral de problema y el umbral de nivel son independientes.** Un
estudiante puede ser de nivel `alto` sin tener ninguna dimensión por encima de
0.60 (riesgo repartido). Para que no quede "requiere intervención" con plan
vacío, en ese caso se le asigna la intervención de su **factor principal**.
Está documentado en el contrato y probado
(`test_intervencion.py::test_nivel_alto_sin_problemas_atiende_el_factor_principal`).

### 6.6.1 Hueco cerrado del contrato anterior y hueco nuevo encontrado

- **Caso A03** (estrato ≤ 2 con ingreso > 10 SMMLV): quedaba abierto en la
  entrega anterior y **ya está cerrado** en el Paso 1. Probado en
  `test_validacion.py::test_contradiccion_estrato_bajo_ingreso_alto_caso_a03`
  y reproducido a propósito en la cohorte por el generador.
- **Caso E15, encontrado en esta ronda:** `NaN` es un `float` y **todas** sus
  comparaciones devuelven `False`, así que `NaN < 0` y `NaN > 5` son falsas y
  el valor **burlaba la validación de rango**, llegando hasta el cálculo de la
  probabilidad y envenenándola. Se cerró exigiendo que los campos decimales
  sean números finitos (`math.isfinite`). `±inf` también se rechaza.
- **Bug del generador encontrado por las pruebas:** la rotación del tipo de
  error y la de la subvariante usaban el mismo módulo 3, lo que las dejaba
  correlacionadas: la contradicción A03 **nunca** se generaba. Corregido
  contando la vuelta por tipo de error.

### 6.7 Validación empírica sobre el dataset real UCI (Realinho et al., 4.424 estudiantes)

En `modelo/datos_reales.py` se integró el dataset público real **UCI Predict
Students' Dropout and Academic Success** (`data/predict+students+dropout+and+academic+success/data.csv`,
4.424 registros de educación superior con desenlace real `Target`), mapeando sus
atributos a los 14 campos del contrato (`E`) y evaluando los **3.630 estudiantes
con desenlace cerrado** (`1.421 Dropout` vs. `2.209 Graduate`, tasa acumulada
observada = **39,15%**):

| Métrica empírica sobre el dataset real UCI ($N = 3.630$) | Valor obtenido |
|---|---|
| Registros válidos en el Paso 1 | **3.630 de 3.630** (100%) |
| `b₀` calibrado a la tasa observada (0,3915) | **−3,5722** |
| **AUC–ROC (estadístico $U$ de Mann-Whitney)** | **0,8936** |
| Probabilidad media asignada a desertores reales (`Dropout`) | **55,15%** |
| Probabilidad media asignada a graduados reales (`Graduate`) | **28,85%** |
| Estudiantes reales con problema académico (`sA ≥ 0,60` → **`tutoria_academica`**) | **473 estudiantes** |

**Dos conclusiones clave de la prueba con datos reales:**
1. Sin reentrenar los coeficientes expertos (`3.0, 2.5, 1.5, 1.2`), el modelo
   separa a los desertores reales de los graduados reales con un **AUC–ROC de
   0,8936**.
2. Mientras que en la cohorte sintética ningún estudiante cruzaba `sA ≥ 0,60`, en
   el dataset real **473 estudiantes activan `tutoria_academica`**, confirmando
   empíricamente que la regla del Paso 3 funciona sin necesidad de forzar las
   distribuciones sintéticas.

---

## 7. Limitaciones y cómo pasar a datos reales

### Limitaciones, sin adornos

1. **Los coeficientes son supuestos, no estimaciones.** `p = 0.27` significa
   "0.27 bajo estos supuestos", no "27% de probabilidad medida". Por eso la
   página muestra siempre el intervalo P5–P95 al lado de p.
2. **La cohorte es sintética.** Toda conclusión sobre *la población* (el
   83.9% de riesgo bajo, el 15.3% que requiere intervención) describe la
   cohorte simulada, **no** a los estudiantes de la universidad. Lo que sí es
   transferible es el *mecanismo*: las fórmulas, la calibración y las reglas.
3. **El semestre no entra en el modelo de riesgo.** `semestre` es parte de la
   entrada E y se usa para describir al estudiante y para generar la cohorte,
   pero **no aparece en ninguna de las cuatro fórmulas de subpuntaje**. En la
   literatura el riesgo de deserción se concentra en los primeros semestres,
   así que esto es una omisión real del modelo especificado. Se deja
   documentada en lugar de corregirla por cuenta propia.
4. **La dimensión académica casi no se activa** con la cohorte generada
   (sección 6.6a).
5. **El intervalo P5–P95 subestima la incertidumbre total**: solo propaga la
   de los coeficientes, no la de la forma funcional ni la de la falta de datos
   (sección 4).
6. **Las cuatro dimensiones se tratan como aditivas e independientes.** No hay
   interacciones: el modelo supone que trabajar 40 horas pesa lo mismo tenga o
   no el estudiante un buen promedio. Con datos reales se podrían probar
   términos de interacción.
7. **El modelo no está validado contra resultados reales.** Calibración,
   sensibilidad, validez de cara y monotonía comprueban que el modelo es
   *coherente*, no que sea *correcto*. La precisión predictiva (AUC,
   sensibilidad/especificidad) **no se puede medir sin datos etiquetados**.
8. **Un perfil exclusivamente financiero no alcanza el nivel medio** si las
   otras tres dimensiones valen cero (p ≈ 0.08, sección 6.3): el modelo exige
   riesgo en más de una dimensión. Es una consecuencia de los coeficientes
   supuestos y de b₀, no un error; se deja documentada sin modificarla.
9. **La cohorte de referencia no genera tutorías académicas** (sección 6.6a),
   y no se alteraron las distribuciones para forzarlas.

### Cómo pasar a datos reales

1. **Conseguir el histórico anonimizado** de la universidad: por cada
   estudiante-semestre, las variables de las cuatro dimensiones y la etiqueta
   `desertó en el semestre siguiente` (sí/no). Sin identificadores
   personales, con el visto bueno del comité de ética y de la oficina de
   protección de datos.
2. **Estimar los coeficientes por máxima verosimilitud** en lugar de
   suponerlos: ajustar `b₀, bA, bF, bL, bP` sobre los subpuntajes. Las cuatro
   fórmulas de subpuntaje pueden conservarse (son la capa interpretable) o
   reemplazarse por las variables crudas para dejar que el ajuste reparta los
   pesos.
3. **Sustituir la calibración por bisección** por la tasa base observada en el
   propio histórico — b₀ saldría del ajuste y la bisección deja de ser
   necesaria.
4. **Cambiar el intervalo de Montecarlo por los errores estándar** de la
   estimación: con datos reales la incertidumbre de los coeficientes se
   *calcula*, no se supone al 25%.
5. **Validar de verdad**: partición temporal (entrenar con cohortes
   anteriores, probar con la más reciente), AUC, curva de calibración y matriz
   de confusión al umbral operativo. Recién ahí se puede hablar de precisión.
6. **Revisar el sesgo antes de usarlo para asignar recursos.** Un modelo
   alimentado con estrato e ingreso puede acabar marcando a los estudiantes
   pobres como "riesgo alto" y convertir eso en una etiqueta. Hay que medir
   el error por subgrupo y decidir explícitamente que el resultado se use para
   **ofrecer apoyo**, nunca para restringir cupos, admisiones o beneficios.

Lo que **no** cambia al pasar a datos reales: la cadena de 3 pasos, el
contrato del Paso 1, la base de datos, la API y la página. El modelo se
reentrena por dentro.

---

## 8. Lista de [OK], [SUPUESTO] y [VERIFICAR]

El detalle completo de verificación contra fuentes primarias se encuentra en
[`Calibracion Y FUentes/calibracion_desercion_colombia_corregido.md`](../../Calibracion%20Y%20FUentes/calibracion_desercion_colombia_corregido.md)
y [`Calibracion Y FUentes/fuentes_de_datasets_deserci_n_universitaria.md`](../../Calibracion%20Y%20FUentes/fuentes_de_datasets_deserci_n_universitaria.md).

| # | Marca | Estado y fuente primaria | Dónde |
|---|---|---|---|
| 1 | **[OK] / [SUPUESTO]** | En **SPADIES 3.0 (MEN, 2024)** la TDA universitaria oficial es **8,65%** ($p_{\text{sem}} \approx \mathbf{0,0442}$ bajo riesgo constante) y en 1.er semestre ronda ~9,7% (LEE 74). `TASA_BASE_SEMESTRAL = 0.09` se conserva como valor por defecto `[SUPUESTO]` de alerta temprana y `0.0442` está integrado como preset oficial SPADIES en la UI | `config.py`, §3.2 |
| 2 | **[SUPUESTO]** | Coeficientes `bA = 3.0, bF = 2.5, bL = 1.5, bP = 1.2`: juicio experto. En datos reales UCI alcanzan `AUC-ROC = 0.8936` | `config.py`, §3.2, §6.7 |
| 3 | **[SUPUESTO]** | Pesos internos de las 4 fórmulas de subpuntaje (`0.40/0.30/0.30`, etc.) | `config.py`, §3.1 |
| 4 | **[SUPUESTO]** | Valores de saturación: 3 materias perdidas, 8 M COP de saldo, 4 SMMLV, 40 h/semana, 120 min, 3 personas a cargo | `config.py`, §3.1 |
| 5 | **[SUPUESTO]** | Umbrales de nivel (`0.15 / 0.35`) y de problema (`0.60`) | `config.py`, §4 |
| 6 | **[SUPUESTO]** | Desviación del 25% de los coeficientes para el Montecarlo de incertidumbre | `config.py`, §4 |
| 7 | **[OK] / [VERIFICAR]** | Contraste con fuentes nacionales: estratos en Saber Pro 2019 (`16/35/33/10/4/2%`, LEE 15 `[OK]`), umbrales de ingreso por clase social (vulnerable $\le 2,14$ SMMLV, media hasta $11,5$ SMMLV, DANE 2024 `[OK]`), ocupación estudiantil (25,3% general DANE 2025; 70–81% en último año Saber Pro, Chaparro & Briceño 2025 `[OK]`), Gratuidad en IES públicas (939.282 beneficiarios, 97% pregrado público, MEN 2025 `[OK]`). El cruce exacto ingreso×estrato y primera generación nacional quedan `[VERIFICAR]` contra microdatos de la universidad | `config.py` §6 |
| 8 | **[OK]** | Referencia verificada de **Tinto (1975)**: *Review of Educational Research*, *45*(1), 89–125 (`10.3102/00346543045001089`) | §5 |
| 9 | **[OK]** | Referencia verificada de **Bean y Metzner (1985)**: *Review of Educational Research*, *55*(4), 485–540 (`10.3102/00346543055004485`) | §5 |
| 10 | **[OK]** | Sistema oficial del MEN verificado: **SPADIES 3.0** (integrado al SNIES), TDA universitaria 2024 = 8,65%, TAI = 12,08%, cohorte sem. 10 = 22,61% | §5 |
| 11 | **[OK]** | Estudios con regresión logística verificados: **Tapasco-Alzate et al. (2019)**, **Arismendy Fuentes et al. (2020)**, **Jordana Schmidt et al. (2023)** y tabla de estimación Mendeley Cúcuta (`9rw37dmx6s`) | §3 |
