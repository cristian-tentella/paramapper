import csv
import os
from typing import Any, TextIO

import numpy as np


class DataParser:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.headers: list[str] = []
        self.row_count: int = 0

    def validate_file(self) -> None:
        pass

    def extract_metadata(self) -> dict[str, dict[str, Any]]:
        pass

    def create_sanitized_copy(self, columns_meta, output_path: str) -> str:
        pass


class CSVParser(DataParser):
    def validate_file(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        if not self.filepath.lower().endswith(".csv"):
            raise ValueError(f"Invalid format, expected .csv, received {self.filepath}")

    def extract_metadata(self) -> dict[str, dict[str, Any]]:
        with open(self.filepath, mode="r", encoding="utf-8") as f:
            dialect = self._sniff_dialect(f)
            reader = csv.reader(f, dialect)

            raw_headers = next(reader, [])
            self.headers = [h.strip() for h in raw_headers if h.strip()]

            if not self.headers:
                raise ValueError("CSV file is empty or void of headers")

            rows = [row for row in reader if row and any(cell.strip() for cell in row)]
            self.row_count = len(rows)

        matrix = np.array(rows, dtype=str)
        metadata: dict[str, dict[str, Any]] = {}

        for col_idx, header in enumerate(self.headers):
            if col_idx >= matrix.shape[1]:
                continue

            col_data = np.char.strip(matrix[:, col_idx])
            col_data = col_data[col_data != ""]

            if col_data.size == 0:
                continue

            try:
                numeric_values = col_data.astype(float)
                metadata[header] = {
                    "type": "NUMERIC",
                    "min": float(np.min(numeric_values)),
                    "max": float(np.max(numeric_values)),
                    "tokens": None,
                }
            except ValueError:
                try:
                    date_values = col_data.astype("datetime64")
                    timestamps = date_values.astype("datetime64[s]").astype(float)

                    metadata[header] = {
                        "type": "DATETIME",
                        "min": float(np.min(timestamps)),
                        "max": float(np.max(timestamps)),
                        "tokens": None,
                    }
                except ValueError:
                    unique_tokens = np.unique(col_data)
                    metadata[header] = {
                        "type": "CATEGORICAL",
                        "min": None,
                        "max": None,
                        "tokens": "\n".join(unique_tokens),
                    }

        return metadata

    def create_sanitized_copy(self, columns_meta, output_path: str) -> str:
        token_maps = {}
        datetime_cols = set()

        for col in columns_meta:
            if col.data_type == "CATEGORICAL" and col.unique_tokens:
                tokens = col.unique_tokens.split("\n")
                token_maps[col.name] = {t: str(idx) for idx, t in enumerate(tokens)}
            elif col.data_type == "DATETIME":
                datetime_cols.add(col.name)

        with (
            open(self.filepath, mode="r", encoding="utf-8") as f_in,
            open(output_path, mode="w", newline="", encoding="utf-8") as f_out,
        ):
            dialect = self._sniff_dialect(f_in)
            reader = csv.reader(f_in, dialect)
            writer = csv.writer(f_out)

            headers = next(reader, [])
            writer.writerow(headers)

            col_actions = {}
            for idx, h in enumerate(headers):
                h_clean = h.strip()
                if h_clean in token_maps:
                    col_actions[idx] = ("CATEGORICAL", token_maps[h_clean])
                elif h_clean in datetime_cols:
                    col_actions[idx] = ("DATETIME", None)

            for row in reader:
                if not row:
                    continue

                for idx, action_info in col_actions.items():
                    if idx < len(row):
                        action_type, mapping = action_info
                        cell = row[idx].strip()

                        if action_type == "CATEGORICAL":
                            row[idx] = mapping.get(cell, "0")
                        elif action_type == "DATETIME":
                            try:
                                ts = np.datetime64(cell).astype("datetime64[s]").astype(float)
                                row[idx] = str(ts)
                            except ValueError:
                                row[idx] = "0.0"

                writer.writerow(row)

        return output_path

    def _sniff_dialect(self, file_stream: TextIO) -> csv.Dialect:
        try:
            sample = file_stream.read(2048)
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        finally:
            file_stream.seek(0)
        return dialect


class JSONParser(DataParser):
    pass


def get_parser(filepath: str) -> DataParser:
    file_extension = filepath.split(".")[-1].lower()

    match file_extension:
        case "csv":
            return CSVParser(filepath)
        case "json":
            return JSONParser(filepath)
        case _:
            raise ValueError(f"Files with .{file_extension} extension are not supported")
