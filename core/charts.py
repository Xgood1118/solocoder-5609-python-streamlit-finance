import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Optional, Dict
from plotly.subplots import make_subplots


COLORS = {
    'revenue': '#2E86DE',
    'profit': '#26DE81',
    'cost': '#FC5C65',
    'up': '#26DE81',
    'down': '#FC5C65',
    'flat': '#A4B0BE',
    'primary': '#2E86DE',
    'secondary': '#6C5CE7',
    'bg': '#FFFFFF',
    'text': '#2D3436',
}


def create_revenue_trend_chart(df: pd.DataFrame, date_col: str,
                               revenue_col: str,
                               yoy_col: Optional[str] = None,
                               title: str = "营收趋势") -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title, xaxis_title="日期", yaxis_title="金额")
        return fig

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=df[revenue_col],
        mode='lines+markers',
        name='本期营收',
        line=dict(color=COLORS['revenue'], width=3),
        marker=dict(size=8),
        hovertemplate='%{x}<br>营收: %{y:,.2f}<extra></extra>'
    ))

    if yoy_col and yoy_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df[date_col],
            y=df[yoy_col],
            mode='lines+markers',
            name='去年同期',
            line=dict(color=COLORS['secondary'], width=2, dash='dash'),
            marker=dict(size=6),
            hovertemplate='%{x}<br>去年同期: %{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['text'])),
        xaxis_title="日期",
        yaxis_title="金额（元）",
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    fig.update_yaxes(gridcolor='#F1F2F6', zerolinecolor='#E0E0E0')
    fig.update_xaxes(gridcolor='#F1F2F6')

    return fig


def create_cost_structure_chart(df: pd.DataFrame, dim_col: str,
                                cost_cols: List[str],
                                title: str = "成本结构") -> go.Figure:
    if df.empty or dim_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(title=title)
        return fig

    valid_cols = [c for c in cost_cols if c in df.columns]

    fig = go.Figure()
    color_palette = ['#2E86DE', '#6C5CE7', '#FD79A8', '#FDCB6E', '#00B894', '#E17055', '#74B9FF', '#A29BFE']

    for i, col in enumerate(valid_cols):
        color = color_palette[i % len(color_palette)]
        fig.add_trace(go.Bar(
            x=df[dim_col],
            y=df[col],
            name=col,
            marker_color=color,
            hovertemplate='%{x}<br>%{fullData.name}: %{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['text'])),
        barmode='stack',
        xaxis_title=dim_col,
        yaxis_title="金额（元）",
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    fig.update_yaxes(gridcolor='#F1F2F6', zerolinecolor='#E0E0E0')

    return fig


def create_profit_waterfall(df: pd.DataFrame, category_col: str,
                            value_col: str,
                            title: str = "利润瀑布图") -> go.Figure:
    if df.empty or category_col not in df.columns or value_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(title=title)
        return fig

    categories = df[category_col].tolist()
    values = df[value_col].tolist()

    running_total = 0
    base = []
    measure = []
    text_values = []

    for i, v in enumerate(values):
        if v >= 0:
            measure.append('increase')
            base.append(running_total)
        else:
            measure.append('decrease')
            base.append(running_total + v)
        running_total += v
        text_values.append(f"{v:,.2f}")

    base.append(0)
    categories.append('净利润')
    measure.append('total')
    text_values.append(f"{running_total:,.2f}")
    values.append(running_total)

    fig = go.Figure(go.Waterfall(
        name="利润构成",
        orientation="v",
        measure=measure,
        x=categories,
        text=text_values,
        textposition="outside",
        decreasing=dict(marker=dict(color=COLORS['down'])),
        increasing=dict(marker=dict(color=COLORS['up'])),
        totals=dict(marker=dict(color=COLORS['primary'])),
        connector=dict(line=dict(color='#636E72', width=1, dash='dot')),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['text'])),
        yaxis_title="金额（元）",
        margin=dict(l=40, r=40, t=60, b=80),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    fig.update_yaxes(gridcolor='#F1F2F6', zerolinecolor='#E0E0E0')

    return fig


def create_cashflow_waterfall(opening: float, inflows: Dict[str, float],
                              outflows: Dict[str, float],
                              title: str = "现金流瀑布图") -> go.Figure:
    categories = ['期初余额']
    values = [opening]
    measure = ['absolute']

    for name, val in inflows.items():
        categories.append(name)
        values.append(val)
        measure.append('increase')

    for name, val in outflows.items():
        categories.append(name)
        values.append(-val)
        measure.append('decrease')

    total = opening + sum(inflows.values()) - sum(outflows.values())
    categories.append('期末余额')
    values.append(total)
    measure.append('total')

    text_values = [f"{v:,.2f}" for v in values]

    fig = go.Figure(go.Waterfall(
        name="现金流",
        orientation="v",
        measure=measure,
        x=categories,
        text=text_values,
        textposition="outside",
        decreasing=dict(marker=dict(color=COLORS['down'])),
        increasing=dict(marker=dict(color=COLORS['up'])),
        totals=dict(marker=dict(color=COLORS['primary'])),
        connector=dict(line=dict(color='#636E72', width=1, dash='dot')),
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['text'])),
        yaxis_title="金额（元）",
        margin=dict(l=40, r=40, t=60, b=80),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    fig.update_yaxes(gridcolor='#F1F2F6', zerolinecolor='#E0E0E0')

    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str,
                     title: str = "", color: str = COLORS['primary'],
                     horizontal: bool = False) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title)
        return fig

    if horizontal:
        fig = go.Figure(go.Bar(
            x=df[y_col],
            y=df[x_col],
            orientation='h',
            marker_color=color,
            hovertemplate='%{y}<br>%{x:,.2f}<extra></extra>'
        ))
    else:
        fig = go.Figure(go.Bar(
            x=df[x_col],
            y=df[y_col],
            marker_color=color,
            hovertemplate='%{x}<br>%{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=COLORS['text'])),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    fig.update_yaxes(gridcolor='#F1F2F6', zerolinecolor='#E0E0E0')

    return fig


def create_pie_chart(df: pd.DataFrame, name_col: str, value_col: str,
                     title: str = "") -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title)
        return fig

    fig = px.pie(df, names=name_col, values=value_col, title=title,
                 hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    return fig


def style_chart(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        font=dict(family='Microsoft YaHei, Arial, sans-serif', size=12),
        plot_bgcolor=COLORS['bg'],
        paper_bgcolor=COLORS['bg'],
    )
    return fig
