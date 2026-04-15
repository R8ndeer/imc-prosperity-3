from __future__ import annotations

"""Structured trader-log parsing hooks for the dashboard."""

import json
from pathlib import Path

import pandas as pd


LOG_COLUMNS = ["source_file", "day", "timestamp", "product", "group", "key", "value"]


def parse_json_log_line(line: str, *, source_file: str) -> list[dict[str, object]]:
    try:
        payload = json.loads(line)
    except Exception:
        return []

    if not isinstance(payload, dict):
        return []

    general = payload.get("GENERAL")
    timestamp = general.get("TIMESTAMP") if isinstance(general, dict) else None
    rows: list[dict[str, object]] = []

    for group, values in payload.items():
        if group == "GENERAL":
            continue
        if isinstance(values, dict):
            iterable = values.items()
        elif isinstance(values, list):
            iterable = ((str(index), value) for index, value in enumerate(values))
        else:
            iterable = [("value", values)]

        for key, value in iterable:
            rows.append(
                {
                    "source_file": source_file,
                    "day": None,
                    "timestamp": timestamp,
                    "product": group,
                    "group": group,
                    "key": key,
                    "value": json.dumps(value) if isinstance(value, (dict, list)) else value,
                }
            )

    return rows


def load_logs(log_dir: Path | None) -> pd.DataFrame:
    if log_dir is None or not Path(log_dir).exists():
        return pd.DataFrame(columns=LOG_COLUMNS)

    rows: list[dict[str, object]] = []
    for path in sorted(Path(log_dir).glob("*.log")):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                rows.extend(parse_json_log_line(line.strip(), source_file=path.name))

    if not rows:
        return pd.DataFrame(columns=LOG_COLUMNS)
    return pd.DataFrame(rows, columns=LOG_COLUMNS)
