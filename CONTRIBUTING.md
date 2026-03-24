# Contribuir a GateManager

## Levantar el proyecto

**Requisitos:** Python 3.10+, Tkinter (incluido en Python estándar).

```bash
git clone https://github.com/Concara3443/gatemanager.git
cd gatemanager
python "LEBL Parking.pyw"
```

No hay dependencias externas en tiempo de ejecución.

## Instalar herramientas de desarrollo

```bash
pip install -r requirements-dev.txt
```

Esto instala `pytest`, `pytest-cov` y `ruff` (linter + formatter).

## Correr tests

```bash
pytest
```

Con cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

## Lint y formato

```bash
ruff check .          # linter
ruff format .         # formatter
ruff check --fix .    # auto-fix
```

## Hooks pre-commit (opcional)

```bash
pip install pre-commit
pre-commit install
```

A partir de ahí, `ruff` se ejecuta automáticamente antes de cada commit.

## Compilar el ejecutable

Requiere `pip install pyinstaller`:

```bash
compilar.bat
```

Genera `dist/GateManager.exe`.

## Añadir un nuevo aeropuerto

Ver [docs/ADDING_AN_AIRPORT.md](docs/ADDING_AN_AIRPORT.md) — solo requiere crear tres archivos JSON.

## Estilo de commits

Formato: `<tipo>: <descripción corta en español o inglés>`

| Tipo       | Cuándo usarlo                          |
|------------|----------------------------------------|
| `feat`     | Nueva funcionalidad                    |
| `fix`      | Corrección de bug                      |
| `refactor` | Cambio de código sin alterar behavior  |
| `docs`     | Solo documentación                     |
| `data`     | Cambios en archivos JSON de aeropuertos|
| `chore`    | Tareas de mantenimiento (CI, deps…)    |

Ejemplos:
```
feat: añadir soporte para aeropuerto LEMD
fix: corregir filtrado de stands dedicados con múltiples terminales
data: actualizar envergaduras LEPA T-B
```

## Pull Requests

- Abre una PR contra `main`.
- Describe qué cambia y por qué.
- Si afecta a la UI, incluye una captura de pantalla.
- Los checks de CI deben pasar (lint + tests).
