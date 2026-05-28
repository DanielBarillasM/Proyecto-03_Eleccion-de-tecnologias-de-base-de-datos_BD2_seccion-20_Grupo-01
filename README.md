# PuzzleGraph Solver

Aplicación académica para resolver rompecabezas modelados como grafos usando **Python**, **Neo4j** y **NiceGUI**.

> El sistema modela cada rompecabezas como un grafo: cada pieza es un nodo y cada posible ensamble entre piezas es una relación. Gracias a este enfoque, el algoritmo puede iniciar desde cualquier pieza, recorrer las conexiones del rompecabezas y generar una secuencia de armado. Si una pieza está marcada como faltante, el sistema no detiene la solución, sino que genera un armado parcial y reporta los huecos pendientes.

## Qué problema resuelve

El proyecto permite registrar un rompecabezas como un conjunto de piezas conectadas. A partir de una pieza inicial cualquiera, el algoritmo genera instrucciones humanas de armado, por ejemplo: colocar una pieza arriba, abajo, a la izquierda, a la derecha, en diagonal, cerca de otra, o como parte de un subensamble.

El usuario puede marcar piezas faltantes. En ese caso, la solución no se detiene: el sistema reporta el hueco, continúa con las piezas disponibles y muestra si el resultado final es **completo** o **parcial**.

## Tecnologías

- **Python**: lógica del programa, modelos y algoritmo BFS.
- **NiceGUI**: interfaz gráfica web local, moderna y presentable para demo.
- **Neo4j**: base de datos de grafos para representar piezas como nodos y conexiones como relaciones.
- **Cypher**: consultas sobre nodos `Puzzle`, `Piece`, `Component` y relaciones `CONNECTS_TO`.
- **JSON local**: modo fallback para ejecutar la demo sin conexión a Neo4j.

## Rompecabezas incluidos

| ID | Tipo | Piezas | Descripción |
|---|---:|---:|---|
| `plesiosaurus` | Secuencial/irregular | 10 | Dinosaurio marino numerado. |
| `aviones` | Cuadrícula | 20 | Rompecabezas rectangular 4x5 de aviones. |
| `animalitos` | Cuadrícula | 16 | Escena rectangular de animales del bosque. |
| `peces` | Irregular | 7 | Piezas orgánicas de peces/delfines. |
| `tres_animales` | Multi-componente | 13 | Tres figuras independientes dentro del mismo tablero. |
| `excavadora` | Irregular/semántico | 10 | Vehículo con pala, brazo, cabina y base. |

El algoritmo es genérico: puede resolver cualquier rompecabezas cuyas piezas y relaciones estén registradas en JSON o Neo4j.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar en modo JSON local

```bash
copy .env.example .env
python main.py
```

Luego abrir:

```text
http://127.0.0.1:8080
```

El modo JSON no necesita Neo4j y es el modo recomendado para probar la interfaz rápidamente.

## Ejecutar con Neo4j

1. Configurar `.env`:

```env
DATA_MODE=neo4j
NEO4J_URI=neo4j+s://TU_INSTANCIA.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password
NEO4J_DATABASE=neo4j
```

2. Cargar datos:

```bash
python scripts/seed_neo4j.py
```

3. Ejecutar:

```bash
python main.py
```

Desde la GUI también puedes presionar **Probar Neo4j** para verificar la conexión.

## Probar el solver sin abrir GUI

```bash
python scripts/validate_data.py
python scripts/test_solver.py
```

`validate_data.py` verifica que no haya relaciones rotas ni piezas aisladas. `test_solver.py` valida casos completos y parciales con piezas faltantes.

## Qué permite la GUI

- Seleccionar rompecabezas.
- Cambiar entre JSON local y Neo4j.
- Seleccionar pieza inicial.
- Marcar piezas faltantes.
- Ejecutar el algoritmo.
- Ver pasos de armado como tarjetas.
- Ver un resumen de solución completa/parcial.
- Copiar una versión textual de la solución para el informe.
- Copiar una versión JSON técnica de la solución.
- Ver grafo visual aproximado.
- Consultar tabla de piezas y relaciones.
- Revisar explicación del modelo y consultas Cypher principales.

## Estructura

```text
app/domain           Modelos de dominio
app/infrastructure   Repositorios JSON y Neo4j
app/services         Solver BFS, formateador de solución y utilidades
app/ui               Interfaz NiceGUI
assets               Imágenes de los rompecabezas
data                 JSON con rompecabezas default
cypher               Schema y semilla mínima
docs                 Documentación del modelo, algoritmo y demo
scripts              Scripts de carga, validación y pruebas
```

## Correcciones y mejoras de esta versión

- Corrección del repositorio Neo4j al leer piezas desde la base de datos.
- La GUI evita marcar como faltante la pieza inicial.
- Al seleccionar una pieza inicial, se limpia automáticamente de la lista de faltantes.
- En modo Neo4j, las piezas faltantes seleccionadas se persisten antes de resolver.
- Se agregó un resumen visual de solución completa/parcial.
- Se agregó exportación textual/JSON dentro de la interfaz para copiar evidencias.
- Se agregó leyenda de colores para la vista de grafo.
- Se agregó `scripts/validate_data.py` para validar integridad del dataset.
- Se ampliaron pruebas de rompecabezas completos y parciales.

## Alcance

El sistema no hace visión por computadora automática. Resuelve cualquier rompecabezas siempre que esté registrado previamente como grafo de piezas y relaciones. Esto mantiene la solución sencilla, defendible y alineada con el objetivo de elegir una tecnología de base de datos adecuada.

## Troubleshooting

Si NiceGUI muestra un error sobre `ui.add_head_html` y `ui.page`, verifica que en `app/ui/app.py` el CSS se agregue con `shared=True`.

Si Neo4j no conecta, cambia `DATA_MODE=json` en `.env` para hacer la demo local sin depender de internet o de AuraDB.

Si el puerto está ocupado, cambia:

```env
APP_PORT=8081
```
