# LEBL Parking Assignment System
Sistema de asignación de parkings para el aeropuerto de Barcelona El Prat (LEBL) en IVAO Virtual ATC.

---

## Descarga e instalación

> **[Descargar última versión → Releases](../../releases/latest)**

1. Ve a la sección **Releases** y descarga `LEBL Parking.exe`.
2. Ponlo donde quieras y ábrelo directamente.

> La **primera vez** que se abre tarda ~20 segundos extrayendo los datos internos (aparece una pantalla de carga). Las siguientes aperturas son inmediatas.

> Si Windows muestra una advertencia de SmartScreen, haz clic en **"Más información" → "Ejecutar de todas formas"**. El ejecutable no está firmado digitalmente.

### Desde fuente (Python 3.8+, sin instalador)
```
python parking_gui.py        # GUI
python parking_finder.py     # CLI
```
Sin dependencias externas — solo librería estándar de Python.

---

## Interfaz gráfica (GUI)

<!-- SCREENSHOT: vista general de la aplicación -->
![Ventana principal](assets/screenshots/main_window.png)

La GUI permite asignar stands, consultar información, sincronizar con Aurora y gestionar todos los stands asignados en una sesión.

### Panel izquierdo — Query y ocupados

<!-- SCREENSHOT: panel izquierdo con campos de query y filtros -->
![Panel izquierdo](assets/screenshots/left_panel.png)

- **Query** — introduce 1, 2 o 3 campos (Callsign, Airline, Aircraft, Origin). Con solo Aircraft busca por envergadura; con Airline calcula terminal y dedicados automáticamente.
- **Detección GA automática** — al escribir un callsign, la herramienta detecta si es una matrícula privada (EC-LBS, G-ABCD, N12345…) y activa el modo GA automáticamente, buscando en los stands de aviación general (01-57). El botón `GA` junto al campo Callsign muestra el país de matrícula detectado y permite forzarlo manualmente.
- **Filtros** — Tipo (Todo / Gates / Remote), Schengen (Auto / SCH / No-SCH), Terminal (Auto / T1 / T2). Se combinan con la query.
- **Current Strip** — tarjeta de vuelo con callsign, avión, terminal, zona Schengen y stand asignado.
- **Stands ocupados** — lista de todos los stands bloqueados en la sesión actual.
  - `⟳ Sync Aurora` — importa los stands ocupados en tiempo real desde Aurora.
  - `▦ Ver ocupados` — abre el panel de ocupados con callsign y avión por stand.
  - `x Liberar stand…` — libera un stand manualmente.

### Panel derecho — Tabla de stands y detalles

<!-- SCREENSHOT: tabla de stands disponibles -->
![Panel derecho](assets/screenshots/right_panel.png)

- **Tabla de stands disponibles** — columnas Stand, Max WS, Tipo, Zona, Max Acft, Excluye. Colores:
  - 🟣 Morado — envergadura exacta (★ perfecto)
  - 🟢 Verde — gate disponible
  - 🟠 Naranja — remoto
  - 🟡 Amarillo — fallback (otro terminal)
- **Info stand** — búsqueda directa por ID con todos los datos del stand + checks de compatibilidad (envergadura, Schengen, terminal, dedicados).
- **Botón Assign Stand ↵** — asigna el stand seleccionado. También con doble clic o `Enter`.

### Paneles flotantes

<!-- SCREENSHOT: panel de asignaciones -->
![Panel derecho](assets/screenshots/asignaciones.png)

#### ASIGNACIONES ▤
Historial de todos los stands asignados y pre-asignados en la sesión:
- Hora, Callsign, Aerolínea, Avión, Origen, Stand, Estado
- Estados: `ASIGNADO`, `PRE-ASIGNADO`, `ASIGNADO (auto)`, `REEMPLAZADO`
- Exportar a CSV

#### ▦ Ver ocupados

<!-- SCREENSHOT: panel de ocupados -->
![Panel derecho](assets/screenshots/ocupados.png)

Lista completa de stands bloqueados con el callsign y avión que los ocupa. Distingue entre stands asignados manualmente (naranja) y stands sin info conocida (gris, p.ej. bloqueados por exclusión).

---

## Integración con Aurora (IVAO)

<!-- SCREENSHOT: indicador de conexión Aurora en header -->
![Panel derecho](assets/screenshots/aurora_connected.png)

La GUI se conecta automáticamente a Aurora (localhost:1130) al arrancar.

| Función | Descripción |
|---------|-------------|
| **Auto-refresh** | Checkbox en la cabecera. Detecta cambios en el tráfico seleccionado en Aurora y lanza la query automáticamente cada ~4s. |
| **QUERY SELECTED (F5)** | Consulta el tráfico actualmente seleccionado en Aurora y rellena los campos. |
| **Asignación automática** | Al asignar un stand, envía `#LBGTE` a Aurora para etiquetar el gate en el strip del piloto. |
| **Pre-asignación** | Si el tráfico no está asumido, guarda el stand y lo envía a Aurora automáticamente cuando se asume. |
| **Sync Aurora** | Importa todos los gates ocupados actualmente en Aurora al conjunto de stands bloqueados. |

---

## Re-asignación

Si asignas un nuevo stand a un callsign que ya tiene uno asignado:
1. El stand anterior se libera (y sus exclusiones).
2. El registro anterior queda marcado como `REEMPLAZADO`.
3. Se asigna el nuevo stand y se envía a Aurora.

---

## Stands especiales

| Rango | Uso |
|-------|-----|
| 01–57 | GA — aviación general (excluidos de resultados normales) |
| 71–87 | Mantenimiento — excluidos de resultados normales. Asignables manualmente via "Info stand". |
| 91–96 | EJU/EZY/EZS dedicados (T2) |
| 141–165 | Cargo |
| 200, 202, 200R | IBE dedicados (T1) |
| 260–268 | ANY dedicados (T1 Schengen) — ANY va aquí preferentemente; otras aerolíneas también pueden usarlos |
| 900–999 | Uso especial — excluidos de resultados por defecto |

---

## CLI (modo consola)

El CLI original `parking_finder.py` sigue disponible para uso sin interfaz gráfica.

```
python parking_finder.py
```

### Sintaxis de consulta

```
AEROLINEA AERONAVE ORIGEN [modificadores]
```

| Modificador | Efecto |
|-------------|--------|
| `r` | Solo stands remotos |
| `s` | Forzar Schengen |
| `ns` | Forzar Non-Schengen |
| `g` | Modo GA |
| `c` | Modo Cargo |

| Comando | Efecto |
|---------|--------|
| `a [CALLSIGN]` | Query desde Aurora (tráfico seleccionado o callsign indicado) |
| `o 242 243` | Marcar stands como ocupados |
| `x 242` | Liberar stand |
| `clear` | Liberar todos los stands |
| `q` | Salir |

---

## Detección Schengen automática

Por prefijo ICAO del aeropuerto de origen:
- **Schengen**: `BI EB ED ET EE EF EH EK EL EN EP ES EV EY LD LE GC GE LF LG LH LI LJ LK LM LO LP LS LZ LX`
- **Resto**: se asume Non-Schengen.

---

## Añadir contenido

### Nueva aerolínea
```json
// data/airlines.json
"XYZ": "T1"   // o "T2" o "CARGO"
```

### Nueva aerolínea con stands dedicados
```python
# parking_finder.py
DEDICATED['XYZ']          = {'101', '102', '103'}
DEDICATED_LABEL['XYZ']    = 'XYZ DEDICATED'
DEDICATED_TERMINAL['XYZ'] = 'T1'
```

### Nueva aeronave
```json
// data/aircraft_wingspans.json
"B39M": 35.9
```

---

## Carpeta dev (solo desarrolladores)

Scripts para regenerar las bases de datos desde los PDFs oficiales de LEBL:

```
python dev/build_aircraft_db.py          # regenera aircraft_wingspans.json
python dev/build_parking_db.py           # regenera parkings.json
python dev/scrape_incompatibilities.py   # inyecta excludes desde el PDF
```

> ⚠️ `build_parking_db.py` sobreescribe `parkings.json` y pierde las modificaciones manuales.

---

## Archivos

```
LEBL Parking.exe            ← ejecutable único (distribución)

LEBL Parking.pyw            ← lanzador directo con Python instalado
iniciar_gui.bat             ← lanzador .bat
parking_gui.py              ← GUI principal
parking_finder.py           ← motor de búsqueda + CLI
aurora_bridge.py            ← conexión TCP con Aurora
callsign_analyzer.py        ← detector de matrículas privadas / GA
data/
  airlines.json
  aircraft_wingspans.json
  parkings.json
  prefix_data.json          ← base de datos de prefijos de matrícula (180+ países)
MANUAL.txt                  ← documentación completa de uso
```
