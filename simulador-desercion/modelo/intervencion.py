"""
Paso 3 del simulador: decidir si el estudiante requiere intervencion y cual.

Regla de decision (seccion 7 del modelo):

    requiere_intervencion = (nivel == "alto")
                            or (nivel == "medio" and hay al menos un problema)

Un estudiante de nivel bajo nunca requiere intervencion, aunque tenga una
dimension problematica: el portal no puede priorizar a todo el mundo.

Tipo de intervencion, una por dimension problematica (s_d >= 0.60):

    academica  -> tutoria academica
    financiera -> plan de apoyo financiero (cuotas, beca de alimentacion,
                  bono de transporte: las mismas opciones del prototipo y
                  del motor de la entrega anterior)
    laboral    -> flexibilidad horaria / oferta en jornada nocturna
    personal   -> acompanamiento de bienestar universitario

Prioridad: la intervencion del factor principal (la dimension que mas aporta
al riesgo) va primero; las demas siguen ordenadas por subpuntaje.

Caso de borde cerrado a proposito: un estudiante de nivel alto cuyo riesgo
viene repartido entre varias dimensiones puede no tener NINGUNA dimension por
encima de 0.60. Requiere intervencion, pero la lista de problemas esta vacia.
En ese caso se le asigna la intervencion de su factor principal, para que
nunca quede "requiere intervencion" con un plan vacio.
"""

import config


def _plan(dimension, prioridad):
    """Una entrada del plan de intervencion, tomada del catalogo de config."""
    ficha = config.INTERVENCIONES[dimension]
    return {
        "dimension": dimension,
        "tipo": ficha["tipo"],
        "nombre": ficha["nombre"],
        "acciones": list(ficha["acciones"]),
        "prioridad": prioridad,
    }


def requiere_intervencion(nivel, problemas):
    """True si el estudiante entra al programa de acompanamiento."""
    if nivel == "alto":
        return True
    return nivel == "medio" and len(problemas) > 0


def decidir(nivel, problemas, factor_principal):
    """Paso 3 completo.

    nivel: "bajo" | "medio" | "alto" (de riesgo.nivel)
    problemas: dimensiones con s_d >= UMBRAL_PROBLEMA, de mayor a menor
    factor_principal: dimension con mayor contribucion b_d * s_d

    Devuelve {"requiere_intervencion": bool, "intervenciones": [...]}.
    """
    if not requiere_intervencion(nivel, problemas):
        return {"requiere_intervencion": False, "intervenciones": []}

    # El factor principal primero; detras, las demas dimensiones problematicas
    # conservando el orden por subpuntaje que trae la lista.
    ordenadas = [dim for dim in problemas if dim != factor_principal]
    if factor_principal in problemas:
        ordenadas.insert(0, factor_principal)
    elif not ordenadas:
        # Nivel alto sin ninguna dimension por encima del umbral: se atiende
        # el factor principal para no dejar el plan vacio.
        ordenadas = [factor_principal]

    intervenciones = [_plan(dim, i + 1) for i, dim in enumerate(ordenadas)]
    return {"requiere_intervencion": True, "intervenciones": intervenciones}
