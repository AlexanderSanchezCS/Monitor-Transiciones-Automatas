# Monitor de Transiciones con Autómatas Finitos

Proyecto para el análisis y monitoreo de transiciones en autómatas finitos aplicado a sesiones de compra de una tienda en línea.

## Objetivo

Representar y analizar las transiciones entre estados de un autómata.

## Ejecutar la aplicación

La aplicación utiliza Python estándar para el backend y HTML, CSS y JavaScript para el frontend. No requiere instalar dependencias externas.

```bash
python3 backend/server.py
```

Después, abre [http://localhost:8000](http://localhost:8000) en el navegador.

## Estructura

- `backend/`: API HTTP y entrega de archivos estáticos; no contiene la lógica académica.
- `frontend/`: consola web del monitor.
- `datos/`: generador y conjuntos CSV del experimento.
- `automatas/`: representaciones formales `.jff` y `.json` para abrir en JFLAP o reutilizar en otras herramientas.
- `monitor/automata.py`: alfabeto, estados, transiciones, simulación, cierre-ε, construcción por subconjuntos y minimización.
- `monitor/monitor.py`: lectura de CSV, reconstrucción de sesiones, detección de patrones y métricas.
- `informe/`: informe técnico y presentación.

## Flujo de datos y responsabilidades

```text
datos/*.csv
    ↓
monitor/monitor.py
    ↓ usa
monitor/automata.py
    ↓
backend/server.py → API JSON → frontend/app.js
```

La fuente de verdad del AFD mínimo está duplicada únicamente como formato de
intercambio en `automatas/afd_minimo.json` y `automatas/afd_minimo.jff`; la
aplicación carga la definición equivalente desde `monitor/automata.py`.

## Generación de datos sintéticos

Los conjuntos se generan con semillas fijas y no requieren dependencias externas:

```bash
python3 datos/generador.py
```

El generador crea:

- `datos/validacion.csv`: 300 sesiones etiquetadas y 1.557 eventos.
- `datos/prueba.csv`: 60 sesiones sin etiquetas y 309 eventos.
- `datos/clave_prueba.csv`: etiquetas reservadas para evaluar la prueba.
- `datos/auditoria_generacion.csv`: control de origen, longitud y consistencia por sesión.
- `datos/hashes.sha256`: huellas SHA-256 para verificar reproducibilidad.

La validación usa `random.Random(2026)` y la prueba `random.Random(2027)`. La distribución contiene 54 anomalías en validación y 11 en prueba; las sesiones normales incluyen casos cercanos como `BVC`, `BPXC`, `CVC`, `CPC`, `VD`, `BD`, `VR` y `BPR`.

## Vistas académicas de la aplicación

- **Autómata**: estados `M0` a `M3`, estado inicial, estado de aceptación, diagrama y tabla completa de 32 transiciones.
- **Comparación de modelos**: resumen de estados del AFND, AFD por subconjuntos y AFD mínimo.
- **Métricas**: verdaderos positivos, falsos positivos, falsos negativos, precisión y recall.
- **Simulador**: traza paso a paso de la cadena, estado final y explicación del lenguaje reconocido.

## Colaboradores

Proyecto académico de desarrollo colaborativo.
