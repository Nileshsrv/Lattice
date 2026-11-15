"""CSV dataset ingest: parse, detect columns/units, flag unknowns (I-11).

Column headers may carry units as 'name_unit' (e.g. wavelength_nm) or
'name [unit]'. A column with no parseable unit is dimensionless only if the
uploader's metadata says so; otherwise the unit is recorded as unknown.
"""

import csv
import io
import re

from astropy import units as u

_HEADER_RE = re.compile(r"^(?P<name>[^\[\]]+?)[_\s]*\[?(?P<unit>[A-Za-z%/^0-9*\s-]*)\]?$")


def _parse_header(header: str) -> tuple[str, str | None]:
    header = header.strip()
    if "[" in header and "]" in header:
        name, unit = header.split("[", 1)
        return name.strip(), unit.rstrip("]").strip()
    if "_" in header:
        name, maybe_unit = header.rsplit("_", 1)
        try:
            u.Unit(maybe_unit)
            return name.strip(), maybe_unit
        except Exception:
            return header, None
    return header, None


def parse_csv(content: bytes) -> dict:
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if len(rows) < 2:
        raise ValueError("CSV must contain a header row and at least one data row")
    headers = rows[0]
    columns: list[dict] = []
    unknowns: list[str] = []
    for header in headers:
        name, unit = _parse_header(header)
        if unit is None:
            unknowns.append(f"unit of column '{name}' is not declared")
        columns.append({"name": name, "unit": unit, "header": header})
    data: dict[str, list[float]] = {col["name"]: [] for col in columns}
    n_bad = 0
    for row in rows[1:]:
        if len(row) != len(headers):
            n_bad += 1
            continue
        try:
            values = [float(cell) for cell in row]
        except ValueError:
            n_bad += 1
            continue
        for col, value in zip(columns, values):
            data[col["name"]].append(value)
    quality: list[str] = []
    if n_bad:
        quality.append(f"{n_bad} malformed row(s) were skipped (flagged, not deleted)")
    n_rows = len(next(iter(data.values()))) if data else 0
    return {
        "columns": columns,
        "data": data,
        "n_rows": n_rows,
        "unknowns": unknowns,
        "quality_flags": quality,
    }


def column_in_canonical_unit(
    parsed: dict, name: str, canonical_unit: str
) -> list[float]:
    """Convert a parsed column to a tool's canonical unit; dimensionless passes through."""
    col = next((c for c in parsed["columns"] if c["name"] == name), None)
    if col is None:
        raise ValueError(f"dataset has no column '{name}'")
    values = parsed["data"][name]
    if not canonical_unit:
        return values
    if not col["unit"]:
        raise ValueError(
            f"column '{name}' has no declared unit; cannot convert to {canonical_unit}"
        )
    factor = (1.0 * u.Unit(col["unit"])).to(u.Unit(canonical_unit)).value
    return [v * factor for v in values]
