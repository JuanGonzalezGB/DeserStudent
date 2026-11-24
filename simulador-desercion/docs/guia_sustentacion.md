# Guía de sustentación — 5 puntos

Guion corto para explicarle al profesor el modelo y la demo. La idea es
**abrir con la respuesta a su pregunta**, no esperar a que la haga.

---

## 1. El problema y por qué se simula (1 min)

> "El portal tiene que decidir a quién acompañar y con qué. Para eso necesita
> una probabilidad de deserción por estudiante y, sobre todo, **saber por qué**
> es alta: una tutoría no resuelve una deuda de matrícula.
>
> Lo simulamos por dos razones: no hay histórico real disponible con el que
> entrenar nada, y los datos que el modelo necesita —promedio, deuda, ingreso
> del hogar, personas a cargo— son datos personales sensibles. Con una cohorte
> sintética construimos y validamos todo el sistema sin tocar un dato de una
> persona real."

**Mostrar:** la página completa, de un vistazo.

---

## 2. Montecarlo no es el modelo: la logística sí (2 min) — **el punto clave**

Esto es lo que se rechazó dos veces. Hay que decirlo de frente y primero.

> "La vez pasada dijimos 'Montecarlo' y eso estaba mal planteado.
> **Montecarlo no es un modelo de deserción: es un método de muestreo.**
> No contiene ninguna teoría sobre por qué alguien abandona la carrera, así
> que por sí solo no puede explicar un caso ni decidir una intervención. Si le
> metemos que el 9% deserta, nos devuelve el 9%: no aporta nada.
>
> **El modelo que explica el riesgo es una regresión logística.** Montecarlo
> se usa en dos lugares concretos, y en los dos el problema sí es de muestreo:
>
> 1. **Generar la cohorte sintética** — produce las entradas, no los riesgos.
> 2. **Propagar la incertidumbre de los coeficientes** — K = 1000 repeticiones
>    con `bᵈ ~ Normal(bᵈ, 0.25·bᵈ)` para reportar el intervalo P5–P95.
>
> Están en módulos separados, `generador.py` e `incertidumbre.py`, justamente
> para que se vea que no son el modelo."

**La frase para cerrar el punto:**

> "Montecarlo responde *qué pasa si los supuestos se mueven*.
> La logística responde *por qué este estudiante está en riesgo*.
> Son preguntas distintas."

**Por qué la logística y no otra cosa** (la tabla comparativa está en
`justificacion_modelo.md` §2): es interpretable —cada coeficiente dice cuánto
pesa cada dimensión—, da una probabilidad entre 0 y 1, es el enfoque más común
en la literatura de deserción, y **se puede reentrenar con datos reales cuando
existan sin cambiar nada más del sistema**.

**Si pregunta por los otros candidatos:** reglas deterministas no dan
probabilidad; supervivencia/Markov pide historias longitudinales que no
tenemos; machine learning necesita miles de casos etiquetados para entrenar.

**Mostrar:** el `p = 1/(1+exp(...))` con el b₀ real en la pestaña
"Validación del modelo", y un estudiante cualquiera con su intervalo P5–P95.

---

## 3. Cómo se calcula el riesgo, y que b₀ no se inventó (2 min)

> "Son dos niveles. Primero, cuatro **subpuntajes transparentes**, uno por
> dimensión, todos entre 0 y 1. Por ejemplo el académico:
>
> `sA = 0.40·(1 − promedio/5) + 0.30·min(perdidas/3, 1) + 0.30·(1 − asistencia/100)`
>
> Se recalcula a mano en diez segundos. Los pesos de cada dimensión suman 1.0,
> y eso es lo que **garantiza** que el subpuntaje no se salga de [0,1].
>
> Segundo, la logística los combina. Los coeficientes son supuestos expertos
> —3.0, 2.5, 1.5, 1.2— y están marcados como `[SUPUESTO]`.
>
> **Pero b₀ no lo inventamos.** b₀ se **calibra por bisección** para que la
> probabilidad media de la cohorte sea exactamente igual a la tasa base de
> deserción semestral. Con n = 500 y semilla 42, b₀ sale **−4.9475** y la media
> queda en **0.09000** contra un objetivo de 0.09: una diferencia de 10⁻⁸
> frente a un margen exigido de 0.005.
>
> Eso es lo que ancla el modelo: los coeficientes reparten el riesgo entre
> estudiantes, y b₀ fija el nivel global para que coincida con la realidad."

**Decir explícitamente:** la tasa base 0.09 está marcada `[SUPUESTO]` (alerta temprana de primer año, coherente con el ~9,7% de 1.er semestre en LEE 74); en **SPADIES 3.0 (MEN, corte 2024)** la TDA universitaria oficial verificada `[OK]` es **8,65%**, que equivale a **4,42% semestral** (`0.0442`, disponible con un clic en el botón de calibración oficial de la página).

**Mostrar:** la tarjeta de calibración y la gráfica de contribución por
dimensión.

---

## 4. La validación: cuatro pruebas, y un resultado contraintuitivo (3 min)

Esta es la sección que responde "¿y por qué debo creerte?".

| Prueba | Resultado real |
|---|---|
| **Calibración** | media 0.09000 vs. objetivo 0.09, diferencia 10⁻⁸ (margen ±0.005) — **pasa** |
| **Sensibilidad** | cada coeficiente ±50%; la financiera mueve el índice 10.13 pp, la académica solo 3.22 pp |
| **Validez de cara** | 3 perfiles de referencia, 3 de 3 coinciden con lo esperado |
| **Monotonía** | 13 de 13 variables: empeorar una variable nunca baja p — **pasa** |

**El resultado que conviene contar, porque demuestra que la validación sirve
para algo:**

> "El supuesto más influyente **no** es el coeficiente más grande. bA = 3.0 es
> el mayor de los cuatro, pero la dimensión académica es la que **menos** mueve
> el índice: 3.22 puntos porcentuales. La financiera, con b = 2.5, lo mueve el
> triple: 10.13 pp.
>
> La razón es que la influencia depende del **tamaño típico del subpuntaje en
> la cohorte**, no solo del coeficiente: s̄F = 0.43 contra s̄A = 0.11.
> Equivocarse en bA importa poco porque sA casi siempre es chico.
> **La conclusión práctica: si conseguimos datos reales, lo primero que hay
> que estimar bien es bF.**"

**Dos cosas que hay que decir sin que las pregunten** (es lo que diferencia
una validación real de una decorativa):

- *"En esta cohorte **ningún** estudiante cruza el umbral de problema
  académico, así que la demo no emite ninguna tutoría. No es un bug: cruzar
  0.60 exige fallar a la vez en promedio, perdidas y asistencia, y eso casi no
  ocurre en una cohorte plausible. Probamos ampliar la dispersión del promedio
  y de la asistencia y siguen saliendo 0 a 3 casos. **Decidimos no retocar las
  distribuciones para forzar que aparecieran tutorías**, porque ajustar los
  supuestos de entrada hasta obtener la salida que uno quiere es justo lo que
  no se puede defender. Queda reportado como limitación."*

- *"El intervalo P5–P95 mide solo la incertidumbre **de los coeficientes**.
  No mide el error por no tener datos reales ni por haber elegido esta forma
  funcional. Un intervalo estrecho no significa que el modelo sea correcto."*

**Mostrar:** la pestaña "Validación del modelo" completa.

---

## 5. La demo y la ingeniería (2 min)

> "La arquitectura es la misma cadena de 3 pasos de la entrega anterior:
> **validar → calcular riesgo → intervenir**, un módulo por paso.
>
> El **Paso 1** es el mismo contrato: nunca lanza excepción, nunca inventa un
> dato que falta, y un registro inválido **no recibe probabilidad** —va a
> revisión humana con su motivo. El generador mete un 3% de registros
> dañados a propósito para demostrarlo: de 500 estudiantes, 15 quedan en
> revisión, 5 por cada tipo de error.
>
> **El caso A03 quedó cerrado.** Era el hueco que encontramos la vez pasada:
> estrato ≤ 2 con ingreso > 10 SMMLV recibía plan de apoyo financiero porque
> nadie verificaba la combinación. Ahora va a revisión, está probado, y el
> generador lo reproduce a propósito en la cohorte.
>
> **Y encontramos un hueco nuevo en esta ronda:** `NaN`. Es un `float`, y
> todas sus comparaciones devuelven `False`, así que `NaN < 0` y `NaN > 5` son
> falsas y **burlaba la validación de rango** hasta llegar al cálculo de la
> probabilidad. Lo cerró el caso E15 de la prueba de estrés.
>
> Son **340 pruebas** con pytest, sin `skip` ni `xfail`. Los datos persisten
> en SQLite con consultas parametrizadas, así que el historial sobrevive al
> reinicio del servidor. Y la página es HTML, CSS y JavaScript propio: las
> gráficas son SVG dibujado a mano, funciona sin internet."

**Demo en vivo, en este orden:**
1. Pulsar **Simular** con n = 500, semilla 42 → índice general 9.00%.
2. Filtrar por **"Requiere intervención"** → 74 estudiantes (15.26%).
3. Clic en el estudiante de mayor p → panel de detalle: las 4 dimensiones, el
   intervalo P5–P95, los problemas y el plan priorizado.
4. Filtrar **"Solo revisión humana"** → los 15 registros dañados; clic en uno
   para mostrar que **no tiene probabilidad**, solo su motivo.
5. Pestaña **Historial** → reiniciar el servidor y mostrar que sigue ahí.

---

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Por qué no Montecarlo solo? | Porque no es un modelo: no explica por qué alguien deserta, así que no sirve para decidir la intervención. Se usa donde el problema sí es de muestreo. |
| ¿De dónde salen los coeficientes? | Juicio experto, marcados `[SUPUESTO]`. Por eso se reporta el intervalo P5–P95 y por eso hay prueba de sensibilidad. |
| ¿Y b₀? | Ese no es un supuesto: se calibra por bisección contra la tasa base. Diferencia 10⁻⁸. |
| ¿La tasa base de dónde viene? | En **SPADIES 3.0 (MEN, 2024)** la TDA universitaria oficial es **8,65%** (`4,42%` semestral). El valor por defecto `0.09` es un `[SUPUESTO]` de alerta temprana (1.er semestre ~9,7% en LEE 74), y ambos están como botones directos en la interfaz. |
| ¿Qué precisión tiene? | En la cohorte sintética se valida coherencia; **al evaluar el dataset real UCI ($N=3.630$ con desenlace cerrado)** alcanza **AUC–ROC = 0,8936** y activa **473 tutorías académicas**. |
| ¿Por qué 4 dimensiones? | Tinto (1975, *Rev. Educ. Res.*, 45(1), 89–125) aporta la académica y parte de la personal; Bean y Metzner (1985, *Rev. Educ. Res.*, 55(4), 485–540) la financiera, la laboral y el resto de la personal. Referencias verificadas `[OK]`. |
| ¿Cómo se pasa a datos reales? | Histórico anonimizado → estimar los coeficientes por máxima verosimilitud → errores estándar en vez del 25% supuesto → validar con partición temporal y AUC. La cadena de 3 pasos, la base y la página no cambian. |
| ¿Por qué nadie recibe tutoría? | Es el hallazgo del punto 4: estructural, no un bug. Y explicar por qué no se retocaron las distribuciones. |
| ¿El semestre no se usa? | Correcto, y es una limitación real: está en la entrada E y en el generador, pero no entra en ninguna fórmula de subpuntaje, aunque la literatura concentra el riesgo en los primeros semestres. Está documentado. |
| ¿No es discriminatorio usar estrato e ingreso? | Es un riesgo real. Hay que medir el error por subgrupo antes de usarlo, y el resultado se usa para **ofrecer apoyo**, nunca para restringir cupos o beneficios. |
