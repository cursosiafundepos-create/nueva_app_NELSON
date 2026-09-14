"""Controlador: expone las rutas / (vista) y /api/cargar, /api/cruzar (pasos del flujo)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from reportes_app.models import report_model as model

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    return render_template("index.html", data_dir=str(current_app.config["DATA_DIR"]))


def _cargar_desde_carpeta(data_dir: Path, hoy: date):
    """Lógica común de carga: localiza hoy/anterior, los lee y arma la respuesta JSON."""
    ruta_hoy, ruta_ayer, fecha_ayer = model.find_today_and_previous(data_dir, hoy)
    df_hoy = model.load_excel(ruta_hoy)

    resumen_hoy = model.summarize(ruta_hoy, df_hoy)
    session["ruta_hoy"] = str(ruta_hoy)

    resumen_ayer = None
    warning = None
    if ruta_ayer is not None:
        try:
            df_ayer = model.load_excel(ruta_ayer)
            resumen_ayer = model.summarize(ruta_ayer, df_ayer)
            session["ruta_ayer"] = str(ruta_ayer)
            dias_atras = (hoy - fecha_ayer).days
            if dias_atras != 1:
                warning = (
                    f"Nota: el reporte anterior disponible es del {fecha_ayer.isoformat()} "
                    f"(hace {dias_atras} días), no de ayer exactamente. Se usará ese de todas "
                    "formas por ser el más reciente antes de hoy."
                )
        except model.ReportError as exc:
            warning = str(exc)
            session.pop("ruta_ayer", None)
    else:
        warning = (
            f"No se encontró ningún archivo anterior a hoy ({hoy.isoformat()}) para comparar."
        )
        session.pop("ruta_ayer", None)

    return jsonify(
        ok=True,
        fecha_hoy=hoy.isoformat(),
        hoy=resumen_hoy.__dict__,
        ayer=resumen_ayer.__dict__ if resumen_ayer else None,
        columnas=resumen_hoy.columns,
        warning=warning,
    )


@main_bp.post("/api/cargar")
def cargar():
    data_dir: Path = current_app.config["DATA_DIR"]
    hoy = date.today()

    try:
        return _cargar_desde_carpeta(data_dir, hoy)
    except model.ReportError as exc:
        necesita_subida = "más de un archivo" not in str(exc)
        return jsonify(ok=False, error=str(exc), necesita_subida=necesita_subida), 400


@main_bp.post("/api/subir")
def subir():
    data_dir: Path = current_app.config["DATA_DIR"]
    hoy = date.today()

    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename:
        return jsonify(ok=False, error="Selecciona un archivo Excel para subir."), 400

    try:
        model.save_uploaded_file(data_dir, archivo.filename, archivo.read(), hoy)
        return _cargar_desde_carpeta(data_dir, hoy)
    except model.ReportError as exc:
        return jsonify(ok=False, error=str(exc)), 400


@main_bp.post("/api/cruzar")
def cruzar():
    ruta_hoy = session.get("ruta_hoy")
    ruta_ayer = session.get("ruta_ayer")

    if not ruta_hoy or not ruta_ayer:
        return jsonify(
            ok=False,
            error="Primero completa el Paso 1 (Cargar) con un archivo de hoy y uno de ayer.",
        ), 400

    payload = request.get_json(silent=True) or {}
    key_column = (payload.get("key_column") or "").strip()
    if not key_column:
        return jsonify(ok=False, error="Selecciona la columna clave antes de cruzar."), 400

    try:
        df_hoy = model.load_excel(Path(ruta_hoy))
        df_ayer = model.load_excel(Path(ruta_ayer))
        resultado = model.compare(df_hoy, df_ayer, key_column)
    except model.ReportError as exc:
        return jsonify(ok=False, error=str(exc)), 400

    return jsonify(
        ok=True,
        key_column=resultado.key_column,
        total_procesado_ayer=len(resultado.procesado_ayer),
        total_nuevo_hoy=len(resultado.nuevo_hoy),
        procesado_ayer=resultado.procesado_ayer,
        nuevo_hoy=resultado.nuevo_hoy,
    )
