# Callsign Analyzer

Este módulo permite identificar si un callsign de aviación corresponde a una matrícula (avión privado/aviación general) o a un vuelo comercial (aerolínea).

## Estructura
- `prefix_data.json`: Base de datos de prefijos y patrones extraída de `regs.csv`.
- `parse_regs.py`: Script para regenerar la base de datos desde el CSV.
- `checker.py`: Lógica principal de análisis y CLI.

## Uso

### Desde la línea de comandos
Puedes pasar uno o varios callsigns como argumentos:
```bash
python callsign_analyzer/checker.py ECLBS IBE123 N12345
```

### Desde Python
```python
from callsign_analyzer.checker import CallsignAnalyzer

analyzer = CallsignAnalyzer()
resultado = analyzer.check("ECLBS")

if resultado['is_private']:
    print(f"Es una matrícula de: {', '.join(resultado['countries'])}")
else:
    print("Es un vuelo comercial o desconocido")
```

## Características
- Elimina guiones automáticamente (soporta `EC-LBS` y `ECLBS`).
- Identifica el país basándose en prefijos internacionales.
- Valida patrones de longitud y tipo de caracteres (letras/números).
- Filtra aerolíneas comunes mediante códigos ICAO (IBE, VLG, RYR, etc.).
