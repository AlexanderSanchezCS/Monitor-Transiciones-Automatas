# AUTÓMATAS — Monitor de Transiciones

Aplicación académica para el análisis de sesiones de compra mediante autómatas
finitos. El sistema reconstruye las cadenas de eventos de cada sesión, detecta
patrones anómalos y muestra el recorrido del AFD mínimo en una interfaz web.

## 1. Objetivo del proyecto

El monitor procesa eventos de una tienda en línea representados mediante el
alfabeto:

```text
Σ = {B, P, F, C, X, D, R, V}
```

El sistema identifica cuatro patrones:

| Patrón | Condición |
|---|---|
| P1 | La cadena contiene `BC` |
| P2 | La cadena contiene `CC` |
| P3 | La cadena comienza con `D` |
| P4 | La cadena comienza con `R` |

El AFD mínimo utiliza los estados `M0`, `M1`, `M2` y `M3`. `M0` es el estado
inicial y `M3` es el estado de aceptación para las sesiones anómalas.

## 2. Integrantes y responsabilidades

| Integrante | Responsabilidad |
|---|---|
| **Cristhian Danghelo Valverde Villamagua** | Documentación |
| **Ariel Alexander Tandazo Ruiz** | Monitor en Python |
| **Alexander Antonio Sánchez Azuero** | Código y pruebas |
| **Mateo Valentin Rojas Granda** | Modelo formal |

## 3. Requisitos

- Python 3.10 o superior.
- Navegador web actualizado.
- No se requieren dependencias externas para ejecutar la aplicación.

## 4. Ejecución de la aplicación web

Desde la raíz del proyecto:

```bash
python3 backend/server.py
```

Luego abre:

```text
http://localhost:8000
```

Si el puerto 8000 está ocupado:

```bash
PORT=8001 python3 backend/server.py
```

En ese caso, abre `http://localhost:8001`.

## 5. Estructura del proyecto

```text
proyecto-monitor/
├── README.md
├── datos/
│   ├── generador.py
│   ├── validacion.csv
│   ├── prueba.csv
│   ├── clave_prueba.csv
│   ├── auditoria_generacion.csv
│   └── hashes.sha256
├── automatas/
│   ├── afd_minimo.json
│   ├── afd_minimo.jff
│   ├── p1_bc.json
│   ├── p1_bc.jff
│   ├── p2_cc.json
│   ├── p2_cc.jff
│   ├── p3_inicio_d.json
│   ├── p3_inicio_d.jff
│   ├── p4_inicio_r.json
│   ├── p4_inicio_r.jff
│   └── patrones.json
├── monitor/
│   ├── automata.py
│   └── monitor.py
├── backend/
│   └── server.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── tests/
│   └── test_monitor.py
└── informe/
```

## 6. Responsabilidad de cada módulo

### `datos/generador.py`

Genera los datasets sintéticos con semillas reproducibles:

- `random.Random(2026)` para validación.
- `random.Random(2027)` para prueba.

También genera la clave de prueba, el archivo de auditoría y los hashes
SHA-256.

### `monitor/automata.py`

Contiene la lógica formal del autómata:

- Alfabeto.
- Estados.
- Función de transición.
- Simulación de cadenas.
- Validación de símbolos.
- Cierre de ε.
- Construcción por subconjuntos.
- Minimización de AFD.

### `monitor/monitor.py`

Contiene la lógica del monitor:

- Lectura de archivos CSV.
- Reconstrucción de sesiones.
- Detección de P1, P2, P3 y P4.
- Comparación con `clave_prueba.csv`.
- Cálculo de VP, FP, FN, TN, precisión, recall y exactitud.
- Reporte de resultados por consola.

### `backend/server.py`

Funciona como capa HTTP. Expone la lógica Python mediante las rutas:

```text
/api/summary
/api/patterns
/api/events
/api/sessions?dataset=validation
/api/sessions?dataset=test
/api/automaton
/api/analyze
```

También sirve los archivos estáticos del frontend.

### `frontend/`

Contiene la interfaz web del monitor:

- Resumen de resultados.
- Explorador de sesiones.
- Patrones detectados.
- Diagrama interactivo del AFD mínimo.
- Simulador paso a paso.
- Tabla formal de transición.
- Metodología del conjunto de datos.

### `automatas/`

Contiene las representaciones formales para documentación y revisión:

- Archivos `.json` para intercambio estructurado.
- Archivos `.jff` compatibles con JFLAP.
- Definiciones de los patrones individuales.

### `tests/`

Contiene las pruebas automáticas de equivalencia del AFD, lectura de datasets,
métricas y minimización.

## 7. Flujo de datos

```text
datos/*.csv
      ↓
monitor/monitor.py
      ↓
monitor/automata.py
      ↓
backend/server.py
      ↓
API JSON
      ↓
frontend/app.js
      ↓
Interfaz web
```

Una sesión se procesa de la siguiente manera:

1. Se leen los eventos del CSV.
2. Se agrupan por `id_sesion`.
3. Se reconstruye la secuencia de símbolos.
4. El AFD procesa la cadena desde `M0`.
5. Si termina en `M3`, se clasifica como anómala.
6. Los verificadores identifican el patrón específico.
7. En el conjunto de prueba se compara el resultado con `clave_prueba.csv`.

## 8. Datos sintéticos

El generador produce:

| Archivo | Contenido |
|---|---|
| `validacion.csv` | 300 sesiones etiquetadas y 1.557 eventos |
| `prueba.csv` | 60 sesiones sin etiqueta y 309 eventos |
| `clave_prueba.csv` | Etiquetas oficiales del conjunto de prueba |
| `auditoria_generacion.csv` | Trazabilidad y consistencia de cada sesión |
| `hashes.sha256` | Verificación de reproducibilidad |

Para regenerar los archivos:

```bash
python3 datos/generador.py
```

Las sesiones anómalas se construyen mediante la inyección controlada de los
patrones P1, P2, P3 y P4. Las sesiones normales incluyen casos cercanos que no
deben activar ningún patrón.

## 9. Reporte de métricas por consola

El monitor puede ejecutarse sin abrir la aplicación web:

```bash
python3 -m monitor.monitor validation
python3 -m monitor.monitor test
```

Resultados esperados con los datasets actuales:

```text
Validación: VP=54, FP=0, FN=0, TN=246
Prueba:     VP=11, FP=0, FN=0, TN=49
```

En ambos conjuntos, la precisión, el recall y la exactitud son del 100%.

## 10. Pruebas automáticas

Para ejecutar las pruebas:

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas comprueban:

- Equivalencia entre `afd_minimo.json` y la tabla Python.
- Existencia de 32 transiciones.
- Clasificación de cadenas normales y anómalas.
- Tratamiento de la cadena vacía.
- Métricas de validación y prueba.
- Coincidencia con la clave de prueba.
- Estados únicos después de minimizar el AFD.

## 11. Reproducibilidad y verificación

Para verificar que los archivos generados coinciden con sus hashes:

```bash
cd datos
sha256sum -c hashes.sha256
cd ..
```

La auditoría y las métricas se calculan a partir de los datos y las etiquetas
esperadas. No se utilizan valores manuales para clasificar las sesiones.

Los conteos del AFND unido y del AFD por subconjuntos solo deben incluirse en
el informe cuando sus tablas completas de transiciones hayan sido incorporadas
y ejecutadas por el código. El AFD mínimo actual sí está definido y verificado:

```text
4 estados
8 símbolos
32 transiciones
M0 inicial
M3 de aceptación
```

## 12. Documentación del proyecto

La carpeta `informe/` está destinada al informe final en PDF y a la
presentación. El informe debe incluir el método de generación de datos, la
definición formal de los autómatas, la implementación del monitor, las
métricas y las evidencias de reproducibilidad.
