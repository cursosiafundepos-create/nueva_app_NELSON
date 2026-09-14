# Cruce de Reportes Diarios

Aplicación Flask (patrón MVC) para leer el reporte de hoy desde una carpeta,
compararlo contra el de ayer y mostrar, paso a paso, qué información ya se
había procesado y cuál es nueva.

## Estructura (MVC)

```
src/reportes_app/
  models/report_model.py       -> lógica: buscar archivos por fecha, leer Excel, comparar
  controllers/main_controller.py -> rutas Flask: /, /api/cargar, /api/cruzar
  templates/index.html          -> vista: wizard paso a paso
  static/css/style.css
  static/js/app.js
data/reportes/                  -> carpeta "X": aquí van los reportes .xlsx
```

## Convención de archivos

Los archivos deben estar en `data/reportes/` y su **nombre debe incluir la
fecha** en formato `YYYY-MM-DD`, por ejemplo:

```
reporte_2026-09-14.xlsx   <- hoy
reporte_2026-09-13.xlsx   <- ayer
```

El prefijo (`reporte_`) puede ser el que quieras; lo único que se busca es
la fecha dentro del nombre. Debe haber **un solo archivo por fecha**.

## Cómo correr

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv run python run.py
```

Abre http://127.0.0.1:5000

## Flujo paso a paso

1. **Cargar**: busca el archivo de hoy (y el de ayer) en `data/reportes/`,
   muestra cuántas filas tiene cada uno y deja elegir la columna clave
   (ID/folio) para comparar.
2. **Cruzar**: compara ambos reportes por esa columna clave y muestra dos
   grupos: lo que ya existía ayer y lo que es nuevo hoy.

## Configurar otra carpeta

Por defecto usa `<raíz del proyecto>/data/reportes`. Para usar otra ruta:

```bash
REPORTES_DIR=/ruta/a/tu/carpeta uv run python run.py
```
