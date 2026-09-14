"""Modelo: lógica para localizar, leer y comparar reportes Excel de la carpeta X."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

DATE_IN_FILENAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
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


def _find_file_for_date(directory: Path, target: date) -> Path:
    """Busca en `directory` un Excel cuyo nombre contenga la fecha `target` (YYYY-MM-DD)."""
    target_str = target.isoformat()
    if not directory.exists():
        raise ReportError(f"La carpeta '{directory}' no existe.")

    candidatos = [
        p
        for p in directory.iterdir()
        if p.suffix.lower() in EXCEL_EXTENSIONS and target_str in p.name
    ]

    if not candidatos:
        raise ReportError(
            f"No se encontró ningún archivo con la fecha {target_str} en '{directory.name}'."
        )
    if len(candidatos) > 1:
        nombres = ", ".join(p.name for p in candidatos)
        raise ReportError(
            f"Hay más de un archivo con la fecha {target_str}: {nombres}. "
            "Debe existir solo uno por día."
        )
    return candidatos[0]


def find_today_and_yesterday(directory: Path, today: date) -> tuple[Path, Path | None]:
    """Devuelve (ruta_hoy, ruta_ayer_o_None). Lanza ReportError si no existe el de hoy."""
    from datetime import timedelta

    ruta_hoy = _find_file_for_date(directory, today)

    yesterday = today - timedelta(days=1)
    try:
        ruta_ayer = _find_file_for_date(directory, yesterday)
    except ReportError:
        ruta_ayer = None

    return ruta_hoy, ruta_ayer


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
