# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [Sin publicar]

### Añadido
- Los stands con la misma puntuación ahora se muestran en orden aleatorio.
- **Sistema de scoring** (0–105): columna Score en la tabla, razones detalladas al seleccionar un stand.
- **Filtro instantáneo** en la tabla de resultados con contador de coincidencias.
- **Undo** de la última asignación (Ctrl+Z y botón).
- **Exportar / Importar sesión** completa en JSON.
- **Instalación de aeropuertos por ZIP** desde la barra inferior (botón "+ Aeropuerto").
- **Auto-assign con confirmación**: propuesta automática al detectar tráfico en Aurora.
- **Favoritos por aerolínea**: click derecho en la tabla para marcar stands favoritos; se guardan por aeropuerto.
- **Sincronización bidireccional con Aurora**: sync automático de gates ocupados cada 30 s; los gates liberados en Aurora se liberan también en GateManager automáticamente.
- `app/_version.py` para versionado centralizado.
- `dev/validate_airport.py`: validador de datos JSON de aeropuertos.
- `requirements-dev.txt` con herramientas de desarrollo.
- CI en GitHub Actions (lint + tests + cobertura).
- Workflow de release automático que compila `GateManager.exe` con PyInstaller.

### Cambiado
- `airlines.json` es ahora opcional (aeropuertos de una sola terminal funcionan sin él).
- El selector de terminal se oculta automáticamente si el aeropuerto solo tiene una terminal.
- El spec de PyInstaller detecta aeropuertos automáticamente (sin hardcodear LEBL/LEPA).
- `AirportData.available()` filtra aeropuertos que no tienen `config.json` y `parkings.json`.

---

## [v3.0.2] — 2025

### Cambiado
- La ventana principal tiene un tamaño mínimo mayor para evitar que los paneles queden cortados.
- El ejecutable compilado pasa a llamarse `GateManager.exe` (antes `LEBL Parking.exe`).
- Todas las referencias internas de "Stand Manager" actualizadas a "Gate Manager".
- Las referencias de versión pasan de `v3.0` a `v3` en el README y en la interfaz.

---

## [v3.0] — 2025

### Añadido
- Soporte **multi-aeropuerto**: selector de aeropuerto al arrancar cuando hay más de uno disponible.
- Aeropuerto **LEPA** (Palma de Mallorca) incluido junto a LEBL.
- Modo automático con **Aurora** (IVAO): polling cada 4 s, auto-relleno de formulario y auto-consulta.
- Envío del gate asignado de vuelta a Aurora.
- Diálogo de **stands ocupados** con lista en tiempo real.
- Exportación del historial de asignaciones a **CSV**.
- Splash screen al arrancar el ejecutable.

### Cambiado
- Interfaz completamente rediseñada (tema oscuro, paneles izquierdo/derecho).
- La lógica de filtrado se extrajo a `parking_finder.py` (separado de la GUI).

### Eliminado
- Interfaz de línea de comandos (CLI) — ahora solo GUI.
