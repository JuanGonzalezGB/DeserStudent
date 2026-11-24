"""
CLI: procesa un dataset de entradas contra un oráculo y reporta PASA / FALLA.

Uso:
    python ejecutar_pruebas.py --dataset 03_dataset_ejemplo.json --oraculo 04_oraculo_ejemplo.json

El dataset es una lista de {"id": ..., "entrada": {...}}.
El oráculo es un dict {id: esperado}. Acepta dos formatos de "esperado":
  - Por pasos: {"S1": ..., "S2": ..., "S3": ...}  -> compara S1, S2 y S3.
  - Solo salida final (formato de la carpeta principal), por ejemplo
    {"decision": "plan", "cuotas": 4, ...} o {"decision": "abstener", "motivo": "..."}
    -> compara la salida final del sistema.
"""

import argparse
import csv
import json
import sys

from motor import procesar_estudiante

CAMPOS_PLAN = ("decision", "cuotas", "beca_alimentacion", "bono_transporte", "tutoria")


def salida_final(obtenido):
    return obtenido["S1"] if obtenido["S1"] != "valido" else obtenido["S3"]


def _comparar_dict(etiqueta, esperado, obtenido, claves):
    obtenido = obtenido or {}
    return [f"{etiqueta}.{c}: esperado={esperado.get(c)!r} obtenido={obtenido.get(c)!r}"
            for c in claves if esperado.get(c) != obtenido.get(c)]


def comparar(esperado, obtenido):
    """Devuelve la lista de diferencias; vacía significa PASA."""
    if "S1" in esperado:                                   # formato por pasos
        difs = []
        e1, o1 = esperado["S1"], obtenido["S1"]
        if isinstance(e1, dict):
            difs += _comparar_dict("S1", e1, o1 if isinstance(o1, dict) else {"decision": o1}, e1.keys())
        elif e1 != o1:
            difs.append(f"S1: esperado={e1!r} obtenido={o1!r}")
        for paso in ("S2", "S3"):
            e, o = esperado.get(paso), obtenido.get(paso)
            if e is None or o is None:
                if e != o:
                    difs.append(f"{paso}: esperado={e!r} obtenido={o!r}")
            else:
                difs += _comparar_dict(paso, e, o, e.keys())
        return difs
    final = salida_final(obtenido)                          # formato solo salida final
    if not isinstance(final, dict):
        final = {"decision": final}
    claves = CAMPOS_PLAN if esperado.get("decision") == "plan" else ("decision", "motivo")
    return _comparar_dict("salida", esperado, final, claves)


def resumir(obtenido):
    s1 = obtenido["S1"]
    if s1 != "valido":
        return f"{s1['decision']}({s1['motivo']}: {s1['campo']})"
    s2, s3 = obtenido["S2"], obtenido["S3"]
    return (f"fin={s2['riesgo_financiero']} aca={s2['riesgo_academico']} | "
            f"cuotas={s3['cuotas']} beca={s3['beca_alimentacion']} "
            f"bono={s3['bono_transporte']} tutoria={s3['tutoria']}")


def cargar_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"No se pudo leer {ruta}: {exc}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pruebas de estrés del motor del Portal de Acompañamiento")
    parser.add_argument("--dataset", required=True, help="JSON con la lista de casos de entrada")
    parser.add_argument("--oraculo", required=True, help="JSON con las respuestas esperadas por id")
    parser.add_argument("--salida", default="resultados_ejecucion.csv", help="CSV de resultados")
    args = parser.parse_args(argv)

    casos = cargar_json(args.dataset)
    oraculo = cargar_json(args.oraculo)

    filas = []
    for caso in casos:
        id_caso = caso["id"]
        obtenido = procesar_estudiante(caso["entrada"])
        if id_caso not in oraculo:
            estado, difs = "SIN_ORACULO", []
        else:
            difs = comparar(oraculo[id_caso], obtenido)
            estado = "PASA" if not difs else "FALLA"
        filas.append({"id": id_caso, "estado": estado, "obtenido": resumir(obtenido),
                      "motivo_falla": "; ".join(difs),
                      "salida_completa": json.dumps(obtenido, ensure_ascii=False)})

    ancho_obt = max(len(f["obtenido"]) for f in filas)
    print(f"{'ID':<6} {'ESTADO':<12} {'OBTENIDO':<{ancho_obt}}  MOTIVO DE LA FALLA")
    print("-" * (22 + ancho_obt + 20))
    for f in filas:
        print(f"{f['id']:<6} {f['estado']:<12} {f['obtenido']:<{ancho_obt}}  {f['motivo_falla']}")

    evaluados = [f for f in filas if f["estado"] != "SIN_ORACULO"]
    pasan = sum(f["estado"] == "PASA" for f in evaluados)
    tasa = 100 * pasan / len(evaluados) if evaluados else 0.0
    print("-" * (22 + ancho_obt + 20))
    print(f"Pasan {pasan}/{len(evaluados)}  ·  tasa de éxito {tasa:.1f}%")

    with open(args.salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)
    print(f"Resultados exportados a {args.salida}")
    return 0 if pasan == len(evaluados) else 1


if __name__ == "__main__":
    sys.exit(main())
