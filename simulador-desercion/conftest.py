"""
Configuracion de pytest para el simulador.

Pone la raiz del proyecto en sys.path para que las pruebas puedan importar
config, db, app y el paquete modelo sin instalar nada, y ofrece los fixtures
compartidos por los seis archivos de prueba.
"""

import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# Registro valido de referencia: todos los campos en valores plausibles y de
# riesgo intermedio. Las pruebas parten de aqui y cambian UN campo a la vez.
REGISTRO_VALIDO = {
    "promedio": 3.5,
    "materias_perdidas": 1,
    "asistencia_pct": 85.0,
    "semestre": 4,
    "saldo_pendiente_cop": 2_000_000,
    "ingreso_hogar_smmlv": 3.0,
    "estrato": 3,
    "tiene_apoyo_financiero": False,
    "horas_trabajo_semana": 15.0,
    "trabaja_en_area_de_estudio": False,
    "tiempo_desplazamiento_min": 40,
    "personas_a_cargo": 1,
    "apoyo_familiar": 4,
    "primera_generacion_universitaria": False,
}


@pytest.fixture
def registro():
    """Una copia fresca del registro valido de referencia."""
    return dict(REGISTRO_VALIDO)


@pytest.fixture
def ruta_db(tmp_path):
    """Ruta a una base de datos SQLite temporal, propia de cada prueba."""
    return str(tmp_path / "simulador_prueba.db")


@pytest.fixture
def cliente(ruta_db):
    """Cliente de prueba de Flask apuntando a la base temporal."""
    import app as modulo_app

    aplicacion = modulo_app.create_app(ruta_db=ruta_db)
    aplicacion.config["TESTING"] = True
    with aplicacion.test_client() as c:
        yield c
