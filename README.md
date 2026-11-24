# Práctica: pruebas de estrés del Portal de Acompañamiento

**Sistema evaluado:** el motor que, a partir del perfil de un estudiante, propone el plan de apoyo financiero (cuotas, beca de alimentación, bono de transporte) y el tipo de tutoría. Es la lógica detrás de las pantallas del prototipo en Stitch. Lo modelamos como tres pasos encadenados (E → 1 → 2 → 3), tal como lo dibujó el profesor.

## Entregables del tablero

| Tablero | Archivo |
|---|---|
| 1. Contrato | `01_contrato.md` |
| 2. Simular data / 3. Data set simulado | `03_dataset.json` (S01 a S15, con "por qué es difícil") |
| 3. Comprobar E y S (data típica y extrema) | `04_oraculo.json` + `05_resultados.md` + CSV con la traza de cada paso |
| 4. Data real | `03_dataset.json` (R01 a R05) |
| Artefacto | `motor.py` + scripts + este paquete |
| Biblioteca P. | `02_biblioteca_prompts.md` |
| Diagrama | `06_diagrama.md` |

## Resultado

- Ronda 1: **14/20** pasan. Seis fallos, todos en casos adversariales (ver `05_resultados.md`).
- Ronda 2, con las correcciones: **20/20**.
- Ronda 2 con 15 casos nuevos de Gemini (A01 a A15): **14/15**. Falla A03 por un hueco del contrato (ver `09_ronda2_casos_nuevos.md`).

## Cómo reproducirlo

```bash
python3 generar_dataset.py     # escribe 03_dataset.json y 04_oraculo.json
python3 ejecutar_pruebas.py    # corre v1 y v2, escribe los CSV
python3 generar_informe.py     # escribe 05_resultados.md
python3 ronda2_nuevos_casos.py # corre A01 a A15 contra v2
```

## Cosas a revisar antes de entregar

1. **Los 5 "reales" no son datos reales:** son perfiles típicos inventados. Si pueden conseguir 5 casos reales anonimizados (o de compañeros), reemplácenlos en `generar_dataset.py`.
2. **El oráculo deben firmarlo ustedes.** La diapositiva insiste en que el modelo genera entradas y ustedes escriben las respuestas esperadas. Aquí todo lo armó Claude; revisen `04_oraculo.json` contra el contrato y ajústenlo si no están de acuerdo con alguna regla.
3. **El motor v1 se escribió a propósito solo con las reglas del camino feliz**, como suele quedar una primera versión, para que la ronda 1 encontrara fallos reales al ejecutarse.
4. **"Biblioteca P."** la interpretamos como biblioteca de prompts. Confírmenlo con el profesor.
