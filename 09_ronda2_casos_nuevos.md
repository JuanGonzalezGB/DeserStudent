# 9. Ronda 2 con casos nuevos (A01 a A15)

Los 15 casos los propuso la gema de Gemini con el prompt P2. Antes de ejecutarlos revisamos sus respuestas esperadas contra `01_contrato.md`, porque el oráculo lo fijamos nosotros y no el modelo (la diapositiva pide expresamente que el modelo **no** incluya la respuesta esperada; la gema la incluyó igual).

**Resultado con el motor v2: 14/15 pasan.** Se reproduce con `python3 ronda2_nuevos_casos.py`. Los datos están en `07_dataset_ronda2.json`, el oráculo en `08_oraculo_ronda2.json` y la traza por paso en `resultados_ronda2_nuevos_v2.csv`.

## Respuestas esperadas que corregimos

| Caso | Gemini esperaba | Correcto según el contrato | Por qué |
|---|---|---|---|
| A02 | plan con cuotas=4 | plan(cuotas=0, beca=F, bono=F, tutoria=orientacion) | Solo pidió tutoría. Las cuotas solo se dan si pide apoyo financiero. |
| A03 | abstener(datos_contradictorios) | El contrato actual da plan(cuotas=4, beca=T) | El contrato solo marca como contradictorio "estrato ≥ 5 con ingreso < 1 SMMLV". Mantuvimos la expectativa de Gemini porque es el comportamiento deseado, y por eso el caso **falla**: es un hueco del contrato, no del código. |

Las otras 13 respuestas esperadas coinciden con el contrato.

## El fallo encontrado: A03

Un estudiante de estrato 1 con ingreso de 18 SMMLV recibe beca de alimentación, porque la regla de riesgo alto es "ingreso ≤ 2 **o** estrato ≤ 2". Corrección propuesta para la ronda 3:
1. En el contrato (paso 1): agregar "estrato ≤ 2 con ingreso > 10 SMMLV" como dato contradictorio y abstenerse.
2. En el código: una línea más en `paso1_v2`, simétrica a la de S06.

## Observaciones de la auditoría que no son exactas

- **"S06, S08 y S12 violaron el cortocircuito y llegaron al paso 3".** Sí llegaron al paso 3, pero no porque el pipeline ignorara el corte. El paso 1 de v1 los dejaba pasar como `valido` porque le faltaban esas validaciones. Cuando el paso 1 devuelve `abstener` o `error`, el pipeline sí corta (se ve en la traza de los CSV, por ejemplo S01 o S05).
- **"La primera versión del oráculo violaba el contrato en S15 y S13".** El oráculo siempre estuvo bien en esos casos. El que fallaba era el motor v1, y por eso esos casos salieron como FALLA.

## Huecos de cobertura que siguen abiertos

La auditoría acierta en que faltan algunos casos. Los que todavía no cubre ningún caso:
- Combinaciones de varios fallos a la vez (por ejemplo posgrado + campo faltante + fuera de rango). Además, **el contrato no dice cuál motivo debe ganar**, así que primero hay que definir esa prioridad.
- Booleano en un campo numérico (`semestre: true`) y texto raro en `id_estudiante`.
- Bordes de `materias_perdidas` = 1 vs. 2 y de `estrato` = 2 vs. 3.
