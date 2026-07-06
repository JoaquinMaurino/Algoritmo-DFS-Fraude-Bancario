# Análisis y Estructura del Código: Proyecto Fraude Bancario

Este documento es una guía de estudio profundo del código fuente. Te servirá como material de apoyo para entender la arquitectura, el flujo de datos y las decisiones de diseño de cara a la exposición del trabajo práctico.

---

## 1. Arquitectura y Patrones de Diseño

El proyecto está diseñado con una arquitectura **modular y desacoplada**. En lugar de tener un solo archivo gigante o funciones que hacen todo a la vez, el código está dividido en capas de responsabilidad única:

1.  **Capa de Configuración (`src/config.py`)**: Centraliza las variables mágicas.
2.  **Capa de Datos (`src/data/`)**: Se encarga exclusivamente de leer el CSV y armar el grafo en memoria.
3.  **Capa de Algoritmos Base (`src/algorithms/dfs_core.py`)**: El "motor" matemático del proyecto.
4.  **Capa de Reglas de Negocio (`chain_analysis.py`, `cycle_detection.py`, `smurfing.py`)**: Utilizan el motor base para responder a las preguntas específicas del TP.
5.  **Capa de Presentación (`app.py`, `graph_renderer.py`, `pdf_report.py`)**: Interfaz de usuario, gráficos interactivos y exportación de documentos. Ninguno de estos archivos realiza cálculos de fraude por su cuenta.

---

## 2. Flujo de Información (El "Ciclo de Vida" de los Datos)

Cuando el usuario sube el archivo `Transacciones.csv` en la interfaz, el flujo es el siguiente:

1.  **Ingreso**: `app.py` recibe el archivo y se lo pasa a `load_graph_from_csv()` (en `graph_builder.py`).
2.  **Modelado**: `graph_builder.py` usa Pandas para leer el CSV, consolida aristas repetidas sumando sus montos, y construye un objeto `nx.DiGraph` (Grafo Dirigido de NetworkX).
3.  **Consulta**: Cuando el usuario hace clic en "Buscar cadenas", `app.py` invoca a una función de la capa de reglas de negocio (ej. `buscar_cadena_sospechosa_mas_larga()`).
4.  **Motor**: La regla de negocio configura parámetros (como profundidad máxima o filtros de monto) y llama al motor `dfs()` en `dfs_core.py`.
5.  **Respuesta**: El motor retorna los caminos encontrados, la regla de negocio los ordena y formatea, y `app.py` los envía a `graph_renderer.py` para dibujarlos en pantalla usando PyVis.

---

## 3. Análisis Detallado por Archivo

A continuación, repasamos la responsabilidad exacta de cada archivo y sus funciones clave.

### 3.1. El Núcleo: `src/algorithms/dfs_core.py`
Este es el archivo más importante del proyecto a nivel algorítmico. Contiene el motor de búsqueda.

*   **Responsabilidad**: Recorrer el grafo de forma segura y eficiente.
*   **Puntos Clave a explicar**:
    *   **DFS Iterativo**: En lugar de usar recursividad (que podría lanzar un error de `RecursionError` si la cadena es muy larga), implementa DFS usando una **pila explícita** (`pila = [...]` y `pila.pop()`).
    *   **Detección de Ciclos Controlada**: Usa una lista de `visitados` que viaja junto con cada camino explorado. Esto asegura que no se quede atrapado en un bucle infinito, ya que un nodo no se vuelve a visitar dentro del mismo camino.
    *   **Filtros Dinámicos**: Recibe un parámetro `edge_filter`. Esto permite que el DFS evalúe en tiempo real si debe cruzar una arista o no (por ejemplo, si el monto cumple con el mínimo requerido).

### 3.2. Reglas de Cadenas: `src/algorithms/chain_analysis.py`
*   **Responsabilidad**: Resolver las **Consignas 1, 2, 3 y 6**.
*   **Puntos Clave a explicar**:
    *   Reutiliza el motor DFS. No reinventa la rueda.
    *   Usa cierres (closures) como `_filtro_monto_minimo` para inyectar lógica de negocio dentro del recorrido genérico del DFS.
    *   **Deduplicación**: Implementa `_deduplicar_y_ordenar`, que usa un `frozenset` del camino. Si dos caminos son estructuralmente el mismo (solo encontrados en distinto orden), el `frozenset` generará el mismo hash y se eliminará el duplicado.
    1. El Monto Mínimo por Transacción (Filtro Dinámico)
No cualquier transferencia califica; todas las transferencias de la cadena deben involucrar grandes sumas de dinero (por ejemplo, transacciones mayores a $1,000,000).

¿Dónde se evalúa? En la función _filtro_monto_minimo(monto_minimo) (línea 21).
¿Cuándo se evalúa? Se evalúa en tiempo real mientras el algoritmo recorre el grafo. Este filtro se inyecta en el motor DFS. Si el motor está recorriendo una cadena (ej. cuenta A → cuenta B), y se da cuenta de que la transferencia fue de apenas $50, aborta la exploración de ese camino instantáneamente sin perder tiempo en revisar a quién le mandó la cuenta B después.
2. La Longitud de la Cadena (Mínimo y Máximo de Saltos)
Para que se considere una "cadena" de lavado y no una simple transferencia aislada, el dinero debe pasar por múltiples manos. Se usan dos parámetros: transacciones_minimas (generalmente 3) y transacciones_maximas (generalmente 5, para acotar la búsqueda).

¿Dónde se evalúa? En la función buscar_todas_las_cadenas_sospechosas (líneas 108 y 109).
¿Cuándo se evalúa? Se evalúa después de que el motor DFS terminó de construir un camino válido de altos montos. Si la ruta encontrada (hops) entra en el rango permitido (por ejemplo, entre 3 y 5 saltos), entonces se la guarda oficialmente como candidata de fraude.

### 3.3. Detección de Ciclos: `src/algorithms/cycle_detection.py`
*   **Responsabilidad**: Resolver las **Consignas 4 y 7**.
*   **Puntos Clave a explicar**:
    *   Llama al motor DFS encendiendo el flag `detect_cycles=True`.
    *   Verifica los resultados usando `_es_ciclo_cerrado` para confirmar que el último nodo destino de la cadena es exactamente igual al nodo desde donde arrancó la búsqueda.
    *   También utiliza `frozenset` para deduplicar. (A → B → C → A) es el mismo ciclo que (B → C → A → B).

### 3.4. Detección de Smurfing: `src/algorithms/smurfing.py`
*   **Responsabilidad**: Resolver la **Consigna 5**.
*   **Puntos Clave a explicar**:
    *   **NO usa DFS**. El smurfing es un patrón de profundidad fija (Origen → Intermediario → Destino).
    *   Usa inspección directa de vecinos (`grafo.successors(origen)`). Revisa si un intermediario reenvía el 80% o más de lo que recibió de un origen hacia un mismo destino.
    *   Usa un diccionario donde la clave es la tupla `(origen, destino)`. Si para una misma clave se agrupan 2 o más intermediarios válidos, se confirma el patrón de pitufeo (smurfing).

### 3.5. Visualización interactiva: `src/algorithms/graph_renderer.py`
*   **Responsabilidad**: Dibujar los grafos de NetworkX usando PyVis.
*   **Puntos Clave a explicar**:
    *   Retorna un `string` de código HTML (con `net.generate_html()`).
    *   Usa un esquema semántico de colores para ayudar al analista visualmente: Rojo para el Origen, Verde para el Destino final, Azul para intermediarios normales y Naranja para intermediarios cómplices (smurfs).

### 3.6. Interfaz Web: `app.py`
*   **Responsabilidad**: Renderizar la aplicación Streamlit e interactuar con el usuario.
*   **Puntos Clave a explicar**:
    *   Uso de `@st.cache_data` sobre la función de cargar el grafo. Esto es vital para el rendimiento: evita que el archivo CSV se lea y el grafo se reconstruya cada vez que el usuario hace clic en un botón.
    *   Uso de `st.components.v1.html` para incrustar de forma segura el HTML que genera PyVis dentro de la app de Streamlit.
    *   Implementa un truncamiento visual (`[:20]`). Debido a que algunos patrones pueden tener miles de resultados, la UI procesa todos pero solo renderiza el Top 20 para evitar colapsar la memoria del navegador.

### 3.7. Reportes: `src/reports/pdf_report.py`
*   **Responsabilidad**: Exportar el análisis a PDF.
*   **Puntos Clave a explicar**:
    *   Utiliza la librería `fpdf2`.
    *   Implementa funciones auxiliares (`format_nodes` y `trunc`) para asegurar que cadenas con muchísimos nodos no superen el ancho del papel A4, evitando excepciones por desbordamiento de línea que la librería PDF no sabe manejar internamente.

---

## 4. Resumen de Decisiones de Diseño para defender en la exposición

Si el jurado pregunta *"¿Por qué lo hicieron de esta manera?"*, aquí tienes los argumentos técnicos fuertes:

1.  **Por qué DFS propio y no `nx.all_simple_paths`**: NetworkX tiene funciones de caminos, pero no permiten inyectar lógica de filtrado *durante* el recorrido. Nuestro DFS permite abortar la búsqueda en una rama apenas detecta que el monto es menor al umbral, ahorrando muchísimo tiempo de procesamiento computacional.
2.  **Por qué DFS Iterativo con Pila y no Recursivo**: La recursividad consume espacio en el Call Stack de Python. Un grafo con una cadena de 1000 nodos haría colapsar el programa (`RecursionError`). La pila explícita (`list` que actúa como Stack) mueve la memoria al Heap, permitiendo recorrer grafos infinitamente profundos.
3.  **Por qué separar Smurfing del DFS**: El DFS es para caminos lineales de profundidad arbitraria. El smurfing requiere encontrar un abanico (múltiples intermediarios en paralelo conectando dos mismos puntos). Hacer esto con DFS sería forzar la herramienta equivocada para el trabajo. Iterar vecinos directamente es `O(N * K^2)`, que es rapidísimo.
4.  **Uso de `frozenset`**: Las listas en Python no son "hasheables", por lo que no sirven como claves de diccionario ni se pueden meter en un `set` para detectar duplicados. Un `frozenset` soluciona esto y además ignora el orden de los elementos, lo cual es matemáticamente perfecto para detectar si dos ciclos encontrados empezando desde distintos nodos contienen los mismos participantes.
