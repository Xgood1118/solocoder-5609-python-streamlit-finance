import pandas as pd
import io
from typing import Dict, List, Optional, Tuple


def read_file(file_bytes: bytes, filename: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    filename_lower = filename.lower()
    if filename_lower.endswith('.csv'):
        return pd.read_csv(io.BytesIO(file_bytes))
    elif filename_lower.endswith(('.xlsx', '.xls')):
        return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name or 0)
    else:
        raise ValueError(f"Unsupported file format: {filename}")


def apply_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    reverse_map = {}
    for orig_col, biz_col in mapping.items():
        if biz_col and orig_col in df.columns:
            reverse_map[orig_col] = biz_col
    df_mapped = df.rename(columns=reverse_map)
    return df_mapped


def detect_column_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return 'numeric'
    try:
        pd.to_datetime(series.head(10))
        return 'date'
    except (ValueError, TypeError):
        return 'category'


def join_tables(tables: Dict[str, pd.DataFrame],
                join_keys: Dict[str, str],
                join_type: str = 'left') -> pd.DataFrame:
    if not tables:
        return pd.DataFrame()
    if len(tables) == 1:
        return list(tables.values())[0]

    table_names = list(tables.keys())
    result = tables[table_names[0]].copy()

    for name in table_names[1:]:
        left_key = join_keys.get(name + '_left', '')
        right_key = join_keys.get(name + '_right', '')
        if left_key and right_key and left_key in result.columns and right_key in tables[name].columns:
            right_df = tables[name].copy()
            if right_key != left_key and left_key in right_df.columns:
                right_df = right_df.drop(columns=[left_key])
            result = result.merge(
                right_df,
                left_on=left_key,
                right_on=right_key,
                how=join_type,
                suffixes=('', f'_{name}')
            )
        else:
            continue

    return result


class DataSource:
    def __init__(self):
        self.tables: Dict[str, pd.DataFrame] = {}
        self.column_mappings: Dict[str, Dict[str, str]] = {}
        self.joined_data: Optional[pd.DataFrame] = None

    def add_table(self, name: str, file_bytes: bytes, filename: str,
                  column_mapping: Optional[Dict[str, str]] = None,
                  sheet_name: Optional[str] = None):
        df = read_file(file_bytes, filename, sheet_name)
        self.tables[name] = df
        if column_mapping:
            self.column_mappings[name] = column_mapping
        else:
            self.column_mappings[name] = {col: col for col in df.columns}

    def get_mapped_table(self, name: str) -> pd.DataFrame:
        if name not in self.tables:
            raise ValueError(f"Table {name} not found")
        return apply_column_mapping(self.tables[name], self.column_mappings.get(name, {}))

    def get_available_columns(self, name: str) -> List[str]:
        if name not in self.tables:
            return []
        return list(self.tables[name].columns)

    def get_business_columns(self, name: str) -> List[str]:
        mapped = self.get_mapped_table(name)
        return list(mapped.columns)

    def build_joined_data(self, join_keys: Dict[str, str], join_type: str = 'left') -> pd.DataFrame:
        mapped_tables = {}
        for name in self.tables:
            mapped_tables[name] = self.get_mapped_table(name)
        self.joined_data = join_tables(mapped_tables, join_keys, join_type)
        return self.joined_data

    def update_column_mapping(self, table_name: str, mapping: Dict[str, str]):
        if table_name not in self.tables:
            raise ValueError(f"Table {table_name} not found")
        self.column_mappings[table_name] = mapping
