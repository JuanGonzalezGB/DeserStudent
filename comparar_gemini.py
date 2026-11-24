"""Compara las respuestas de Gemini (gemini_respuestas.json) con el oráculo y escribe resultados_gemini.csv."""
import csv, json
from ejecutar_pruebas import comparar

oraculo = json.load(open("04_oraculo.json", encoding="utf-8"))
texto = open("gemini_respuestas.json", encoding="utf-8").read().strip()
texto = texto[texto.find("["): texto.rfind("]") + 1]       # ignora ```json u otro texto alrededor
respuestas = {r["id"]: r for r in json.loads(texto)}

def aplanar(r):
    """Convierte la respuesta por pasos de Gemini en la salida final del sistema."""
    if r is None:
        return {"decision": "sin_respuesta"}
    if r.get("S1") != "valido":
        return r.get("S1") or {"decision": "sin_respuesta"}
    return r.get("S3") or {"decision": "sin_respuesta"}

filas, pasan = [], 0
for i, esperado in oraculo.items():
    obtenido = aplanar(respuestas.get(i))
    estado, dif = comparar(esperado, obtenido)
    pasan += estado == "PASA"
    filas.append({"id": i, "estado": estado, "diferencia": dif,
                  "esperado": json.dumps(esperado, ensure_ascii=False),
                  "obtenido_gemini": json.dumps(respuestas.get(i), ensure_ascii=False)})
    print(i, estado, dif)
with open("resultados_gemini.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
print(f"Gemini: {pasan}/{len(oraculo)} pasan")
