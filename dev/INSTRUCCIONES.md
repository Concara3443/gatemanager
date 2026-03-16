# ✈️ Guía de Uso: PDF to JSON (Parking Extractor)

Esta herramienta permite extraer automáticamente los stands de parking desde un PDF (PDC de ENAIRE) y configurar masivamente sus propiedades (Terminal, Zona Schengen, Remoto) mediante un sistema de menús y rangos inteligentes.

## 🛠️ Requisitos
Asegúrate de tener instalada la librería `pdfplumber`:
```bash
pip install pdfplumber
```

## 🚀 Ejecución
1. Abre una terminal en la carpeta `dev/`.
2. Ejecuta el script pasando la ruta del PDF:
```bash
python pdf_to_json.py <ruta_del_pdf>
```
*Ejemplo:* `python pdf_to_json.py LE_AD_2_LEAL_PDC_1_en.pdf`

---

## 🎮 Sistema de Menús e Interactividad
Al ejecutar el script, entrarás en un **Panel de Control** interactivo:

### 1. Configuración por Rangos
Puedes asignar valores a múltiples stands a la vez usando:
- **Comas:** `1, 5, 12`
- **Guiones (Rangos):** `1-10, 20-30`
- **Rangos Alfanuméricos:** El script es inteligente. Si pones `100-101b`, incluirá automáticamente el `101a` si existe en el PDF.

### 2. Secciones Navegables
- **Terminales:** Crea tantas como necesites (T1, T2, Cargo...).
- **Zonas Schengen:** Menú rápido para seleccionar `schengen_only`, `non_schengen_only`, `mixed` o `ga`.
- **Remotos:** Marca stands como remotos (`s`) o de contacto (`n`).

### 3. Utilidades de Control
- **Ver Pendientes:** Te muestra una lista detallada de qué stands aún no tienen asignada una terminal, zona o estado remoto.
- **Resumen:** Muestra una tabla con todas las asignaciones realizadas para revisar antes de guardar.
- **Sobrescribir:** Si te equivocas, vuelve a asignar el rango al valor correcto y se actualizará automáticamente.

---

## 🤖 Automatizaciones Inteligentes
El script realiza varias tareas por ti sin necesidad de entrada manual:
- **`max_acft`:** Busca en la base de datos `data/aircraft_wingspans.json` y selecciona automáticamente la aeronave de **mayor envergadura** de las permitidas en ese stand.
- **`excludes` (Incompatibilidades):** Escanea la columna de observaciones del PDF y extrae automáticamente los stands incompatibles (ej: "INCOMP. E1" -> `["E1"]`).

## 📁 Resultado
El archivo `.json` final se generará **en la misma carpeta que el script** (`dev/`), facilitando su localización.

---
*Desarrollado para GateManager v3.0*
