import pandas as pd
import math
from typing import Dict, Optional, List, Tuple


def format_number(value: float, unit: str = 'auto', decimals: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return '-'
    abs_val = abs(value)

    if unit == 'auto':
        if abs_val >= 100000000:
            unit = '亿'
            scaled = value / 100000000
        elif abs_val >= 10000:
            unit = '万'
            scaled = value / 10000
        else:
            unit = ''
            scaled = value
    elif unit == '亿':
        scaled = value / 100000000
    elif unit == '万':
        scaled = value / 10000
    else:
        scaled = value

    formatted = f"{scaled:,.{decimals}f}"
    if unit:
        formatted += unit
    return formatted


def format_percent(value: float, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return '-'
    return f"{value * 100:.{decimals}f}%"


def get_trend_direction(current: float, previous: float) -> Tuple[str, str]:
    if previous is None or previous == 0 or math.isnan(previous):
        return ('flat', 'gray')
    diff = current - previous
    if diff > 0:
        return ('up', 'green')
    elif diff < 0:
        return ('down', 'red')
    else:
        return ('flat', 'gray')


def calc_growth_rate(current: float, previous: float) -> Optional[float]:
    if previous is None or previous == 0 or math.isnan(previous):
        return None
    return (current - previous) / abs(previous)


def calculate_kpis(df: pd.DataFrame,
                   revenue_col: str = 'revenue',
                   profit_col: str = 'profit',
                   cost_col: str = 'cost',
                   date_col: str = 'date',
                   compare_period: str = 'month') -> Dict:
    if df.empty:
        return {
            'revenue': 0, 'profit': 0, 'cost': 0, 'profit_margin': 0,
            'revenue_yoy': None, 'profit_yoy': None, 'cost_yoy': None,
            'revenue_mom': None, 'profit_mom': None, 'cost_mom': None,
        }

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)

    latest_date = df[date_col].max()

    if compare_period == 'month':
        current_period = latest_date.to_period('M')
        prev_period = current_period - 1
        yoy_period = current_period - 12
    elif compare_period == 'quarter':
        current_period = latest_date.to_period('Q')
        prev_period = current_period - 1
        yoy_period = current_period - 4
    elif compare_period == 'year':
        current_period = latest_date.to_period('Y')
        prev_period = current_period - 1
        yoy_period = current_period - 1
    else:
        current_period = latest_date.to_period('M')
        prev_period = current_period - 1
        yoy_period = current_period - 12

    period_freq_map = {'day': 'D', 'week': 'W', 'month': 'M', 'quarter': 'Q', 'year': 'Y'}
    period_freq = period_freq_map.get(compare_period, 'M')
    df['_period'] = df[date_col].dt.to_period(period_freq)

    current_data = df[df['_period'] == current_period]
    prev_data = df[df['_period'] == prev_period]
    yoy_data = df[df['_period'] == yoy_period]

    revenue = current_data[revenue_col].sum() if revenue_col in current_data.columns else 0
    profit = current_data[profit_col].sum() if profit_col in current_data.columns else 0
    cost = current_data[cost_col].sum() if cost_col in current_data.columns else 0
    profit_margin = profit / revenue if revenue != 0 else 0

    prev_revenue = prev_data[revenue_col].sum() if revenue_col in prev_data.columns else None
    prev_profit = prev_data[profit_col].sum() if profit_col in prev_data.columns else None
    prev_cost = prev_data[cost_col].sum() if cost_col in prev_data.columns else None

    yoy_revenue = yoy_data[revenue_col].sum() if revenue_col in yoy_data.columns else None
    yoy_profit = yoy_data[profit_col].sum() if profit_col in yoy_data.columns else None
    yoy_cost = yoy_data[cost_col].sum() if cost_col in yoy_data.columns else None

    return {
        'revenue': revenue,
        'profit': profit,
        'cost': cost,
        'profit_margin': profit_margin,
        'revenue_yoy': calc_growth_rate(revenue, yoy_revenue),
        'profit_yoy': calc_growth_rate(profit, yoy_profit),
        'cost_yoy': calc_growth_rate(cost, yoy_cost),
        'revenue_mom': calc_growth_rate(revenue, prev_revenue),
        'profit_mom': calc_growth_rate(profit, prev_profit),
        'cost_mom': calc_growth_rate(cost, prev_cost),
    }


def format_kpi_value(value: float, value_type: str = 'amount') -> str:
    if value_type == 'amount':
        return format_number(value)
    elif value_type == 'percent':
        return format_percent(value)
    else:
        return str(value)


def evaluate_condition(df: pd.DataFrame, condition_expr: str) -> pd.Series:
    try:
        return df.eval(condition_expr)
    except Exception:
        return pd.Series([False] * len(df), index=df.index)


def get_top_n(df: pd.DataFrame, dim_col: str, value_col: str, n: int = 10,
              ascending: bool = False) -> pd.DataFrame:
    if dim_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame()
    grouped = df.groupby(dim_col)[value_col].sum().reset_index()
    return grouped.sort_values(value_col, ascending=ascending).head(n)


def detect_anomalies(df: pd.DataFrame, value_col: str, date_col: str,
                     threshold: float = 0.3, period: str = 'month') -> pd.DataFrame:
    if value_col not in df.columns or date_col not in df.columns:
        return pd.DataFrame()

    freq_map = {'day': 'D', 'week': 'W', 'month': 'M', 'quarter': 'Q', 'year': 'Y'}
    freq = freq_map.get(period, 'M')
    agg = df.groupby(df[date_col].dt.to_period(freq))[value_col].sum().reset_index()
    agg.columns = [date_col, value_col]
    agg['prev_value'] = agg[value_col].shift(1)
    agg['change_rate'] = (agg[value_col] - agg['prev_value']) / agg['prev_value'].abs()
    anomalies = agg[agg['change_rate'].abs() > threshold].copy()
    return anomalies


class KPIConfig:
    def __init__(self):
        self.important_customer_condition = 'revenue > 1000000'
        self.potential_product_condition = 'growth_rate > 0.2'
        self.anomaly_threshold = 0.3
        self.top_n = 10
