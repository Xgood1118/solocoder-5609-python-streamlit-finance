import pandas as pd
from typing import List, Dict, Optional, Tuple


def parse_date_column(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    return df


def add_time_periods(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    df = parse_date_column(df, date_col)
    df = df.copy()
    df['year'] = df[date_col].dt.year
    df['quarter'] = df[date_col].dt.to_period('Q').astype(str)
    df['month'] = df[date_col].dt.to_period('M').astype(str)
    df['week'] = df[date_col].dt.to_period('W').astype(str)
    df['day'] = df[date_col].dt.date.astype(str)
    df['year_month'] = df[date_col].dt.strftime('%Y-%m')
    return df


def filter_by_date(df: pd.DataFrame, date_col: str,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
    df = parse_date_column(df, date_col)
    if start_date:
        df = df[df[date_col] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df[date_col] <= pd.to_datetime(end_date)]
    return df


def filter_by_categories(df: pd.DataFrame, filters: Dict[str, List[str]]) -> pd.DataFrame:
    df = df.copy()
    for col, values in filters.items():
        if values and col in df.columns:
            df = df[df[col].isin(values)]
    return df


def aggregate_by_period(df: pd.DataFrame, date_col: str,
                        value_cols: List[str],
                        period: str = 'month',
                        agg_func: str = 'sum') -> pd.DataFrame:
    df = add_time_periods(df, date_col)
    period_col = period if period in ['year', 'quarter', 'month', 'week', 'day'] else 'month'
    agg_dict = {col: agg_func for col in value_cols if col in df.columns}
    grouped = df.groupby(period_col).agg(agg_dict).reset_index()
    grouped = grouped.sort_values(period_col)
    return grouped


def aggregate_by_dimension(df: pd.DataFrame,
                           dim_cols: List[str],
                           value_cols: List[str],
                           agg_func: str = 'sum') -> pd.DataFrame:
    agg_dict = {col: agg_func for col in value_cols if col in df.columns}
    dim_cols_valid = [c for c in dim_cols if c in df.columns]
    if not dim_cols_valid:
        return pd.DataFrame()
    grouped = df.groupby(dim_cols_valid).agg(agg_dict).reset_index()
    return grouped


def get_same_period_last_year(df: pd.DataFrame, date_col: str,
                              value_cols: List[str],
                              period: str = 'month') -> pd.DataFrame:
    freq_map = {'day': 'D', 'week': 'W', 'month': 'M', 'quarter': 'Q', 'year': 'Y'}
    freq = freq_map.get(period, 'M')
    agg = aggregate_by_period(df, date_col, value_cols, period)
    period_col = period
    result = agg.copy()
    result['_period_dt'] = pd.PeriodIndex(result[period_col], freq=freq).to_timestamp()
    result['_prev_year_dt'] = result['_period_dt'] - pd.DateOffset(years=1)
    result['_prev_year_period'] = result['_prev_year_dt'].dt.to_period(freq).astype(str)

    prev_data = agg.set_index(period_col)
    for col in value_cols:
        result[f'{col}_yoy'] = result['_prev_year_period'].map(prev_data[col])

    result = result.drop(columns=['_period_dt', '_prev_year_dt', '_prev_year_period'])
    return result


class DrillState:
    def __init__(self):
        self.history: List[Dict] = []
        self.current_index: int = -1

    def add_state(self, level: str, filters: Dict, title: str):
        self.history = self.history[:self.current_index + 1]
        self.history.append({'level': level, 'filters': filters, 'title': title})
        self.current_index = len(self.history) - 1

    def go_back(self) -> Optional[Dict]:
        if self.current_index > 0:
            self.current_index -= 1
            return self.history[self.current_index]
        return None

    def go_forward(self) -> Optional[Dict]:
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        return None

    def get_current(self) -> Optional[Dict]:
        if self.current_index >= 0 and self.history:
            return self.history[self.current_index]
        return None

    def get_breadcrumbs(self) -> List[str]:
        return [h['title'] for h in self.history[:self.current_index + 1]]

    def can_go_back(self) -> bool:
        return self.current_index > 0

    def can_go_forward(self) -> bool:
        return self.current_index < len(self.history) - 1

    def reset(self):
        self.history = []
        self.current_index = -1


def apply_filters(df: pd.DataFrame, date_col: Optional[str],
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None,
                  category_filters: Optional[Dict[str, List[str]]] = None,
                  drill_filters: Optional[Dict[str, List[str]]] = None) -> pd.DataFrame:
    result = df.copy()
    if date_col and (start_date or end_date):
        result = filter_by_date(result, date_col, start_date, end_date)
    if category_filters:
        result = filter_by_categories(result, category_filters)
    if drill_filters:
        result = filter_by_categories(result, drill_filters)
    return result
