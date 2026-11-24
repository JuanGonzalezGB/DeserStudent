# 5. Resultados: esperado vs. obtenido

- **Ronda 1 (motor v1):** 14/20 pasan.
- **Ronda 2 (motor v2, con los fallos corregidos):** 20/20 pasan.

Todos los resultados se obtuvieron ejecutando `python3 ejecutar_pruebas.py`. La traza de cada paso (S1, S2, S3) está en los CSV.

## Ronda 1: tabla completa

| ID | Origen | Categoría | Entrada (clave) | Esperado | Obtenido | Estado |
|---|---|---|---|---|---|---|
| R01 | real | típico | Perfil más común: bajo ingreso, una materia perdida, pide ambos apoyos. | plan(cuotas=4, beca=True, bono=True, tutoria=academica) | plan(cuotas=4, beca=True, bono=True, tutoria=academica) | **PASA** |
| R02 | real | típico | Estudiante al día que solo quiere orientación. | plan(cuotas=0, beca=False, bono=False, tutoria=orientacion) | plan(cuotas=0, beca=False, bono=False, tutoria=orientacion) | **PASA** |
| R03 | real | típico | Primer semestre con bajo rendimiento: activa tutoría prioritaria. | plan(cuotas=4, beca=False, bono=False, tutoria=academica_prioritaria) | plan(cuotas=4, beca=False, bono=False, tutoria=academica_prioritaria) | **PASA** |
| R04 | real | típico | Solo pide apoyo financiero, vive lejos. | plan(cuotas=4, beca=True, bono=True, tutoria=ninguna) | plan(cuotas=4, beca=True, bono=True, tutoria=ninguna) | **PASA** |
| R05 | real | típico | Riesgo medio en ambas dimensiones. | plan(cuotas=4, beca=False, bono=True, tutoria=academica) | plan(cuotas=4, beca=False, bono=True, tutoria=academica) | **PASA** |
| S01 | simulado | incompleto | Falta el promedio: sin él no se puede clasificar el riesgo académico. | abstener(campo_faltante) | abstener(campo_faltante: promedio) | **PASA** |
| S02 | simulado | incompleto | Pide apoyo financiero pero no hay saldo: el sistema podría asumir 0 y negar el apoyo. | abstener(campo_faltante) | abstener(campo_faltante: saldo_pendiente) | **PASA** |
| S03 | simulado | fuera de rango | Promedio en escala 0-10 en lugar de 0-5 (dato de otra institución). | error(fuera_de_rango) | error(fuera_de_rango: promedio) | **PASA** |
| S04 | simulado | fuera de rango | Saldo negativo (saldo a favor) mal cargado. | error(fuera_de_rango) | error(fuera_de_rango: saldo_pendiente) | **PASA** |
| S05 | simulado | contradictorio | Perdió más materias de las que inscribió. | abstener(datos_contradictorios) | abstener(datos_contradictorios: perdidas > inscritas) | **PASA** |
| S06 | simulado | contradictorio | Estrato 6 con ingreso menor a 1 SMMLV: posible error o fraude, el sistema daría beca completa. | abstener(datos_contradictorios) | plan(cuotas=4, beca=True, bono=True, tutoria=orientacion) | **FALLA** |
| S07 | simulado | otra población | No está matriculado este semestre: los beneficios no aplican. | abstener(fuera_de_poblacion) | abstener(fuera_de_poblacion: no matriculado) | **PASA** |
| S08 | simulado | otra población | Estudiante de posgrado: el sistema se diseñó para pregrado. | abstener(fuera_de_poblacion) | plan(cuotas=4, beca=True, bono=True, tutoria=orientacion) | **FALLA** |
| S09 | simulado | extremo | Promedio exactamente en el umbral 3.0. | plan(cuotas=0, beca=False, bono=False, tutoria=academica) | plan(cuotas=0, beca=False, bono=False, tutoria=academica) | **PASA** |
| S10 | simulado | extremo | Ingreso exactamente en el umbral de 2 SMMLV. | plan(cuotas=4, beca=True, bono=False, tutoria=ninguna) | plan(cuotas=4, beca=False, bono=False, tutoria=ninguna) | **FALLA** |
| S11 | simulado | extremo | Distancia exactamente en el umbral de 5 km del bono de transporte. | plan(cuotas=4, beca=False, bono=True, tutoria=ninguna) | plan(cuotas=4, beca=False, bono=True, tutoria=ninguna) | **PASA** |
| S12 | simulado | fuera de rango | Saldo absurdo (error de digitación con ceros de más). | error(fuera_de_rango) | plan(cuotas=4, beca=True, bono=True, tutoria=orientacion) | **FALLA** |
| S13 | simulado | tipo inválido | Promedio escrito como texto desde un formulario libre. | error(tipo_invalido) | excepcion(TypeError: '<=' not supported between instances of 'float' and 'str') | **FALLA** |
| S14 | simulado | fuera de rango | Semestre mayor al máximo del programa. | error(fuera_de_rango) | error(fuera_de_rango: semestre) | **PASA** |
| S15 | simulado | abstención/extremo | Primer semestre sin notas aún: el promedio vacío es legítimo, no un campo faltante. | plan(cuotas=4, beca=True, bono=False, tutoria=orientacion) | abstener(campo_faltante: promedio) | **FALLA** |

## Ronda 1: fallos, causa y corrección

| ID | Diferencia | Paso donde falla y corrección |
|---|---|---|
| S06 | decision: esperado=abstener obtenido=plan; motivo: esperado=datos_contradictorios obtenido=None | El paso 1 no revisaba la coherencia estrato/ingreso. Corregido: abstención por datos contradictorios. |
| S08 | decision: esperado=abstener obtenido=plan; motivo: esperado=fuera_de_poblacion obtenido=None | El paso 1 no revisaba el nivel. Corregido: abstención fuera de población. |
| S10 | beca_alimentacion: esperado=True obtenido=False | El paso 2 usaba `< 2` en vez de `≤ 2` SMMLV, contra lo que dice el contrato. Corregido el operador. |
| S12 | decision: esperado=error obtenido=plan; motivo: esperado=fuera_de_rango obtenido=None | El paso 1 no tenía tope de saldo. Corregido: rango 0 a 20.000.000. |
| S13 | decision: esperado=error obtenido=excepcion; motivo: esperado=tipo_invalido obtenido=TypeError | El paso 1 no validaba tipos y el sistema lanzó una excepción. Corregido: error controlado `tipo_invalido`. |
| S15 | decision: esperado=plan obtenido=abstener; cuotas: esperado=4 obtenido=None; beca_alimentacion: esperado=True obtenido=None; bono_transporte: esperado=False obtenido=None; tutoria: esperado=orientacion obtenido=None | El paso 1 trataba el promedio vacío de primer semestre como faltante. Corregido: se acepta y el riesgo académico queda `sin_datos`. |

## Conclusiones

1. Los 5 casos reales pasaron en la ronda 1: el camino feliz funcionaba. Todos los fallos salieron de los casos adversariales, que es justo lo que busca la práctica.
2. Los 6 fallos están en los pasos 1 y 2. Cinco son validaciones que faltaban en la entrada y uno es un umbral mal implementado (`<` en vez de `≤`).
3. Los fallos más graves son S06, S08 y S12: el sistema entregaba beca y bono a quien no debía, en vez de abstenerse o rechazar.
4. S13 es el único fallo que rompe el sistema (excepción). El contrato exige error controlado.
5. Ronda 2: los 20 casos pasan. El siguiente paso es generar 15 entradas nuevas con el prompt P2 para atacar los mismos puntos débiles desde otro ángulo, porque pasar los mismos casos que ya conocíamos no prueba que el sistema esté bien.
