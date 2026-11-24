"""Ronda 2 con casos nuevos (A01-A15, propuestos por la gema de Gemini) contra el motor v2.
Escribe 07_dataset_ronda2.json, 08_oraculo_ronda2.json y resultados_ronda2_nuevos_v2.csv."""
import csv, json
from motor import motor_v2
from ejecutar_pruebas import comparar, resumen

def base(**kw):
    e = {"id_estudiante": "", "nivel": "pregrado", "matriculado": True, "semestre": 3,
         "promedio": 4.0, "materias_inscritas": 5, "materias_perdidas": 0, "saldo_pendiente": 0,
         "ingreso_hogar_smmlv": 3.0, "estrato": 3, "distancia_km": 3.0, "solicita": "ambos"}
    e.update(kw); return e

casos = [
 ("A01","tipo inválido", base(id_estudiante="EST-A01", semestre="primer semestre", promedio=3.8, ingreso_hogar_smmlv=1.5, estrato=2, solicita="tutoria"), "Semestre escrito como texto."),
 ("A02","extremo", base(id_estudiante="EST-A02", semestre=4, promedio=3.5, saldo_pendiente=1_500_000, distancia_km=4.0, solicita="tutoria"), "Promedio exactamente en el umbral 3.5."),
 ("A03","contradictorio", base(id_estudiante="EST-A03", promedio=3.2, materias_inscritas=4, saldo_pendiente=500_000, ingreso_hogar_smmlv=18.0, estrato=1, distancia_km=2.0, solicita="financiero"), "Estrato 1 con ingreso de 18 SMMLV."),
 ("A04","fuera de rango", base(id_estudiante="EST-A04", semestre=2, materias_inscritas=0, ingreso_hogar_smmlv=2.0, estrato=2, distancia_km=1.0, solicita="tutoria"), "Cero materias inscritas."),
 ("A05","incompleto", base(id_estudiante="EST-A05", semestre=5, promedio=2.8, materias_perdidas=2, saldo_pendiente=3_000_000, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=10.0, solicita=None), "Falta el campo solicita."),
 ("A06","extremo", base(id_estudiante="EST-A06", materias_inscritas=6, saldo_pendiente=1, ingreso_hogar_smmlv=2.0, estrato=2, distancia_km=4.99), "Varios umbrales a la vez: saldo $1, ingreso 2.0, distancia 4.99 km."),
 ("A07","otra población", base(id_estudiante="EST-A07", matriculado=False, semestre=1, promedio=None, materias_inscritas=4, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=8.0), "No matriculado, primer semestre sin promedio."),
 ("A08","fuera de rango", base(id_estudiante="EST-A08", semestre=2, promedio=3.8, distancia_km=-5.0, solicita="financiero"), "Distancia negativa."),
 ("A09","incompleto", base(id_estudiante="EST-A09", semestre=2, promedio=None, materias_inscritas=4, saldo_pendiente=1_000_000, ingreso_hogar_smmlv=1.5, estrato=2, distancia_km=6.0), "Promedio vacío en semestre 2 (solo se permite en semestre 1)."),
 ("A10","extremo", base(id_estudiante="EST-A10", semestre=4, promedio=1.2, materias_inscritas=8, materias_perdidas=8, ingreso_hogar_smmlv=5.0, estrato=4, distancia_km=2.0, solicita="tutoria"), "Perdió todas las materias (8 de 8)."),
 ("A11","valor no permitido", base(id_estudiante="EST-A11", promedio=4.1, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=12.0, solicita="beca_completa"), "Valor de solicita fuera de la lista."),
 ("A12","fuera de rango", base(id_estudiante="EST-A12", semestre=6, promedio=3.9, materias_inscritas=6, saldo_pendiente=25_000_000, ingreso_hogar_smmlv=2.0, estrato=2, solicita="financiero"), "Saldo por encima del tope."),
 ("A13","extremo", base(id_estudiante="EST-A13", semestre=2, promedio=2.5, ingreso_hogar_smmlv=6.0, estrato=4, distancia_km=1.0, solicita="financiero"), "Riesgo académico alto sin pedir tutoría."),
 ("A14","otra población", base(id_estudiante="EST-A14", nivel="doctorado", semestre=1, promedio=None, materias_inscritas=3, saldo_pendiente=5_000_000, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=15.0), "Nivel doctorado."),
 ("A15","extremo", base(id_estudiante="EST-A15", promedio=4.2, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=10.0, solicita="financiero"), "Pide apoyo financiero pero no debe nada."),
]
plan = lambda c,b,t,tu: {"decision":"plan","cuotas":c,"beca_alimentacion":b,"bono_transporte":t,"tutoria":tu}
oraculo = {
 "A01": {"decision":"error","motivo":"tipo_invalido"},
 "A02": plan(0,False,False,"orientacion"),      # CORREGIDO: Gemini decía cuotas=4, pero solo pidió tutoría
 "A03": {"decision":"abstener","motivo":"datos_contradictorios"},  # comportamiento deseado; el contrato v1 no lo cubre
 "A04": {"decision":"error","motivo":"fuera_de_rango"},
 "A05": {"decision":"abstener","motivo":"campo_faltante"},
 "A06": plan(4,True,False,"orientacion"),
 "A07": {"decision":"abstener","motivo":"fuera_de_poblacion"},
 "A08": {"decision":"error","motivo":"fuera_de_rango"},
 "A09": {"decision":"abstener","motivo":"campo_faltante"},
 "A10": plan(0,False,False,"academica_prioritaria"),
 "A11": {"decision":"error","motivo":"valor_no_permitido"},
 "A12": {"decision":"error","motivo":"fuera_de_rango"},
 "A13": plan(0,False,False,"academica_prioritaria"),
 "A14": {"decision":"abstener","motivo":"fuera_de_poblacion"},
 "A15": plan(0,False,False,"ninguna"),
}
json.dump([{"id":i,"origen":"simulado (Gemini)","categoria":c,"entrada":e,"por_que_es_dificil":w} for i,c,e,w in casos],
          open("07_dataset_ronda2.json","w"), ensure_ascii=False, indent=2)
json.dump(oraculo, open("08_oraculo_ronda2.json","w"), ensure_ascii=False, indent=2)

filas = []
for i,c,e,w in casos:
    obt, traza = motor_v2(e)
    est, dif = comparar(oraculo[i], obt)
    filas.append({"id":i,"categoria":c,"esperado":json.dumps(oraculo[i],ensure_ascii=False),"obtenido":resumen(obt),
                  "estado":est,"diferencia":dif,"traza_pasos":json.dumps(traza,ensure_ascii=False)})
    print(i, est, resumen(obt), dif)
with open("resultados_ronda2_nuevos_v2.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
print(sum(f["estado"]=="PASA" for f in filas), "/ 15 pasan")
