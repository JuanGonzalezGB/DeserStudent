"""Ejecuta el sistema sobre los 20 casos, compara contra el oráculo y escribe los resultados."""
import csv, json, sys
from motor import motor_v1, motor_v2

CAMPOS_PLAN = ["decision", "cuotas", "beca_alimentacion", "bono_transporte", "tutoria"]

def comparar(esperado, obtenido):
    campos = CAMPOS_PLAN if esperado["decision"] == "plan" else ["decision", "motivo"]
    difs = [f"{c}: esperado={esperado.get(c)} obtenido={obtenido.get(c)}"
            for c in campos if esperado.get(c) != obtenido.get(c)]
    return ("PASA" if not difs else "FALLA"), "; ".join(difs)

def resumen(r):
    if r["decision"] == "plan":
        return f"plan(cuotas={r['cuotas']}, beca={r['beca_alimentacion']}, bono={r['bono_transporte']}, tutoria={r['tutoria']})"
    return f"{r['decision']}({r.get('motivo')}: {r.get('detalle')})"

def ronda(nombre, motor, casos, oraculo):
    filas, fallas = [], 0
    for c in casos:
        obtenido, traza = motor(c["entrada"])
        estado, dif = comparar(oraculo[c["id"]], obtenido)
        fallas += estado == "FALLA"
        filas.append({"id": c["id"], "origen": c["origen"], "categoria": c["categoria"],
                      "esperado": resumen({**{"cuotas":0,"beca_alimentacion":False,"bono_transporte":False,"tutoria":None}, **oraculo[c["id"]]}) if oraculo[c["id"]]["decision"]=="plan" else f"{oraculo[c['id']]['decision']}({oraculo[c['id']]['motivo']})",
                      "obtenido": resumen(obtenido), "estado": estado, "diferencia": dif,
                      "traza_pasos": json.dumps(traza, ensure_ascii=False)})
    with open(f"resultados_{nombre}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
    print(f"{nombre}: {len(casos)-fallas}/{len(casos)} pasan")
    return filas

if __name__ == "__main__":
  casos = json.load(open("03_dataset.json", encoding="utf-8"))
  oraculo = json.load(open("04_oraculo.json", encoding="utf-8"))
  ronda("ronda1_v1", motor_v1, casos, oraculo)
  ronda("ronda2_v2", motor_v2, casos, oraculo)
