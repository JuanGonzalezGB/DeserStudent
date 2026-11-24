"""Escribe 03_dataset.json (entradas) y 04_oraculo.json (respuestas esperadas) por separado."""
import json

def base(**kw):
    e = {"id_estudiante": "", "nivel": "pregrado", "matriculado": True, "semestre": 4,
         "promedio": 3.8, "materias_inscritas": 5, "materias_perdidas": 0,
         "saldo_pendiente": 1_500_000, "ingreso_hogar_smmlv": 3.0, "estrato": 3,
         "distancia_km": 6, "solicita": "ambos"}
    e.update(kw)
    return e

casos = [
 # ---- 5 entradas reales (perfiles típicos) ----
 ("R01","real","típico", base(id_estudiante="EST-1021", semestre=3, promedio=3.2, materias_inscritas=6, materias_perdidas=1, saldo_pendiente=2_400_000, ingreso_hogar_smmlv=1.5, estrato=2, distancia_km=12), "Perfil más común: bajo ingreso, una materia perdida, pide ambos apoyos."),
 ("R02","real","típico", base(id_estudiante="EST-0877", semestre=7, promedio=4.1, saldo_pendiente=0, ingreso_hogar_smmlv=5, estrato=4, distancia_km=3, solicita="tutoria"), "Estudiante al día que solo quiere orientación."),
 ("R03","real","típico", base(id_estudiante="EST-1450", semestre=1, promedio=2.6, materias_inscritas=6, materias_perdidas=3, saldo_pendiente=1_800_000, ingreso_hogar_smmlv=2.5, estrato=3, distancia_km=4), "Primer semestre con bajo rendimiento: activa tutoría prioritaria."),
 ("R04","real","típico", base(id_estudiante="EST-0632", semestre=5, promedio=3.8, saldo_pendiente=3_200_000, ingreso_hogar_smmlv=1.0, estrato=1, distancia_km=25, solicita="financiero"), "Solo pide apoyo financiero, vive lejos."),
 ("R05","real","típico", base(id_estudiante="EST-0998", semestre=9, promedio=3.4, materias_inscritas=4, saldo_pendiente=900_000, ingreso_hogar_smmlv=3.5, estrato=3, distancia_km=8), "Riesgo medio en ambas dimensiones."),
 # ---- 15 entradas adversariales ----
 ("S01","simulado","incompleto", {k:v for k,v in base(id_estudiante="SIM-01").items() if k!="promedio"}, "Falta el promedio: sin él no se puede clasificar el riesgo académico."),
 ("S02","simulado","incompleto", {k:v for k,v in base(id_estudiante="SIM-02", solicita="financiero").items() if k!="saldo_pendiente"}, "Pide apoyo financiero pero no hay saldo: el sistema podría asumir 0 y negar el apoyo."),
 ("S03","simulado","fuera de rango", base(id_estudiante="SIM-03", promedio=7.5), "Promedio en escala 0-10 en lugar de 0-5 (dato de otra institución)."),
 ("S04","simulado","fuera de rango", base(id_estudiante="SIM-04", saldo_pendiente=-500_000), "Saldo negativo (saldo a favor) mal cargado."),
 ("S05","simulado","contradictorio", base(id_estudiante="SIM-05", materias_inscritas=3, materias_perdidas=5), "Perdió más materias de las que inscribió."),
 ("S06","simulado","contradictorio", base(id_estudiante="SIM-06", estrato=6, ingreso_hogar_smmlv=0.3, saldo_pendiente=8_000_000), "Estrato 6 con ingreso menor a 1 SMMLV: posible error o fraude, el sistema daría beca completa."),
 ("S07","simulado","otra población", base(id_estudiante="SIM-07", matriculado=False), "No está matriculado este semestre: los beneficios no aplican."),
 ("S08","simulado","otra población", base(id_estudiante="SIM-08", nivel="posgrado", saldo_pendiente=9_000_000, ingreso_hogar_smmlv=1.5), "Estudiante de posgrado: el sistema se diseñó para pregrado."),
 ("S09","simulado","extremo", base(id_estudiante="SIM-09", promedio=3.0, saldo_pendiente=0, solicita="tutoria"), "Promedio exactamente en el umbral 3.0."),
 ("S10","simulado","extremo", base(id_estudiante="SIM-10", promedio=3.9, saldo_pendiente=1_000_000, ingreso_hogar_smmlv=2.0, estrato=3, distancia_km=2, solicita="financiero"), "Ingreso exactamente en el umbral de 2 SMMLV."),
 ("S11","simulado","extremo", base(id_estudiante="SIM-11", promedio=4.0, saldo_pendiente=1_200_000, ingreso_hogar_smmlv=3.0, estrato=3, distancia_km=5.0, solicita="financiero"), "Distancia exactamente en el umbral de 5 km del bono de transporte."),
 ("S12","simulado","fuera de rango", base(id_estudiante="SIM-12", saldo_pendiente=95_000_000, ingreso_hogar_smmlv=1.0), "Saldo absurdo (error de digitación con ceros de más)."),
 ("S13","simulado","tipo inválido", base(id_estudiante="SIM-13", promedio="tres punto cinco"), "Promedio escrito como texto desde un formulario libre."),
 ("S14","simulado","fuera de rango", base(id_estudiante="SIM-14", semestre=14), "Semestre mayor al máximo del programa."),
 ("S15","simulado","abstención/extremo", base(id_estudiante="SIM-15", semestre=1, promedio=None, saldo_pendiente=1_500_000, ingreso_hogar_smmlv=1.8, estrato=2, distancia_km=2), "Primer semestre sin notas aún: el promedio vacío es legítimo, no un campo faltante."),
]

plan = lambda c,b,t,tu: {"decision":"plan","cuotas":c,"beca_alimentacion":b,"bono_transporte":t,"tutoria":tu}
oraculo = {
 "R01": plan(4,True,True,"academica"),
 "R02": plan(0,False,False,"orientacion"),
 "R03": plan(4,False,False,"academica_prioritaria"),
 "R04": plan(4,True,True,"ninguna"),
 "R05": plan(4,False,True,"academica"),
 "S01": {"decision":"abstener","motivo":"campo_faltante"},
 "S02": {"decision":"abstener","motivo":"campo_faltante"},
 "S03": {"decision":"error","motivo":"fuera_de_rango"},
 "S04": {"decision":"error","motivo":"fuera_de_rango"},
 "S05": {"decision":"abstener","motivo":"datos_contradictorios"},
 "S06": {"decision":"abstener","motivo":"datos_contradictorios"},
 "S07": {"decision":"abstener","motivo":"fuera_de_poblacion"},
 "S08": {"decision":"abstener","motivo":"fuera_de_poblacion"},
 "S09": plan(0,False,False,"academica"),
 "S10": plan(4,True,False,"ninguna"),
 "S11": plan(4,False,True,"ninguna"),
 "S12": {"decision":"error","motivo":"fuera_de_rango"},
 "S13": {"decision":"error","motivo":"tipo_invalido"},
 "S14": {"decision":"error","motivo":"fuera_de_rango"},
 "S15": plan(4,True,False,"orientacion"),
}

json.dump([{"id":i,"origen":o,"categoria":c,"entrada":e,"por_que_es_dificil":w} for i,o,c,e,w in casos],
          open("03_dataset.json","w"), ensure_ascii=False, indent=2)
json.dump(oraculo, open("04_oraculo.json","w"), ensure_ascii=False, indent=2)
print(len(casos), "casos")
