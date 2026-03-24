# Changelog

Todos los cambios notables de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [Sin publicar]

### Añadido
- Los stands con la misma puntuación ahora se muestran en orden aleatorio.

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
