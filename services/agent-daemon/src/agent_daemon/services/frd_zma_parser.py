"""Parsers for FRD and ZMA text files with simple validation summaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParseIssue:
    line_number: int
    message: str


@dataclass(frozen=True)
class ParsedTableSummary:
    file_path: str
    file_type: str
    detected_columns: list[str]
    row_count: int
    frequency_min_hz: float | None
    frequency_max_hz: float | None
    value_ranges: dict[str, tuple[float, float]]
    warnings: list[str]
    errors: list[ParseIssue]


def parse_frd_file(file_path: Path) -> ParsedTableSummary:
    return _parse_measurement_file(file_path=file_path, file_type="FRD")


def parse_zma_file(file_path: Path) -> ParsedTableSummary:
    return _parse_measurement_file(file_path=file_path, file_type="ZMA")


def _parse_measurement_file(file_path: Path, file_type: str) -> ParsedTableSummary:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    warnings: list[str] = []
    errors: list[ParseIssue] = []
    numeric_rows: list[list[float]] = []
    expected_width: int | None = None

    for index, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith(("*", "#", ";", "//")):
            continue
        tokens = line.replace(",", " ").split()
        parsed = _parse_float_tokens(tokens)
        if parsed is None:
            errors.append(ParseIssue(line_number=index, message="Could not parse numeric columns from this line."))
            continue
        if expected_width is None:
            expected_width = len(parsed)
        elif len(parsed) != expected_width:
            errors.append(
                ParseIssue(
                    line_number=index,
                    message=f"Expected {expected_width} columns but found {len(parsed)} columns.",
                )
            )
            continue
        numeric_rows.append(parsed)

    if len(lines) == 0:
        warnings.append("File is empty.")

    if len(numeric_rows) == 0:
        warnings.append("No valid numeric measurement rows were found.")
        return ParsedTableSummary(
            file_path=str(file_path),
            file_type=file_type,
            detected_columns=[],
            row_count=0,
            frequency_min_hz=None,
            frequency_max_hz=None,
            value_ranges={},
            warnings=warnings,
            errors=errors,
        )

    detected_columns = _column_names_for(file_type=file_type, width=len(numeric_rows[0]))
    frequencies = [row[0] for row in numeric_rows]
    values_by_column = _collect_value_ranges(numeric_rows=numeric_rows, detected_columns=detected_columns)

    if any(freq <= 0 for freq in frequencies):
        warnings.append("Some frequency values are zero or negative.")
    if any(later < earlier for earlier, later in zip(frequencies, frequencies[1:])):
        warnings.append("Frequency values are not sorted in ascending order.")
    if len(set(frequencies)) != len(frequencies):
        warnings.append("Duplicate frequency values were detected.")

    if file_type == "ZMA" and len(detected_columns) < 3:
        warnings.append("ZMA files usually include 3 columns (frequency, impedance, phase).")
    if file_type == "FRD" and len(detected_columns) < 2:
        warnings.append("FRD files usually include at least 2 columns (frequency and magnitude).")

    return ParsedTableSummary(
        file_path=str(file_path),
        file_type=file_type,
        detected_columns=detected_columns,
        row_count=len(numeric_rows),
        frequency_min_hz=min(frequencies),
        frequency_max_hz=max(frequencies),
        value_ranges=values_by_column,
        warnings=warnings,
        errors=errors,
    )


def _parse_float_tokens(tokens: list[str]) -> list[float] | None:
    if len(tokens) < 2:
        return None
    values: list[float] = []
    for token in tokens:
        try:
            values.append(float(token))
        except ValueError:
            return None
    return values


def _column_names_for(file_type: str, width: int) -> list[str]:
    if width <= 0:
        return []
    if file_type == "FRD":
        defaults = ["frequency_hz", "magnitude_db", "phase_deg"]
    else:
        defaults = ["frequency_hz", "impedance_ohm", "phase_deg"]
    if width <= len(defaults):
        return defaults[:width]
    extra_names = [f"column_{index}" for index in range(len(defaults) + 1, width + 1)]
    return [*defaults, *extra_names]


def _collect_value_ranges(numeric_rows: list[list[float]], detected_columns: list[str]) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    for index, name in enumerate(detected_columns):
        column_values = [row[index] for row in numeric_rows if index < len(row)]
        if len(column_values) == 0:
            continue
        ranges[name] = (min(column_values), max(column_values))
    return ranges
