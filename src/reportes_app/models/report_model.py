"""Modelo: lógica para localizar, leer y comparar reportes Excel de la carpeta X."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

# Soporta nombres como "reporte_2026-09-14.xlsx" (ISO) o "14-09-2026.xlsx" (DD-MM-YYYY,
# el formato real usado en los reportes de la empresa).
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DMY_DATE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
EXCEL_EXTENSIONS = (".xlsx", ".xls")


class ReportError(Exception):
    """Error de negocio esperado (archivo no encontrado, columna inválida, etc.)."""


@dataclass
class ReportSummary:
    filename: str
    rows: int
    columns: list[str]
    preview: list[dict]


@dataclass
class ComparisonResult:
    key_column: str
    procesado_ayer: list[dict] = field(default_factory=list)
    nuevo_hoy: list[dict] = field(default_factory=list)


def _parse_date_from_filename(name: str) -> date | None:
    """Extrae una fecha del nombre de archivo, probando ISO (YYYY-MM-DD) y DD-MM-YYYY."""
    m = ISO_DATE.search(name)
    if m:
        year, month, day = m.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass

    m = DMY_DATE.search(name)
    if m:
        day, month, year = m.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass

    return None


def _dated_excel_files(directory: Path) -> list[tuple[date, Path]]:
    if not directory.exists():
        raise ReportError(f"La carpeta '{directory}' no existe.")

    encontrados = []
    for p in directory.iterdir():
        if p.suffix.lower() not in EXCEL_EXTENSIONS:
            continue
        fecha = _parse_date_from_filename(p.name)
        if fecha is not None:
            encontrados.append((fecha, p))
    return encontrados


def find_today_and_previous(
    directory: Path, today: date
) -> tuple[Path, Path | None, date | None]:
    """Devuelve (ruta_hoy, ruta_anterior_o_None, fecha_anterior_o_None).

    ruta_hoy: archivo cuyo nombre contiene la fecha de hoy. Lanza ReportError si no existe
    o si hay más de uno.
    ruta_anterior: el archivo con fecha más reciente ANTES de hoy (no necesariamente el día
    calendario inmediato anterior, ya que los reportes no siempre se generan todos los días).
    """
    archivos = _dated_excel_files(directory)

    de_hoy = [p for fecha, p in archivos if fecha == today]
    if not de_hoy:
        raise ReportError(
            f"No se encontró ningún archivo con la fecha de hoy ({today.isoformat()}) "
            f"en '{directory.name}'."
        )
    if len(de_hoy) > 1:
        nombres = ", ".join(p.name for p in de_hoy)
        raise ReportError(
            f"Hay más de un archivo con la fecha de hoy: {nombres}. Debe existir solo uno."
        )
    ruta_hoy = de_hoy[0]

    anteriores = sorted(
        ((fecha, p) for fecha, p in archivos if fecha < today), key=lambda t: t[0]
    )
    if anteriores:
        fecha_anterior, ruta_anterior = anteriores[-1]
    else:
        fecha_anterior, ruta_anterior = None, None

    return ruta_hoy, ruta_anterior, fecha_anterior


def load_excel(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=0, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001 - queremos mostrar el error real al usuario
        raise ReportError(f"No se pudo leer '{path.name}': {exc}") from exc
    df.columns = [str(c).strip() for c in df.columns]
    return df


def summarize(path: Path, df: pd.DataFrame, preview_rows: int = 5) -> ReportSummary:
    return ReportSummary(
        filename=path.name,
        rows=len(df),
        columns=list(df.columns),
        preview=df.head(preview_rows).to_dict(orient="records"),
    )


def compare(df_hoy: pd.DataFrame, df_ayer: pd.DataFrame, key_column: str) -> ComparisonResult:
    if key_column not in df_hoy.columns:
        raise ReportError(f"La columna clave '{key_column}' no existe en el reporte de hoy.")
    if key_column not in df_ayer.columns:
        raise ReportError(f"La columna clave '{key_column}' no existe en el reporte de ayer.")

    claves_ayer = set(df_ayer[key_column].astype(str).str.strip())

    df_hoy = df_hoy.copy()
    df_hoy["_es_nuevo"] = ~df_hoy[key_column].astype(str).str.strip().isin(claves_ayer)

    nuevo_hoy = df_hoy[df_hoy["_es_nuevo"]].drop(columns="_es_nuevo").to_dict(orient="records")
    procesado_ayer = (
        df_hoy[~df_hoy["_es_nuevo"]].drop(columns="_es_nuevo").to_dict(orient="records")
    )

    return ComparisonResult(
        key_column=key_column, procesado_ayer=procesado_ayer, nuevo_hoy=nuevo_hoy
    )
