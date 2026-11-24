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
