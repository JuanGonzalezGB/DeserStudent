# Prompt reutilizable: práctica de pruebas de estrés sobre cualquier sistema

Copia todo lo que está dentro del bloque, pégalo en el chat de la IA y adjunta (o pega donde dice `[ADJUNTO]`) el tema, sistema, prototipo o documento que quieres probar.

```text
# ROL
Actúa como ingeniero(a) de pruebas de software y de sistemas con IA. Tu trabajo es
someter a pruebas de estrés el sistema que describo en el adjunto, siguiendo
exactamente la metodología de clase que explico abajo. Escribe todo en español.

# INSUMO
El sistema a evaluar está en el archivo/texto adjunto: [ADJUNTO]
Si el adjunto no es un sistema sino un tema (por ejemplo "inscripción a cursos" o
"app de domicilios"), primero define en 3 a 5 líneas el sistema concreto que tomaría
decisiones sobre ese tema (qué recibe, qué decide, qué devuelve) y trabaja sobre él.
Si falta información para alguna regla, NO preguntes ni te detengas: elige el
supuesto más razonable, márcalo como [SUPUESTO] y sigue.

# METODOLOGÍA (no te saltes pasos ni cambies el orden)

## Paso 1. Contrato por pasos
Modela el sistema como una cadena de pasos encadenados: E → Paso 1 → Paso 2 → Paso 3
(usa 3 pasos salvo que el sistema pida claramente otro número). Para CADA paso escribe
su contrato de entrada (E) y salida (S):
- Entrada E: tabla con campo | tipo | rango o valores permitidos | obligatorio.
- Paso 1 casi siempre es "validar la entrada". Su S1 es "válido" o una salida
  terminal:
  - error(tipo_invalido | fuera_de_rango | valor_no_permitido): dato mal formado.
    Error controlado, nunca una excepción.
  - abstener(campo_faltante | datos_contradictorios | fuera_de_poblacion): el
    sistema no decide y remite el caso a un humano.
- Pasos 2 y 3: reglas explícitas en tablas (condición → resultado), con umbrales
  numéricos y diciendo si son inclusivos (≤, ≥).
- Cierra con "Garantías del contrato": nunca lanza excepción; nunca inventa datos
  que faltan (no asume 0 ni vacío); nunca da resultados a quien está fuera de la
  población; los umbrales son inclusivos tal como están escritos.

## Paso 2. Data real (5 casos típicos)
Escribe 5 entradas típicas, las que el sistema verá a diario (IDs R01–R05). Si el
adjunto trae datos reales, úsalos anonimizados; si no, invéntalos y marca la tabla
con [DATOS TÍPICOS INVENTADOS: reemplazar por reales].

## Paso 3. Data simulada (15 casos adversariales)
Genera 15 entradas diseñadas para ROMPER un sistema construido sobre ese contrato
(IDs S01–S15). Cubre como mínimo:
- campos faltantes,
- campos contradictorios entre sí,
- entradas de otra población (alguien a quien el sistema no debe atender),
- valores fuera de rango o de otro tipo/escala,
- valores justo en los umbrales (casos frontera),
- entradas donde la respuesta correcta es "abstenerse".
Entrega una tabla: ID | categoría | entrada completa | por qué es difícil.
REGLA CLAVE: en esta tabla NO incluyas la respuesta esperada.

## Paso 4. Oráculo (respuesta esperada)
En una sección APARTE, titulada "Oráculo – BORRADOR para que el equipo lo revise y
firme", escribe para los 20 casos (R01–R05 y S01–S15) la salida esperada, aplicando
el contrato regla por regla. Formato: ID | decisión (resultado / abstener / error) |
detalle | regla del contrato que lo justifica.
Aclara que el oráculo lo deben validar las personas, no el modelo: si el modelo
escribe las respuestas, se mide qué tan bien se copia a sí mismo, no si el sistema
funciona.

## Paso 5. Comprobar E y S (ronda 1)
Escribe una versión 1 del sistema (en Python, sin librerías externas) que implemente
SOLO las reglas del camino feliz, como suele quedar una primera versión. Ejecuta
mentalmente (o de verdad, si puedes ejecutar código) los 20 casos y registra la traza
de cada paso (S1, S2, S3).
Entrega la tabla: ID | origen | categoría | entrada clave | esperado | obtenido | PASA/FALLA.
Al final, el conteo "Ronda 1: X/20 pasan".
Para cada FALLA: en qué paso falló, causa y corrección propuesta.

## Paso 6. Ronda 2
Aplica las correcciones (versión 2), vuelve a correr los 20 casos y entrega la misma
tabla con el conteo "Ronda 2: X/20 pasan". Si algo sigue fallando, dilo; no
maquilles resultados.

## Paso 7. Biblioteca de prompts
Guarda los prompts reutilizables de la práctica, cada uno con propósito, cuándo
usarlo y regla clave:
- P1: generar los 15 casos adversariales a partir del contrato y los 5 reales
  (sin respuesta esperada).
- P2: generar 15 casos nuevos para la ronda 2 atacando los fallos encontrados desde
  otro ángulo.
- P3: revisar el contrato antes de probar y listar ambigüedades (umbrales sin
  inclusividad, campos sin rango, casos sin regla, dudas de abstención).

## Paso 8. Diagramas (Mermaid)
- Diagrama A: el sistema por pasos, E → 1 → 2 → 3, con la S de cada paso y las
  salidas terminales (error, abstener → humano).
- Diagrama B: el proceso de la práctica (contrato → 5 reales → 15 simulados →
  oráculo → ejecutar → ¿obtenido = esperado? → corregir → ronda 2 → artefactos).

# FORMATO DE ENTREGA
Empieza con una tabla "Entregables del tablero" que mapee cada entregable a su
sección:
| Tablero | Sección |
| 1. Contrato | Paso 1 |
| 2. Simular data / 3. Data set simulado | Paso 3 |
| 3. Comprobar E y S (data típica y extrema) | Pasos 4, 5 y 6 |
| 4. Data real | Paso 2 |
| Artefacto | código v1 y v2 + datos en JSON |
| Biblioteca P. | Paso 7 |
| Diagrama | Paso 8 |
Después, cada paso con su encabezado. Entrega el dataset (los 20 casos) y el oráculo
también en JSON para poder reutilizarlos. Termina con "Cosas a revisar antes de
entregar": los [SUPUESTO] que hiciste, si los datos "reales" son inventados y el
recordatorio de que el oráculo lo firma el equipo.

# REGLAS
- Sigue el orden de los pasos; el oráculo se escribe DESPUÉS de los casos y en
  sección aparte.
- No inventes resultados de ejecución: si no ejecutaste código, di "ejecución
  simulada a mano".
- Lenguaje claro, sin relleno; tablas cuando haya más de 3 elementos.
```

## Cómo usarlo

1. Pega el bloque en Claude, ChatGPT o Gemini.
2. Adjunta el archivo del sistema (o escribe el tema) en lugar de `[ADJUNTO]`.
3. Revisa los `[SUPUESTO]` y el oráculo antes de entregar: esa parte la deben firmar ustedes.
