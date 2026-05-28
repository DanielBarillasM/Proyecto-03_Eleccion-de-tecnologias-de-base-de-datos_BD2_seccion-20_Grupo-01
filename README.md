# Proyecto 3 — Elección de Tecnología de Base de Datos

Curso: Bases de Datos 2 · Universidad del Valle de Guatemala

Aplicación para resolver rompecabezas físicos modelados como grafos usando **Python**, **Neo4j** y **Streamlit**.

Cada rompecabezas se representa como un grafo: las piezas son nodos y las conexiones entre conectores (tabs/huecos) son relaciones. El algoritmo BFS recorre el grafo desde una pieza inicial y genera instrucciones ordenadas de ensamblaje. Si hay piezas faltantes, el sistema arma todo lo posible y reporta qué quedó sin completar.

## Tecnologías

- **Python** — modelos de datos, algoritmo BFS, lógica de aplicación
- **Neo4j** — base de datos de grafos; piezas y conectores como nodos, conexiones como relaciones `CONNECTS_WITH`
- **Streamlit** — interfaz web
- **Cypher** — consultas sobre nodos `:Puzzle`, `:Piece`, `:Connector`

## Estructura

```
app/
  config.py   configuración desde .env
  models.py   dataclasses: Piece, Connector, PuzzleGraph, SolveResult
  neo4j.py    repositorio Neo4j (seed, list, get)
  solver.py   algoritmo BFS
  ui.py       interfaz Streamlit
docs/
  solution.tex  documento del proyecto
main.py
requirements.txt
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz:

```env
NEO4J_URI=neo4j+s://TU_INSTANCIA.databases.neo4j.io
NEO4J_USERNAME=tu_usuario
NEO4J_PASSWORD=tu_password
NEO4J_DATABASE=tu_database
```

## Ejecutar

```bash
streamlit run main.py
```

## Funcionalidad

**Pestaña Solve**
- Seleccionar rompecabezas y pieza inicial
- Marcar piezas faltantes antes de resolver
- Ver instrucciones paso a paso con colores (inicio / colocada / faltante)
- Marcar piezas faltantes desde los resultados y recalcular

**Pestaña Create Puzzle**
- Crear piezas con etiquetas identificables (e.g. `1 - Cabeza`)
- Agregar conectores por pieza (tab o hueco) con etiqueta de cinta
- Enlazar conectores entre piezas
- Guardar directamente en Neo4j
