# 2. Biblioteca de prompts

> Interpretación: en el tablero dice "Biblioteca P." Lo leemos como **biblioteca de prompts**, porque la diapositiva ("Tool move 1") entrega justamente un prompt reutilizable para pegar en el chat. Conviene confirmarlo con el profesor.

Cada prompt se guarda con su propósito, cuándo usarlo y la regla clave.

## P1. Generar los casos que rompen el sistema (Tool move 1)

**Propósito:** que el modelo invente las 15 entradas adversariales. El modelo no está apegado a nuestra idea, así que imagina mejor cómo falla.

**Regla clave:** el modelo **no** escribe la respuesta esperada. Nosotros escribimos el oráculo; si el modelo lo hiciera, mediríamos qué tan bien lo copiamos, no si el sistema funciona.

```text
Here is a step contract for a component I am building:
<pegar 01_contrato.md>

Here are 5 real inputs it will see:
<pegar los casos R01 a R05 de 03_dataset.json>

Generate 15 more inputs designed to break a system built on this contract.
Cover: missing fields, contradictory fields, inputs from a different
population, out-of-range values, and inputs where the correct answer is "abstain".

Return a table: input | why this one is hard.
Do NOT include the expected answer.
```

Versión en español equivalente:

```text
Este es el contrato por pasos de un componente que estoy construyendo:
<contrato>

Estas son 5 entradas reales que va a recibir:
<5 filas>

Genera 15 entradas más diseñadas para romper un sistema construido sobre este
contrato. Cubre: campos faltantes, campos contradictorios, entradas de otra
población, valores fuera de rango y entradas donde la respuesta correcta es "abstenerse".

Devuelve una tabla: entrada | por qué es difícil.
NO incluyas la respuesta esperada.
```

**Salida obtenida:** columnas `entrada` y `por_que_es_dificil` de los casos S01 a S15 en `03_dataset.json`. La columna "por qué es difícil" sirve directamente como inventario de modos de falla para el registro de riesgos de la clase 6.

## P2. Convertir los fallos en la ronda 2

**Propósito:** repetir la prueba unas dos semanas después, partiendo de los fallos reales.

```text
Este es el contrato actualizado: <contrato>
Estos casos fallaron en la ronda 1 y así los corregimos: <tabla de fallos de 05_resultados.md>

Genera 15 entradas nuevas que ataquen los mismos puntos débiles desde otro
ángulo (otros umbrales, otras combinaciones de campos, otros tipos de dato).
Devuelve una tabla: entrada | por qué es difícil. NO incluyas la respuesta esperada.
```

## P3. Revisar el contrato antes de probar

```text
Lee este contrato por pasos: <contrato>
Señala ambigüedades: umbrales sin decir si son inclusivos, campos sin rango,
casos que ninguna regla cubre y situaciones donde no está claro si abstenerse.
No propongas código, solo la lista de huecos.
```
