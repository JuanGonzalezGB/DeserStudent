# 6. Diagramas

## A. El sistema por pasos (lo del tablero: E → 1 → 2 → 3, cada paso con su S)

```mermaid
flowchart LR
    E(["E: perfil del estudiante"]) --> P1["Paso 1<br/>Validar perfil"]
    P1 -->|"S1: válido"| P2["Paso 2<br/>Clasificar riesgo"]
    P2 -->|"S2: riesgo financiero y académico"| P3["Paso 3<br/>Recomendar plan"]
    P3 --> S3(["S3: plan<br/>cuotas · beca · bono · tutoría"])
    P1 -->|"S1: error"| ERR(["Error controlado"])
    P1 -->|"S1: abstener"| ABS(["Remitir a asesor humano"])
```

## B. El proceso de la práctica

```mermaid
flowchart TD
    A["1. Contrato por pasos<br/>(01_contrato.md)"] --> B["2. 5 entradas reales<br/>(datos típicos)"]
    B --> C["3. El modelo genera 15 entradas adversariales<br/>con el prompt P1 (biblioteca de prompts)"]
    C --> D["Dataset simulado<br/>faltantes · contradictorios · otra población<br/>fuera de rango · extremos · abstención"]
    D --> O["4. Nosotros escribimos el oráculo<br/>(respuesta esperada, sin el modelo)"]
    O --> X["5. Ejecutar el sistema<br/>y guardar E y S de cada paso"]
    X --> K{"6. ¿Obtenido = esperado?"}
    K -- Sí --> OK["Registrar PASA"]
    K -- No --> F["Registrar FALLA:<br/>paso, causa, corrección"]
    F --> R["Corregir el sistema"]
    R --> X2["Ronda 2 (≈ 2 semanas después)<br/>con los fallos encontrados + prompt P2"]
    X2 --> X
    OK --> Z["7. Artefactos: contrato, biblioteca de prompts,<br/>dataset simulado, resultados"]
```

Para verlos como imagen: pega cada bloque en https://mermaid.live y exporta a PNG.
