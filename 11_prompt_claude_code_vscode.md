# 11. Prompt para Claude Code en VS Code

**Antes de pegarlo:**
1. Abre en VS Code una carpeta vacía para el proyecto, por ejemplo `practica-pruebas-estres`.
2. Adjunta (o arrastra al chat) estos archivos:
   - De `cli/`: `motor.py`, `ejecutar_pruebas.py`, `test_motor.py`, `03_dataset_ejemplo.json`, `04_oraculo_ejemplo.json`, `README.md`
   - De la carpeta principal: `03_dataset.json`, `04_oraculo.json`, `07_dataset_ronda2.json`, `08_oraculo_ronda2.json`, `01_contrato.md`
3. Copia y pega el bloque de abajo.

---

```text
<rol>
Eres un ingeniero de Python y QA. Vas a montar en este workspace un proyecto que YA ESTÁ
ESCRITO Y PROBADO: tu trabajo es instalarlo, ejecutarlo y verificarlo, no rediseñarlo.
</rol>

<contexto>
Es una práctica universitaria de "pruebas de estrés de un sistema con datos". El sistema es
el motor de recomendación de un Portal de Acompañamiento estudiantil: recibe el perfil de un
estudiante (E) y lo procesa en tres pasos encadenados con cortocircuito:
  Paso 1 validar perfil (S1) -> Paso 2 clasificar riesgo (S2) -> Paso 3 recomendar plan (S3).
Si S1 no es "valido", S2 y S3 son null. El contrato completo está en 01_contrato.md.
Te adjunto todos los archivos del proyecto.
</contexto>

<tarea>
1. Crea esta estructura en la raíz del workspace y copia cada archivo adjunto SIN CAMBIAR
   SU CONTENIDO (byte a byte):
     cli/motor.py
     cli/ejecutar_pruebas.py
     cli/test_motor.py
     cli/03_dataset_ejemplo.json
     cli/04_oraculo_ejemplo.json
     cli/README.md
     01_contrato.md
     03_dataset.json
     04_oraculo.json
     07_dataset_ronda2.json
     08_oraculo_ronda2.json
2. Detecta mi sistema operativo y, dentro de cli/, crea y activa un entorno virtual (venv).
3. Instala pytest dentro del venv. No instales ninguna otra dependencia: el código solo usa
   la librería estándar.
4. Crea cli/requirements.txt con una sola línea: pytest
5. Crea un .gitignore en la raíz con: venv/, __pycache__/, .pytest_cache/, *.csv
6. Desde cli/, ejecuta y muéstrame la salida de:
     pytest -v
     python ejecutar_pruebas.py --dataset 03_dataset_ejemplo.json --oraculo 04_oraculo_ejemplo.json
     python ejecutar_pruebas.py --dataset ../03_dataset.json --oraculo ../04_oraculo.json --salida resultados_ronda1.csv
     python ejecutar_pruebas.py --dataset ../07_dataset_ronda2.json --oraculo ../08_oraculo_ronda2.json --salida resultados_ronda2.csv
</tarea>

<resultados_esperados>
- pytest: 89 passed.
- Dataset de ejemplo: 5/5 pasan.
- Ronda 1: 20/20 pasan.
- Ronda 2: 14/15 pasan. El caso A03 FALLA A PROPÓSITO: es un hueco documentado del contrato
  (estrato 1 con ingreso de 18 SMMLV recibe beca). Por eso este último comando termina con
  código de salida 1. Eso es correcto y no es un error de instalación.
</resultados_esperados>

<restricciones>
- NO modifiques motor.py, ejecutar_pruebas.py, test_motor.py ni los JSON. No "corrijas" A03.
- NO borres, saltes ni marques como xfail ninguna prueba.
- Si un resultado no coincide con lo esperado, detente y explícame la causa probable
  (versión de Python, ruta, codificación, archivo mal copiado) antes de tocar cualquier cosa.
- Requiere Python 3.9 o superior. Si mi versión es menor, avísame en lugar de adaptar el código.
- En Windows, si PowerShell bloquea la activación del venv, usa
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` solo para esta sesión.
</restricciones>

<formato_de_respuesta>
Al terminar, responde en español con:
1. El árbol de archivos creado.
2. Una tabla: comando | resultado esperado | resultado obtenido | ¿coincide?
3. Los comandos exactos que yo debo escribir mañana para volver a correr todo
   (activar venv, pytest, CLI).
Nada más: sin propuestas de mejora ni refactorizaciones.
</formato_de_respuesta>
```
