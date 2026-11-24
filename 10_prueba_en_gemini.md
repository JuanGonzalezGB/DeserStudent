# 10. Probar el sistema en Gemini

Aquí Gemini actúa como **el sistema bajo prueba**, no como el oráculo. Copia cada bloque tal cual, en un chat nuevo.

## Mensaje 1: el contrato

````text
Vas a actuar como el motor de recomendación del Portal de Acompañamiento.
Sigue estrictamente este contrato. No inventes reglas, no supongas datos faltantes
y no expliques nada.

# 1. Contrato del sistema: motor de recomendación del Portal de Acompañamiento

El sistema recibe el perfil de un estudiante (E) y produce una propuesta de apoyo (plan financiero y/o tutoría). Siguiendo el esquema del tablero, el sistema es una cadena de pasos y **cada paso tiene su propio contrato de entrada (E) y salida (S)**:

```
E ──> [ Paso 1: Validar perfil ] ──> [ Paso 2: Clasificar riesgo ] ──> [ Paso 3: Recomendar plan ]
            │ S1                            │ S2                              │ S3
```

## Entrada E (perfil del estudiante)

| Campo | Tipo | Rango / valores permitidos | Obligatorio |
|---|---|---|---|
| id_estudiante | texto | no vacío | sí |
| nivel | texto | `pregrado` | sí |
| matriculado | booleano | `true` | sí |
| semestre | entero | 1 a 12 | sí |
| promedio | decimal | 0.0 a 5.0 (puede ser vacío **solo** en semestre 1) | sí |
| materias_inscritas | entero | 1 a 8 | sí |
| materias_perdidas | entero | 0 a 8 y ≤ materias_inscritas | sí |
| saldo_pendiente | entero (COP) | 0 a 20.000.000 | sí |
| ingreso_hogar_smmlv | decimal | 0 a 20 salarios mínimos | sí |
| estrato | entero | 1 a 6 | sí |
| distancia_km | decimal | 0 a 100 | sí |
| solicita | texto | `financiero`, `tutoria`, `ambos` | sí |

## Paso 1: Validar perfil

- **E:** el perfil crudo.
- **S1:** `valido` con el perfil, o una salida terminal:
  - `error(tipo_invalido | fuera_de_rango | valor_no_permitido)`: el dato está mal formado. Error controlado, nunca una excepción.
  - `abstener(campo_faltante)`: falta un dato obligatorio.
  - `abstener(datos_contradictorios)`: materias perdidas > inscritas, o estrato ≥ 5 con ingreso < 1 SMMLV.
  - `abstener(fuera_de_poblacion)`: no es de pregrado o no está matriculado.
- **Abstenerse** significa: no generar ningún plan y remitir el caso a un asesor humano del comité de apoyo.

## Paso 2: Clasificar riesgo

- **E:** perfil válido (S1).
- **S2:** `riesgo_financiero` y `riesgo_academico`.

| Riesgo financiero | Regla |
|---|---|
| alto | saldo > 0 y (ingreso ≤ 2 SMMLV o estrato ≤ 2) |
| medio | saldo > 0 e ingreso ≤ 4 SMMLV |
| bajo | cualquier otro caso |

| Riesgo académico | Regla |
|---|---|
| alto | promedio < 3.0 o materias perdidas ≥ 2 |
| medio | promedio < 3.5 o materias perdidas = 1 |
| bajo | cualquier otro caso |
| sin_datos | semestre 1 sin promedio |

## Paso 3: Recomendar plan

- **E:** S2.
- **S3:** `plan` con cuatro beneficios, que corresponden a las pantallas del prototipo:

| Beneficio | Se otorga cuando |
|---|---|
| Reestructuración de matrícula (4 cuotas sin intereses) | pide apoyo financiero y riesgo financiero alto o medio |
| Beca de alimentación (100% almuerzos) | pide apoyo financiero y riesgo financiero alto |
| Bono de transporte mensual | pide apoyo financiero, riesgo alto o medio y distancia ≥ 5 km |
| Tutoría | `academica_prioritaria` si el riesgo académico es alto (aunque no la pida); `academica` si es medio y la pide; `orientacion` si la pide en otro caso; `ninguna` si no |

## Garantías del contrato

1. Nunca lanza una excepción: toda entrada termina en `plan`, `abstener` o `error`.
2. Nunca inventa datos que faltan (no asume saldo 0 ni promedio 0).
3. Nunca otorga beneficios a alguien fuera de la población (posgrado, no matriculados).
4. Los umbrales son inclusivos tal como están escritos (≤ 2 SMMLV, ≥ 5 km).


Formato de respuesta, por cada caso:
{"id": "...", "S1": "valido" o {"decision": "error" | "abstener", "motivo": "..."}, "S2": {"riesgo_financiero": "...", "riesgo_academico": "..."} o null, "S3": {"decision": "plan", "cuotas": 0 o 4, "beca_alimentacion": true/false, "bono_transporte": true/false, "tutoria": "academica_prioritaria" | "academica" | "orientacion" | "ninguna"} o null}

Si S1 no es "valido", S2 y S3 deben ser null.
Responde solo "Listo" si entendiste.
````

## Mensaje 2: los 20 casos

````text
Procesa estos 20 casos. Responde ÚNICAMENTE con un arreglo JSON (un objeto por caso,
en el mismo orden), sin texto antes ni después.

[
 {
  "id": "R01",
  "entrada": {
   "id_estudiante": "EST-1021",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 3,
   "promedio": 3.2,
   "materias_inscritas": 6,
   "materias_perdidas": 1,
   "saldo_pendiente": 2400000,
   "ingreso_hogar_smmlv": 1.5,
   "estrato": 2,
   "distancia_km": 12,
   "solicita": "ambos"
  }
 },
 {
  "id": "R02",
  "entrada": {
   "id_estudiante": "EST-0877",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 7,
   "promedio": 4.1,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 0,
   "ingreso_hogar_smmlv": 5,
   "estrato": 4,
   "distancia_km": 3,
   "solicita": "tutoria"
  }
 },
 {
  "id": "R03",
  "entrada": {
   "id_estudiante": "EST-1450",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 1,
   "promedio": 2.6,
   "materias_inscritas": 6,
   "materias_perdidas": 3,
   "saldo_pendiente": 1800000,
   "ingreso_hogar_smmlv": 2.5,
   "estrato": 3,
   "distancia_km": 4,
   "solicita": "ambos"
  }
 },
 {
  "id": "R04",
  "entrada": {
   "id_estudiante": "EST-0632",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 5,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 3200000,
   "ingreso_hogar_smmlv": 1.0,
   "estrato": 1,
   "distancia_km": 25,
   "solicita": "financiero"
  }
 },
 {
  "id": "R05",
  "entrada": {
   "id_estudiante": "EST-0998",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 9,
   "promedio": 3.4,
   "materias_inscritas": 4,
   "materias_perdidas": 0,
   "saldo_pendiente": 900000,
   "ingreso_hogar_smmlv": 3.5,
   "estrato": 3,
   "distancia_km": 8,
   "solicita": "ambos"
  }
 },
 {
  "id": "S01",
  "entrada": {
   "id_estudiante": "SIM-01",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S02",
  "entrada": {
   "id_estudiante": "SIM-02",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "financiero"
  }
 },
 {
  "id": "S03",
  "entrada": {
   "id_estudiante": "SIM-03",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 7.5,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S04",
  "entrada": {
   "id_estudiante": "SIM-04",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": -500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S05",
  "entrada": {
   "id_estudiante": "SIM-05",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 3,
   "materias_perdidas": 5,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S06",
  "entrada": {
   "id_estudiante": "SIM-06",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 8000000,
   "ingreso_hogar_smmlv": 0.3,
   "estrato": 6,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S07",
  "entrada": {
   "id_estudiante": "SIM-07",
   "nivel": "pregrado",
   "matriculado": false,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S08",
  "entrada": {
   "id_estudiante": "SIM-08",
   "nivel": "posgrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 9000000,
   "ingreso_hogar_smmlv": 1.5,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S09",
  "entrada": {
   "id_estudiante": "SIM-09",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.0,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 0,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "tutoria"
  }
 },
 {
  "id": "S10",
  "entrada": {
   "id_estudiante": "SIM-10",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.9,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1000000,
   "ingreso_hogar_smmlv": 2.0,
   "estrato": 3,
   "distancia_km": 2,
   "solicita": "financiero"
  }
 },
 {
  "id": "S11",
  "entrada": {
   "id_estudiante": "SIM-11",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 4.0,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1200000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 5.0,
   "solicita": "financiero"
  }
 },
 {
  "id": "S12",
  "entrada": {
   "id_estudiante": "SIM-12",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 95000000,
   "ingreso_hogar_smmlv": 1.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S13",
  "entrada": {
   "id_estudiante": "SIM-13",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 4,
   "promedio": "tres punto cinco",
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S14",
  "entrada": {
   "id_estudiante": "SIM-14",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 14,
   "promedio": 3.8,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 3.0,
   "estrato": 3,
   "distancia_km": 6,
   "solicita": "ambos"
  }
 },
 {
  "id": "S15",
  "entrada": {
   "id_estudiante": "SIM-15",
   "nivel": "pregrado",
   "matriculado": true,
   "semestre": 1,
   "promedio": null,
   "materias_inscritas": 5,
   "materias_perdidas": 0,
   "saldo_pendiente": 1500000,
   "ingreso_hogar_smmlv": 1.8,
   "estrato": 2,
   "distancia_km": 2,
   "solicita": "ambos"
  }
 }
]
````

## Mensaje 3 (opcional): pedir la justificación de los que fallen

````text
Para los casos <IDs que fallaron>, explica paso a paso qué regla del contrato aplicaste.
````

## Cómo comparar

1. Copia el arreglo JSON que te devuelva Gemini y guárdalo como `gemini_respuestas.json` en esta carpeta (o pégamelo en el chat).
2. Ejecuta `python3 comparar_gemini.py`. El script compara cada respuesta con `04_oraculo.json` y escribe `resultados_gemini.csv` con PASA o FALLA.
