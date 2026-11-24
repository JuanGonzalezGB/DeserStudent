# Datasets Públicos sobre Deserción en Educación Superior

A continuación se detallan los enlaces directos a los datasets públicos verificados, disponibles para descarga inmediata (sin trámites institucionales) que contienen registros anonimizados a nivel de estudiante.

## 1. Datasets Contexto Colombia (Microdatos)

Debido a restricciones de privacidad (Ley 1581) en los portales gubernamentales directos como `datos.gov.co` o los tableros del MEN/SPADIES, los microdatos granulares a nivel de individuo se obtienen mejor a través de investigaciones de datos abiertos alojadas en repositorios científicos.

### A. Factores de deserción y graduación en universidad pública (Cúcuta, Colombia)
*   **Fuente:** Mendeley Data.
*   **Enlace de descarga:** [https://data.mendeley.com/datasets/9rw37dmx6s](https://data.mendeley.com/datasets/9rw37dmx6s)
*   **Variables útiles:** Estrato, promedio, semestre, materias perdidas, estado (Dropout/Graduate).

### B. Trayectorias Educativas y Resultados (Saber 11 - Saber Pro)
*   **Fuente:** Mendeley Data (Consolidado de microdatos ICFES).
*   **Enlace de descarga:** [https://data.mendeley.com/datasets/vnmf6n8987](https://data.mendeley.com/datasets/vnmf6n8987)
*   **Registros:** 332,933 estudiantes.
*   **Variables útiles:** Estrato, ingresos del hogar (SMMLV), apoyo financiero (beca/crédito), horas de trabajo. *(Nota: Requiere aproximar la variable objetivo de deserción cruzando a los estudiantes que presentaron Saber 11 y entraron a la universidad, pero nunca aparecieron en los registros de Saber Pro).*

---

## 2. Estándar Internacional (UCI Machine Learning Repository)

Este es el dataset de referencia académica creado por Realinho et al., basado en estudiantes de educación superior en Portugal. Es excelente para probar modelos predictivos iniciales, aunque carece del contexto socioeconómico específico de Colombia.

*   **Repositorio Oficial UCI:** [Predict students' dropout and academic success](https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success)
*   **Espejo en Kaggle:** [Predict Students Dropout and Academic Success](https://www.kaggle.com/datasets/naveenkumar20bps1137/predict-students-dropout-and-academic-success)
*   **Registros:** 4,424 estudiantes (filas) y 37 atributos (columnas).

### Mapeo de Variables (Dataset UCI vs Modelo de 14 variables)

| Tu Variable (`Modelo`) | Columna en Dataset UCI (`Realinho et al.`) | Estado de Mapeo y Estrategia |
| :--- | :--- | :--- |
| `promedio` | `Curricular units 1st sem (grade)` y `2nd sem` | **Aproximar:** Promediar el puntaje de ambos semestres. |
| `materias_perdidas` | `Curricular units (enrolled)` - `(approved)` | **Transformar:** Restar las materias aprobadas a las matriculadas. |
| `asistencia_pct` | *Ausente* | Solo dispone de la modalidad `Daytime/evening attendance`. |
| `semestre` | *Ausente* | Es un dataset estático de cierre de carrera. |
| `saldo_pendiente_cop` | `Debtor` / `Tuition fees up to date` | **Transformar:** Convertir en variable binaria de morosidad (0/1). |
| `ingreso_hogar_smmlv`| *Ausente* | Solo se puede aproximar con `Mother's/Father's occupation` o variables macro (`GDP`). |
| `estrato` | *Ausente* | Variable exclusiva del contexto socioeconómico colombiano. |
| `tiene_apoyo_financiero`| `Scholarship holder` | **Directa:** Variable binaria (1 = Becado, 0 = No). |
| `horas_trabajo_semana` | *Ausente* | No registra la intensidad laboral en horas. |
| `trabaja_en_area...` | *Ausente* | No hay detalles del tipo de empleo del estudiante. |
| `tiempo_desplazamiento`| `Displaced` | **Aproximar:** Marca 1 si el estudiante abandonó su ciudad natal para estudiar, 0 si es local. No mide minutos. |
| `personas_a_cargo` | `Marital status` | **Aproximar:** Se puede inferir la carga a partir de su estado civil. |
| `apoyo_familiar` | *Ausente* | No hay registro de apoyo psicológico o soporte familiar. |
| `primera_generacion` | `Mother's / Father's qualification` | **Transformar:** Clasificar con 1 (Sí) si ninguno de los padres tiene título de educación superior. |
| **`Target = Dropout`** | `Target` | **Directa:** Eliminar los registros "Enrolled" para mantener una clasificación binaria (Dropout vs Graduate). |