# Informe Técnico de Calibración (versión corregida): Simulador de Deserción Estudiantil Universitaria en Colombia

Versión verificada el 17-nov-2026 contra fuentes primarias. Convenciones:

- **[OK]**: verificado en la fuente primaria.
- **[VERIFICAR]**: dato plausible pero sin fuente confirmada; no usar como si estuviera respaldado.
- **[SUPUESTO]**: decisión de modelado propia; ninguna fuente la respalda.

---

## 1. Sistema oficial del MEN y tasa base de deserción

- **Sistema [OK].** SPADIES 3.0, subsistema integrado al SNIES. Desertor: estudiante sin matrícula durante dos o más periodos consecutivos, no graduado ni retirado por motivos disciplinarios.
- **Fuente:** [SPADIES, Estadísticas de deserción, indicadores 2024](https://www.mineducacion.gov.co/sistemasinfo/spadies/secciones/Estadisticas-de-desercion/) (publicada el 22-sep-2026; el primer semestre de cada año es el periodo de referencia).

| Indicador 2024 | Total sistema (todos los niveles) | Nivel universitario | 2023 universitario |
| :--- | :--- | :--- | :--- |
| Tasa de deserción anual (TDA) | 9,78 % (2023: 8,97 %) | **8,65 %** | 7,82 % |
| Tasa de ausencia intersemestral (TAI) | 13,92 % (2023: 12,40 %) | **12,08 %** | 11,09 % |
| Deserción por cohorte acumulada, semestre 10 | n/d | **22,61 %** | 23,15 % |

> **Corrección:** el informe original usaba 9,78 % y 13,92 % como si fueran universitarios. Son los totales del sistema.

**Conversión a tasa semestral (riesgo constante entre los dos semestres):**

p_sem = 1 − √(1 − 0,0865) ≈ **0,0442** (4,42 %)

Notas de modelado:

- La TDA se mide sobre el stock de matriculados de cualquier semestre, no sobre cohortes de ingreso. [SUPUESTO] aceptar la raíz cuadrada como aproximación.
- La cohorte acumulada (22,61 % a semestre 10) implica un riesgo medio de ~2,53 % por semestre. El riesgo real es mayor en los primeros semestres (LEE 74: ~9,7 % en el semestre 1 de la cohorte 2016-1, todos los niveles). Un riesgo constante no reproduce esa forma.
- La TAI **no** debe usarse como `TASA_BASE_SEMESTRAL`: incluye estudiantes que regresan.

---

## 2. Distribuciones de estudiantes (`config.py`)

### 2.1 Estrato socioeconómico

El Informe LEE 74 **no** contiene la distribución de estudiantes por estrato (solo deserción por estrato). Datos disponibles:

| Fuente | Población | E1 | E2 | E3 | E4 | E5 | E6 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [LEE Informe 15](https://www.javeriana.edu.co/recursosdb/5581483/7093554/INFORME-15-LEE-JAVERIANA-CARRERAS-y-ESTRATOS-SOCIOECONO%CC%81MICOS.pdf) [OK] | Examinados Saber Pro 2019 (N = 242.111, ~11 % de la matrícula, auto-reporte) | 16 % | 35 % | 33 % | 10 % | 4 % | 2 % |
| SPADIES vía [El Tiempo](https://www.eltiempo.com/vida/educacion/7-de-cada-10-jovenes-que-entran-a-la-universidad-son-de-estratos-1-y-2-592674) [VERIFICAR] | Entrantes a pregrado | ~70 % entre E1 y E2; ~90 % entre E1 y E3 | | | | | |
| [MEN](https://www.mineducacion.gov.co/1780/articles-416059_recurso_13.pdf) [OK] | Pregrado en IES públicas | >75 % entre E1 y E2; >20 % E3 | | | | | |

**Recomendación:** `ESTRATO_PESOS = [0.16, 0.35, 0.33, 0.10, 0.04, 0.02]` (suma 1,00) si el simulador modela estudiantes avanzados. Si modela entrantes, hay que consultar SPADIES directamente. El vector `[0.23, 0.35, 0.27, 0.08, 0.04, 0.03]` del informe original **no tiene fuente**.

**Nota sobre Saber Pro 2021 [OK]:** el ICFES publica el nivel socioeconómico con el INSE (NSE 1: 38 %, NSE 2: 35 %, NSE 3: 7 %, NSE 4: 16 %, sin dato 4 %; 248.534 examinados), que **no** equivale a estrato. No usarlo para `ESTRATO_PESOS`. Fuente: [Informe Nacional Superior 2021](https://www.icfes.gov.co/wp-content/uploads/2024/11/Informe_Nacional_Resultados_Superior_2021.pdf).

**Deserción por estrato [OK]** (LEE 74, 2021-2, todos los niveles): E1 13,3 %, E2 13,5 %, E3 12,5 %, E4 9,6 %, E5 8,3 %, E6 7,1 %.

### 2.2 Ingreso del hogar en SMMLV por estrato

**El DANE no publica una tabla de ingreso por estrato.** Publica umbrales por **clase de ingreso** ([Clases sociales 2024](https://www.dane.gov.co/files/operaciones/PM/cp-PMClasesSociales-2024.pdf)) [OK]:

| Clase | Ingreso per cápita mensual 2024 | Hogar de 3,1 personas (cálculo propio, SMMLV 2024 = $1.300.000) |
| :--- | :--- | :--- |
| Pobres | bajo la línea de pobreza monetaria (varía por dominio) | n/d |
| Vulnerables | hasta $897.987 | hasta ~$2,78 M ≈ **2,14 SMMLV** |
| Clase media | $897.987 – $4.835.315 | ≈ 2,14 – **11,5 SMMLV** |
| Clase alta | más de $4.835.315 | más de ≈ 11,5 SMMLV |

Los rangos del informe original por estrato (E1 0,7–1,4 … E6 >13 SMMLV) **no** salen de este boletín. Asignar una clase de ingreso a cada estrato es [SUPUESTO]; para hacerlo con datos hay que cruzar estrato e ingreso en los microdatos de la GEIH, que no pude consultar.

### 2.3 Estudiantes que trabajan

- **DANE 2025 [OK]:** de la población en edad de trabajar que asiste a una institución educativa (cualquier nivel), 25,3 % está ocupada y 3,9 % desocupada. [Boletín Fuerza laboral y educación 2025](https://www.dane.gov.co/files/operaciones/GEIH/bol-GEIHFLE-2025.pdf). **No es específico de pregrado.**
- **Saber Pro [OK]** ([Chaparro & Briceño, 2025](https://educacionyeducadores.unisabana.edu.co/index.php/eye/article/download/25059/9087/164539)): examinados que trabajan 71,03 % (2016), 69,96 % (2017), 80,7 % (2018), 81,45 % (2019). Son estudiantes próximos a graduarse, o sea sobrevivientes. Cerca del 51 % de los que trabajan lo hacen más de 30 h/semana.
- **Efecto sobre puntaje [OK]:** −0,53 DE (−11,55 puntos de 300). Es efecto sobre **puntajes**, no sobre deserción.
- **Eliminado:** el "promedio de 24–29 h/semana" y el "umbral crítico de 20 h" no aparecen en el estudio. Pasan a [SUPUESTO].

### 2.4 Apoyo financiero

- **Gratuidad [OK]:** 939.282 beneficiarios en 2025, 97 % de la matrícula de pregrado en IES públicas ([MEN, SNIES](https://www.mineducacion.gov.co/1780/w3-article-429538.html)). El número de IES es 64 en comunicados MEN de 2024 [VERIFICAR el dato 2025].
- **Fracción del pregrado nacional con gratuidad:** el 37,6 % del informe original dividía por ~2,5 M (matrícula 2024). No está en la fuente y mezcla años. [VERIFICAR]; calcular con el denominador 2025 de SNIES.
- **ICETEX [VERIFICAR]:** el comunicado citado en el original habla de 150.000 *nuevos cupos públicos*, no de créditos. Hay reportes de 442.369 beneficiarios de crédito tradicional ([Portafolio](https://www.portafolio.co/economia/finanzas/icetex-apoya-a-un-millon-de-colombianos-con-creditos-educativos-mas-accesibles-y-condonaciones-617566)), sin periodo claro. No fijar un porcentaje sin consultar ICETEX.
  - **Nuevos beneficiarios de crédito en pregrado [OK]** ([LEE Informe 76](https://www.javeriana.edu.co/recursosdb/5581483/8102914/INF.76-COBERTURA-ICETEX-F.pdf)): 2022 = 41.079 (1.726 + 19.169 en 2022-1; 1.393 + 18.791 en 2022-2); 2015–2022 = 624.038 personas. La serie cayó de 65.046 (2015-1) a ~20.000 por semestre en 2022. En 2022-2, los estratos 1 y 2 son el 78 % de los beneficiarios.
  - **Límites:** el informe reporta flujos de beneficiarios **nuevos**, no el stock de créditos vigentes ni la fracción de la matrícula cubierta, y advierte que ICETEX modificó después las cifras en datos abiertos. Para `PROP_ICETEX` sigue haciendo falta el stock vigente [VERIFICAR].
- **Becas 8–10 % y "52–54 % con apoyo":** sin fuente → [SUPUESTO].

### 2.5 Primera generación

58–65 % [VERIFICAR]. No se encontró la fuente citada (SNIES 2017 / ASCUN). Los informes nacionales del ICFES que revisé (Saber Pro 2021 y 2024-II) no publican la educación de los padres. Ese dato requiere los microdatos de Saber 11 / Saber Pro, que no pude consultar. Tampoco encontré una cifra nacional publicada de estudiantes de primera generación; ver nota en el apéndice. Usar [SUPUESTO] con un rango amplio y declararlo en el simulador.

---

## 3. Estudios empíricos con regresión logística

### Estudio 1: Universidad de Caldas
- **Cita [OK]:** Tapasco-Alzate, O. A., Ruiz-Ortega, F. J., Osorio-García, D., & Ramírez-Ramírez, D. (2019). Deserción estudiantil: incidencia de factores institucionales relacionados con los procesos de admisión. *Educación y Educadores*, 22(1), 81–100. https://doi.org/10.5294/edu.2019.22.1.5
- **Muestra:** cohortes **2010–2012**, N = 6.421 (tabla 1; el texto dice 6.451), deserción 41,7 %. *(El original decía 2010–2015, N > 8.000: incorrecto.)*
- **OR del modelo global:** segunda opción **2,99**; acción afirmativa 0,82; méritos académicos 0,60; puntaje ICFES ponderado **0,97**; matrícula (costo) 0,89; tipo de colegio 1,20; edad de ingreso **1,03**; sexo 1,42.
- **Advertencias:**
  - El artículo reporta OR; los β son derivados (ln OR).
  - Sexo 1,42 contradice los resultados bivariados y por facultad (las mujeres desertan menos). Probable inversión de codificación: no usar ese signo sin revisarlo.
  - El efecto de la edad (21–25 vs 17 años = +39 %) proviene de un informe MEN 2008 citado, no de su modelo.
  - AUC = 0,63: poder predictivo bajo.

### Estudio 2: Universidad de los Llanos
- **Cita [OK]:** Arismendy Fuentes, C. A., Morales Parrado, N. L., & Díaz Castro, J. (2020). Análisis de la deserción temprana y sus factores explicativos en la Universidad de los Llanos con datos de ingreso, 2015-2. *Investigaciones Andina*, 22(40), 99–121. https://www.redalyc.org/articulo.oa?id=239075120007
  *(El original atribuía el artículo a "González & Eslava" con pp. 99–118: incorrecto.)*
- **Muestra:** N = 574, cohorte 2015-2 hasta 2018-1; deserción temprana (4 primeros semestres).
- **Coeficientes logit [OK]:** puntaje Saber 11 −0,0755 (OR 0,927); mujer −0,451 (OR 0,637); colegio público −0,817 (OR 0,442); repitió años +0,727 (OR 2,07); estudios previos −0,422 (OR 0,656); padres separados +0,486 (OR 1,63); facultad vs. Agropecuarias: Ciencias Básicas e Ingeniería +1,392 (OR 4,02), Salud +1,233 (OR 3,43).
- **Predicción:** 67 % global; sensibilidad 54 %.

### Estudio 3: Universidad de La Frontera (Chile)
- **Cita [OK]:** Jordana Schmidt, B., Boero, P., & Méndez Vera, J. A. (2023). Factores que influyen en la deserción universitaria: El caso de una universidad estatal chilena. *Revista Portuguesa de Educação*, 36(1), e23002. https://doi.org/10.21814/rpe.23401
- **Muestra:** N = 2.222 (cohorte 2016, muestra no probabilística); 8 submodelos.
- **Modelo global [OK] (N = 2.222):** PAAU (apoyo académico) OR 0,505; preferencia de carrera OR 0,639 (p = 0,019); egreso de secundaria el año anterior OR 1,807; PGA categórico (vs. <4,0): PGA2 0,015, PGA3 0,005, PGA4 0,005.
- **Submodelo de Medicina (N = 493) [OK]:** PGA 0,094 (IC 0,032–0,276); PAAU 0,104 (IC 0,012–0,882); autorregulación 0,365 (IC 0,141–0,946). *(El original presentaba estos valores como si fueran del modelo general.)*
- **Preferencia de carrera:** OR 0,479 en el primer año y 0,402 en Ingeniería y Ciencias. El "≈ 1,95" del original es una frase del texto ("casi dos veces"), no un estimador.
- **Advertencias:** el PGA es casi mecánico (un promedio bajo lleva a eliminación reglamentaria, según los propios autores), y la escala es chilena (1–7). No transferir los OR a Colombia.

---

## 4. Referencias (APA 7) [OK]

- Bean, J. P., & Metzner, B. S. (1985). A conceptual model of nontraditional undergraduate student attrition. *Review of Educational Research*, *55*(4), 485–540. https://doi.org/10.3102/00346543055004485 *(DOI espejo JSTOR 10.2307/1170245: [VERIFICAR])*
- Tinto, V. (1975). Dropout from higher education: A theoretical synthesis of recent research. *Review of Educational Research*, *45*(1), 89–125. https://doi.org/10.3102/00346543045001089 *(espejo JSTOR 10.2307/1170024, citado por Tapasco et al. 2019)*

Ambos son modelos conceptuales: respaldan *qué factores incluir*, no pesos numéricos.

---

## 5. Tabla resumen para `config.py`

| Parámetro | Valor | Estado | Fuente |
| :--- | :--- | :--- | :--- |
| `TASA_BASE_SEMESTRAL` | **0.0442** | [OK] derivado | TDA universitaria 2024 = 8,65 % ([SPADIES](https://www.mineducacion.gov.co/sistemasinfo/spadies/secciones/Estadisticas-de-desercion/)); riesgo constante |
| `DESERCION_COHORTE_S10` (validación) | 0.2261 | [OK] | SPADIES 2024, universitario |
| `ESTRATO_PESOS` | `[0.16, 0.35, 0.33, 0.10, 0.04, 0.02]` | [OK] con salvedad | Saber Pro 2019 (LEE 15); cambia si se modelan entrantes |
| `DESERCION_POR_ESTRATO` (referencia) | 13,3 / 13,5 / 12,5 / 9,6 / 8,3 / 7,1 % | [OK] | LEE 74 (2021-2, todos los niveles) |
| `INGRESO_SMMLV_POR_ESTRATO` | umbrales por clase: vulnerable ≤ ~2,1 SMMLV; media hasta ~11,5 SMMLV (hogar de 3,1 pers.) | [OK] por clase; el mapeo a estrato es [SUPUESTO] | [DANE, Clases sociales 2024](https://www.dane.gov.co/files/operaciones/PM/cp-PMClasesSociales-2024.pdf) |
| `PROP_TRABAJA` | 0.25 (todos los niveles) o 0.71–0.81 (último año) | [OK] con salvedad de alcance | DANE 2025; Chaparro & Briceño 2025 |
| `HORAS_TRABAJO` | 24–29 h, umbral 20 h | [SUPUESTO] | sin fuente |
| `PROP_GRATUIDAD` | calcular con 939.282 / pregrado 2025 | [VERIFICAR] | MEN/SNIES |
| `PROP_ICETEX`, `PROP_BECAS` | — | [VERIFICAR] / [SUPUESTO] | solo hay flujo de nuevos beneficiarios (41.079 en 2022; LEE 76), no el stock vigente |
| `PROP_PRIMERA_GEN` | — | [SUPUESTO] | no hay cifra nacional publicada que haya podido confirmar; requiere microdatos Saber 11/Pro |
| `PESO_ACADEMICA` | `[SUPUESTO]` | [SUPUESTO] | PGA/puntaje de ingreso y preferencia de carrera son los predictores más fuertes en los tres estudios, sin cuantificar importancia relativa |
| `PESO_FINANCIERA` | `[SUPUESTO]` | [SUPUESTO] | la brecha E1 vs. E6 (13,3 % vs. 7,1 %) es real, pero no deriva un peso |
| `PESO_LABORAL` | `[SUPUESTO]` | [SUPUESTO] | Chaparro & Briceño miden puntajes, no deserción |
| `PESO_PERSONAL` | `[SUPUESTO]` | [SUPUESTO] | sexo, edad, padres (Tapasco; Arismendy) |

**Sobre los pesos:** los valores 0,42 / 0,28 / 0,18 / 0,12 del informe original no provienen de ningún estudio. Si se necesita una calibración real, usar los OR del Estudio 1 y 2 como coeficientes logit directos (β = ln OR) en vez de pesos "de importancia relativa".

---

## Apéndice: registro de correcciones respecto al original

1. TDA y TAI: eran totales, no universitarias. `p_sem` pasa de 0,0502 a 0,0442.
2. "González & Eslava (2020)" → Arismendy Fuentes, Morales Parrado & Díaz Castro; pp. 99–121; URL SciELO no verificada (la fuente verificada es Redalyc).
3. Tapasco 2019: cohortes y N corregidos.
4. Jordana 2023: OR de PGA, PAAU y autorregulación pertenecen a Medicina; OR 1,95 fabricado.
5. Chaparro & Briceño: eliminadas las horas semanales y el umbral de deserción.
6. ICETEX 150.000 / 6 %, becas 8–10 % y "52–54 %": sin respaldo.
7. 37,6 % gratuidad: derivado con denominador no declarado.
8. Estratos: la fuente LEE 74 no contiene esa distribución; se reemplaza por Saber Pro 2019.
9. Primera generación 58–65 %: sin respaldo.
10. Pesos 0,42/0,28/0,18/0,12: inventados; devueltos a [SUPUESTO].
11. DANE 25,3 %: corregido el alcance (población en edad de trabajar que estudia, cualquier nivel).
12. Rangos de ingreso por estrato: el DANE publica umbrales por clase de ingreso, no por estrato; se reemplazan por esos umbrales.
13. ICETEX: se añade la serie de nuevos beneficiarios (LEE 76); sigue sin haber stock vigente.
14. Primera generación: lo único que encontré fue que al menos el 43 % de los nuevos ingresantes a universidades públicas **argentinas** tiene padres sin título terciario (nota de Infobae). No aplica a Colombia y no debe usarse.
