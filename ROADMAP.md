# Roadmap GateManager

## ⚡ Quick wins
- [x] Versionado centralizado — `app/_version.py`
- [x] Undo última asignación (Ctrl+Z / botón)
- [x] Validador de datos de aeropuertos (`dev/validate_airport.py`)
- [x] `requirements-dev.txt` para herramientas de desarrollo

## 🔧 Medio
- [x] Buscador/filtro instantáneo en tabla de resultados
- [x] Sistema de scoring — columna Score + razones en detalle
- [x] Exportar / Importar sesión completa en JSON
- [x] Instalación de aeropuertos por ZIP (botón "+ Aeropuerto")
- [ ] Auto-assign con confirmación

## 🏗️ Grande
- [ ] Favoritos por aerolínea
- [ ] Reglas por franja horaria (cerrar/reservar stands)
- [ ] Arrivals vs Departures
- [ ] Sincronización bidireccional con Aurora
- [ ] Editor GUI de aeropuertos

## Extras completados
- [x] `airlines.json` opcional (aeropuertos de una sola terminal)
- [x] Selector de terminal oculto si solo hay una terminal
- [x] Spec de PyInstaller dinámico (detecta aeropuertos automáticamente)
- [x] `AirportData.available()` filtra aeropuertos incompletos
- [x] Stands con igual score en orden aleatorio
