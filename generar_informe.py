"""Construye 05_resultados.md a partir de los CSV de las dos rondas."""
import csv, json
casos = {c["id"]: c for c in json.load(open("03_dataset.json", encoding="utf-8"))}
r1 = list(csv.DictReader(open("resultados_ronda1_v1.csv", encoding="utf-8")))
r2 = list(csv.DictReader(open("resultados_ronda2_v2.csv", encoding="utf-8")))
causa = {
 "S06": "El paso 1 no revisaba la coherencia estrato/ingreso. Corregido: abstención por datos contradictorios.",
 "S08": "El paso 1 no revisaba el nivel. Corregido: abstención fuera de población.",
 "S10": "El paso 2 usaba `< 2` en vez de `≤ 2` SMMLV, contra lo que dice el contrato. Corregido el operador.",
 "S12": "El paso 1 no tenía tope de saldo. Corregido: rango 0 a 20.000.000.",
 "S13": "El paso 1 no validaba tipos y el sistema lanzó una excepción. Corregido: error controlado `tipo_invalido`.",
 "S15": "El paso 1 trataba el promedio vacío de primer semestre como faltante. Corregido: se acepta y el riesgo académico queda `sin_datos`.",
}
def esc(s): return s.replace("|", "\\|")
L = ["# 5. Resultados: esperado vs. obtenido", "",
     f"- **Ronda 1 (motor v1):** {sum(f['estado']=='PASA' for f in r1)}/20 pasan.",
     f"- **Ronda 2 (motor v2, con los fallos corregidos):** {sum(f['estado']=='PASA' for f in r2)}/20 pasan.", "",
     "Todos los resultados se obtuvieron ejecutando `python3 ejecutar_pruebas.py`. La traza de cada paso (S1, S2, S3) está en los CSV.", "",
     "## Ronda 1: tabla completa", "",
     "| ID | Origen | Categoría | Entrada (clave) | Esperado | Obtenido | Estado |", "|---|---|---|---|---|---|---|"]
for f in r1:
    L.append(f"| {f['id']} | {f['origen']} | {f['categoria']} | {esc(casos[f['id']]['por_que_es_dificil'])} | {esc(f['esperado'])} | {esc(f['obtenido'])} | **{f['estado']}** |")
L += ["", "## Ronda 1: fallos, causa y corrección", "", "| ID | Diferencia | Paso donde falla y corrección |", "|---|---|---|"]
for f in r1:
    if f["estado"] == "FALLA":
        L.append(f"| {f['id']} | {esc(f['diferencia'])} | {causa[f['id']]} |")
L += ["", "## Conclusiones", "",
      "1. Los 5 casos reales pasaron en la ronda 1: el camino feliz funcionaba. Todos los fallos salieron de los casos adversariales, que es justo lo que busca la práctica.",
      "2. Los 6 fallos están en los pasos 1 y 2. Cinco son validaciones que faltaban en la entrada y uno es un umbral mal implementado (`<` en vez de `≤`).",
      "3. Los fallos más graves son S06, S08 y S12: el sistema entregaba beca y bono a quien no debía, en vez de abstenerse o rechazar.",
      "4. S13 es el único fallo que rompe el sistema (excepción). El contrato exige error controlado.",
      "5. Ronda 2: los 20 casos pasan. El siguiente paso es generar 15 entradas nuevas con el prompt P2 para atacar los mismos puntos débiles desde otro ángulo, porque pasar los mismos casos que ya conocíamos no prueba que el sistema esté bien."]
open("05_resultados.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
