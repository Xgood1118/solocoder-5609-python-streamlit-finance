import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

from core.loader import DataSource
from core.transform import (
    add_time_periods, apply_filters, aggregate_by_period,
    aggregate_by_dimension, get_same_period_last_year, DrillState
)
from core.metrics import (
    calculate_kpis, format_number, format_percent,
    get_trend_direction, get_top_n, detect_anomalies,
    evaluate_condition, KPIConfig
)
from core.charts import (
    create_revenue_trend_chart, create_cost_structure_chart,
    create_profit_waterfall, create_cashflow_waterfall,
    create_bar_chart, create_pie_chart
)
from core.annotations import AnnotationManager
from core.report import (
    export_to_excel, generate_html_report, export_raw_data
)

st.set_page_config(
    page_title="财务数据大屏",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; }
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
    }
    .kpi-label { font-size: 0.85rem; color: #636E72; margin-bottom: 0.3rem; }
    .kpi-value { font-size: 1.8rem; font-weight: bold; color: #2D3436; }
    .kpi-change { font-size: 0.8rem; margin-top: 0.4rem; }
    .kpi-change.up { color: #26DE81; }
    .kpi-change.down { color: #FC5C65; }
    .kpi-change.flat { color: #A4B0BE; }
    .section-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin: 1rem 0 0.5rem 0;
        color: #2D3436;
    }
    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    .breadcrumb-item { color: #2E86DE; cursor: pointer; }
    .breadcrumb-sep { color: #A4B0BE; }
    .filter-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .stPlotlyChart { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if 'data_source' not in st.session_state:
        st.session_state.data_source = DataSource()
    if 'drill_state' not in st.session_state:
        st.session_state.drill_state = DrillState()
    if 'annotation_manager' not in st.session_state:
        st.session_state.annotation_manager = AnnotationManager()
    if 'kpi_config' not in st.session_state:
        st.session_state.kpi_config = KPIConfig()
    if 'column_config' not in st.session_state:
        st.session_state.column_config = {
            'date_col': 'date',
            'revenue_col': 'revenue',
            'profit_col': 'profit',
            'cost_col': 'cost',
            'dept_col': 'department',
            'product_col': 'product',
            'region_col': 'region',
        }
    if 'auto_refresh_interval' not in st.session_state:
        st.session_state.auto_refresh_interval = 0
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'overview'
    if 'selected_date_point' not in st.session_state:
        st.session_state.selected_date_point = None
    if 'show_annotation_panel' not in st.session_state:
        st.session_state.show_annotation_panel = None


def load_sample_data():
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    departments = ['销售一部', '销售二部', '销售三部', '技术部']
    products = ['产品A', '产品B', '产品C', '产品D']
    regions = ['华东', '华南', '华北', '西南']

    data = []
    import random
    random.seed(42)

    for d in dates:
        for dept in departments:
            for prod in products:
                for reg in regions:
                    revenue = random.uniform(5000, 50000)
                    cost_ratio = random.uniform(0.4, 0.7)
                    cost = revenue * cost_ratio
                    profit = revenue - cost
                    data.append({
                        'date': d.strftime('%Y-%m-%d'),
                        'department': dept,
                        'product': prod,
                        'region': reg,
                        'revenue': round(revenue, 2),
                        'cost': round(cost, 2),
                        'profit': round(profit, 2),
                    })

    df = pd.DataFrame(data)
    return df


def get_filtered_data():
    ds = st.session_state.data_source
    cfg = st.session_state.column_config

    if ds.joined_data is None or ds.joined_data.empty:
        return pd.DataFrame()

    df = ds.joined_data.copy()
    date_col = cfg.get('date_col', 'date')

    if date_col not in df.columns:
        return df

    df[date_col] = pd.to_datetime(df[date_col])

    category_filters = {}
    dept_col = cfg.get('dept_col', '')
    product_col = cfg.get('product_col', '')
    region_col = cfg.get('region_col', '')

    if 'selected_depts' in st.session_state and st.session_state.selected_depts and dept_col:
        category_filters[dept_col] = list(st.session_state.selected_depts)
    if 'selected_products' in st.session_state and st.session_state.selected_products and product_col:
        category_filters[product_col] = list(st.session_state.selected_products)
    if 'selected_regions' in st.session_state and st.session_state.selected_regions and region_col:
        category_filters[region_col] = list(st.session_state.selected_regions)

    drill_filters = {}
    current_drill = st.session_state.drill_state.get_current()
    if current_drill and current_drill.get('filters'):
        drill_filters = current_drill['filters']

    start_date = st.session_state.get('start_date')
    end_date = st.session_state.get('end_date')

    df_filtered = apply_filters(
        df, date_col,
        start_date=start_date.strftime('%Y-%m-%d') if start_date else None,
        end_date=end_date.strftime('%Y-%m-%d') if end_date else None,
        category_filters=category_filters,
        drill_filters=drill_filters
    )

    return df_filtered


def render_kpi_cards():
    cfg = st.session_state.column_config
    df = get_filtered_data()

    if df.empty:
        st.info("暂无数据，请先上传数据文件")
        return

    date_col = cfg.get('date_col', 'date')
    revenue_col = cfg.get('revenue_col', 'revenue')
    profit_col = cfg.get('profit_col', 'profit')
    cost_col = cfg.get('cost_col', 'cost')

    period = st.session_state.get('time_granularity', '月')
    period_map = {'日': 'day', '周': 'week', '月': 'month', '季': 'quarter', '年': 'year'}
    period_key = period_map.get(period, 'month')

    kpis = calculate_kpis(df, revenue_col, profit_col, cost_col, date_col, period_key)

    kpi_list = [
        ('本月营收', kpis['revenue'], kpis['revenue_yoy'], kpis['revenue_mom'], 'amount'),
        ('本月利润', kpis['profit'], kpis['profit_yoy'], kpis['profit_mom'], 'amount'),
        ('本月成本', kpis['cost'], kpis['cost_yoy'], kpis['cost_mom'], 'amount'),
        ('利润率', kpis['profit_margin'], None, None, 'percent'),
    ]

    cols = st.columns(4)
    for i, (label, value, yoy, mom, val_type) in enumerate(kpi_list):
        with cols[i]:
            if val_type == 'amount':
                value_str = format_number(value)
            else:
                value_str = format_percent(value)

            yoy_html = ""
            if yoy is not None:
                direction, color = get_trend_direction(yoy, 0)
                if yoy > 0:
                    arrow = "▲"
                elif yoy < 0:
                    arrow = "▼"
                else:
                    arrow = "—"
                yoy_html = f'<div class="kpi-change {direction}">同比 {arrow} {format_percent(abs(yoy))}</div>'

            mom_html = ""
            if mom is not None:
                direction, color = get_trend_direction(mom, 0)
                if mom > 0:
                    arrow = "▲"
                elif mom < 0:
                    arrow = "▼"
                else:
                    arrow = "—"
                mom_html = f'<div class="kpi-change {direction}">环比 {arrow} {format_percent(abs(mom))}</div>'

            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value_str}</div>
                {yoy_html}
                {mom_html}
            </div>
            """, unsafe_allow_html=True)


def render_filters():
    cfg = st.session_state.column_config
    ds = st.session_state.data_source

    with st.container():
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1.5])

        with col1:
            st.subheader("📊 财务数据大屏")
            if st.session_state.last_refresh_time:
                st.caption(f"上次刷新: {st.session_state.last_refresh_time}")

        with col2:
            period_options = ['日', '周', '月', '季', '年']
            st.selectbox("时间粒度", period_options, index=2, key='time_granularity')

        with col3:
            df = ds.joined_data
            if df is not None and not df.empty and cfg.get('date_col') in df.columns:
                date_series = pd.to_datetime(df[cfg['date_col']])
                min_date = date_series.min().date()
                max_date = date_series.max().date()
                st.date_input("时间范围",
                              value=(min_date, max_date),
                              min_value=min_date,
                              max_value=max_date,
                              key='date_range')
                if 'date_range' in st.session_state and st.session_state.date_range:
                    if isinstance(st.session_state.date_range, tuple) and len(st.session_state.date_range) == 2:
                        st.session_state.start_date = st.session_state.date_range[0]
                        st.session_state.end_date = st.session_state.date_range[1]

        with col4:
            if st.button("🔄 刷新数据", use_container_width=True):
                st.session_state.last_refresh_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.success("数据已刷新")
                st.rerun()

        with col5:
            refresh_options = ['不自动刷新', '30秒', '1分钟', '5分钟']
            selected = st.selectbox("自动刷新", refresh_options, index=0)
            interval_map = {'不自动刷新': 0, '30秒': 30, '1分钟': 60, '5分钟': 300}
            st.session_state.auto_refresh_interval = interval_map[selected]

        dept_col = cfg.get('dept_col', '')
        product_col = cfg.get('product_col', '')
        region_col = cfg.get('region_col', '')

        fcol1, fcol2, fcol3 = st.columns(3)

        if df is not None and not df.empty:
            with fcol1:
                if dept_col and dept_col in df.columns:
                    dept_options = sorted(df[dept_col].unique().tolist())
                    st.multiselect("🏢 部门", dept_options, key='selected_depts',
                                   default=dept_options)
                else:
                    st.multiselect("🏢 部门", [], key='selected_depts')

            with fcol2:
                if product_col and product_col in df.columns:
                    product_options = sorted(df[product_col].unique().tolist())
                    st.multiselect("📦 产品线", product_options, key='selected_products',
                                   default=product_options)
                else:
                    st.multiselect("📦 产品线", [], key='selected_products')

            with fcol3:
                if region_col and region_col in df.columns:
                    region_options = sorted(df[region_col].unique().tolist())
                    st.multiselect("📍 地区", region_options, key='selected_regions',
                                   default=region_options)
                else:
                    st.multiselect("📍 地区", [], key='selected_regions')

        st.markdown('</div>', unsafe_allow_html=True)


def render_breadcrumb():
    drill = st.session_state.drill_state
    breadcrumbs = ['总览'] + drill.get_breadcrumbs()

    st.markdown('<div class="breadcrumb">', unsafe_allow_html=True)
    for i, crumb in enumerate(breadcrumbs):
        if i > 0:
            st.markdown('<span class="breadcrumb-sep">›</span>', unsafe_allow_html=True)
        if i < len(breadcrumbs) - 1:
            if st.button(crumb, key=f"crumb_{i}", type="secondary"):
                for _ in range(len(breadcrumbs) - 1 - i):
                    drill.go_back()
                st.rerun()
        else:
            st.markdown(f'<strong>{crumb}</strong>', unsafe_allow_html=True)

    col_back, col_forward = st.columns([1, 1])
    with col_back:
        if drill.can_go_back():
            if st.button("← 返回", key="drill_back", type="secondary"):
                drill.go_back()
                st.rerun()
    with col_forward:
        if drill.can_go_forward():
            if st.button("前进 →", key="drill_forward", type="secondary"):
                drill.go_forward()
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_charts():
    cfg = st.session_state.column_config
    df = get_filtered_data()

    if df.empty:
        return

    date_col = cfg.get('date_col', 'date')
    revenue_col = cfg.get('revenue_col', 'revenue')
    profit_col = cfg.get('profit_col', 'profit')
    cost_col = cfg.get('cost_col', 'cost')
    product_col = cfg.get('product_col', 'product')
    dept_col = cfg.get('dept_col', 'department')

    period = st.session_state.get('time_granularity', '月')
    period_map = {'日': 'day', '周': 'week', '月': 'month', '季': 'quarter', '年': 'year'}
    period_key = period_map.get(period, 'month')

    st.markdown('<p class="section-title">📈 营收趋势</p>', unsafe_allow_html=True)

    trend_df = aggregate_by_period(df, date_col, [revenue_col, profit_col, cost_col], period_key)
    yoy_df = get_same_period_last_year(df, date_col, [revenue_col], period_key)

    if not trend_df.empty:
        trend_df['revenue_yoy'] = yoy_df[f'{revenue_col}_yoy'].values if f'{revenue_col}_yoy' in yoy_df.columns else None
        fig_trend = create_revenue_trend_chart(
            trend_df, period_key, revenue_col,
            yoy_col=f'{revenue_col}_yoy' if f'{revenue_col}_yoy' in trend_df.columns else None,
            title="营收月度趋势"
        )
        st.plotly_chart(fig_trend, use_container_width=True, key="revenue_trend")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="section-title">💸 成本结构</p>', unsafe_allow_html=True)
        if product_col and product_col in df.columns:
            cost_by_product = aggregate_by_dimension(
                df, [product_col], [cost_col, revenue_col, profit_col]
            )
            if not cost_by_product.empty:
                fig_cost = create_cost_structure_chart(
                    cost_by_product, product_col, [cost_col, profit_col],
                    title="产品成本与利润结构"
                )
                st.plotly_chart(fig_cost, use_container_width=True, key="cost_structure")

    with col2:
        st.markdown('<p class="section-title">💧 利润瀑布</p>', unsafe_allow_html=True)
        if dept_col and dept_col in df.columns:
            profit_by_dept = aggregate_by_dimension(df, [dept_col], [profit_col])
            if not profit_by_dept.empty:
                fig_waterfall = create_profit_waterfall(
                    profit_by_dept, dept_col, profit_col,
                    title="各部门利润构成"
                )
                st.plotly_chart(fig_waterfall, use_container_width=True, key="profit_waterfall")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<p class="section-title">🏢 部门营收排名</p>', unsafe_allow_html=True)
        if dept_col and dept_col in df.columns:
            top_dept = get_top_n(df, dept_col, revenue_col, n=10)
            if not top_dept.empty:
                fig_dept = create_bar_chart(
                    top_dept, dept_col, revenue_col,
                    title="部门营收排名", horizontal=True, color='#2E86DE'
                )
                st.plotly_chart(fig_dept, use_container_width=True, key="dept_ranking")

    with col4:
        st.markdown('<p class="section-title">📦 产品营收占比</p>', unsafe_allow_html=True)
        if product_col and product_col in df.columns:
            prod_revenue = aggregate_by_dimension(df, [product_col], [revenue_col])
            if not prod_revenue.empty:
                fig_pie = create_pie_chart(
                    prod_revenue, product_col, revenue_col,
                    title="产品营收占比"
                )
                st.plotly_chart(fig_pie, use_container_width=True, key="product_pie")

    st.markdown('<p class="section-title">🌊 现金流瀑布图</p>', unsafe_allow_html=True)
    total_revenue = df[revenue_col].sum() if revenue_col in df.columns else 0
    total_cost = df[cost_col].sum() if cost_col in df.columns else 0

    inflows = {'营业收入': total_revenue}
    outflows = {'运营成本': total_cost * 0.6, '人力成本': total_cost * 0.3, '其他支出': total_cost * 0.1}

    fig_cf = create_cashflow_waterfall(
        total_revenue * 0.1, inflows, outflows,
        title="现金流瀑布图"
    )
    st.plotly_chart(fig_cf, use_container_width=True, key="cashflow_waterfall")


def render_sidebar():
    with st.sidebar:
        st.title("⚙️ 数据配置")

        st.subheader("📁 数据上传")
        uploaded_files = st.file_uploader(
            "上传 CSV/Excel 文件",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key='file_uploader'
        )

        if uploaded_files:
            for file in uploaded_files:
                file_bytes = file.read()
                name = file.name.rsplit('.', 1)[0]
                try:
                    st.session_state.data_source.add_table(name, file_bytes, file.name)
                    st.success(f"已加载: {file.name}")
                except Exception as e:
                    st.error(f"加载失败 {file.name}: {e}")

        if st.button("📊 使用示例数据", use_container_width=True):
            sample_df = load_sample_data()
            st.session_state.data_source.tables = {'示例数据': sample_df}
            st.session_state.data_source.column_mappings = {
                '示例数据': {col: col for col in sample_df.columns}
            }
            st.session_state.data_source.joined_data = sample_df
            st.success("示例数据已加载")

        st.divider()

        st.subheader("🔗 列名映射")
        ds = st.session_state.data_source
        if ds.tables:
            table_names = list(ds.tables.keys())
            selected_table = st.selectbox("选择表", table_names, key='selected_table_map')

            if selected_table:
                cols = ds.get_available_columns(selected_table)
                st.caption(f"共 {len(cols)} 列")

                biz_mapping = {}
                for col in cols:
                    new_name = st.text_input(
                        f"原始: {col}",
                        value=ds.column_mappings.get(selected_table, {}).get(col, col),
                        key=f"map_{selected_table}_{col}"
                    )
                    biz_mapping[col] = new_name

                if st.button("应用映射", key="apply_mapping"):
                    ds.update_column_mapping(selected_table, biz_mapping)
                    ds.build_joined_data({})
                    st.success("列名映射已应用")

        st.divider()

        st.subheader("🏷️ 指标列配置")
        cfg = st.session_state.column_config
        ds = st.session_state.data_source

        if ds.joined_data is not None and not ds.joined_data.empty:
            all_cols = list(ds.joined_data.columns)

            cfg['date_col'] = st.selectbox(
                "日期列", all_cols,
                index=all_cols.index(cfg['date_col']) if cfg['date_col'] in all_cols else 0,
                key='cfg_date'
            )
            cfg['revenue_col'] = st.selectbox(
                "营收列", all_cols,
                index=all_cols.index(cfg['revenue_col']) if cfg['revenue_col'] in all_cols else 0,
                key='cfg_revenue'
            )
            cfg['profit_col'] = st.selectbox(
                "利润列", all_cols,
                index=all_cols.index(cfg['profit_col']) if cfg['profit_col'] in all_cols else 0,
                key='cfg_profit'
            )
            cfg['cost_col'] = st.selectbox(
                "成本列", all_cols,
                index=all_cols.index(cfg['cost_col']) if cfg['cost_col'] in all_cols else 0,
                key='cfg_cost'
            )
            cfg['dept_col'] = st.selectbox(
                "部门列", [''] + all_cols,
                index=(all_cols.index(cfg['dept_col']) + 1) if cfg['dept_col'] in all_cols else 0,
                key='cfg_dept'
            )
            cfg['product_col'] = st.selectbox(
                "产品列", [''] + all_cols,
                index=(all_cols.index(cfg['product_col']) + 1) if cfg['product_col'] in all_cols else 0,
                key='cfg_product'
            )
            cfg['region_col'] = st.selectbox(
                "地区列", [''] + all_cols,
                index=(all_cols.index(cfg['region_col']) + 1) if cfg['region_col'] in all_cols else 0,
                key='cfg_region'
            )
        else:
            st.info("请先上传数据")

        st.divider()

        st.subheader("🎯 业务规则配置")
        kpi_cfg = st.session_state.kpi_config

        kpi_cfg.top_n = st.number_input("TOP N 数量", min_value=1, value=kpi_cfg.top_n, key='cfg_topn')
        kpi_cfg.important_customer_condition = st.text_input(
            "重要客户条件",
            value=kpi_cfg.important_customer_condition,
            help="使用 pandas 表达式，如: revenue > 1000000",
            key='cfg_important'
        )
        kpi_cfg.potential_product_condition = st.text_input(
            "潜力产品条件",
            value=kpi_cfg.potential_product_condition,
            help="使用 pandas 表达式，如: growth_rate > 0.2",
            key='cfg_potential'
        )
        kpi_cfg.anomaly_threshold = st.slider(
            "异常波动阈值",
            min_value=0.0, max_value=1.0, value=kpi_cfg.anomaly_threshold, step=0.05,
            key='cfg_anomaly'
        )

        st.divider()

        st.subheader("📤 数据导出")

        df = get_filtered_data()
        if not df.empty:
            excel_data = export_to_excel({'筛选后数据': df})
            st.download_button(
                "📥 导出 Excel",
                data=excel_data,
                file_name=f"财务数据_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            cfg = st.session_state.column_config
            date_col = cfg.get('date_col', 'date')
            revenue_col = cfg.get('revenue_col', 'revenue')
            profit_col = cfg.get('profit_col', 'profit')
            cost_col = cfg.get('cost_col', 'cost')
            kpis = calculate_kpis(df, revenue_col, profit_col, cost_col, date_col, 'month')

            charts_html = {}
            period = st.session_state.get('time_granularity', '月')
            period_map = {'日': 'day', '周': 'week', '月': 'month', '季': 'quarter', '年': 'year'}
            period_key = period_map.get(period, 'month')

            trend_df = aggregate_by_period(df, date_col, [revenue_col], period_key)
            if not trend_df.empty:
                fig = create_revenue_trend_chart(trend_df, period_key, revenue_col)
                charts_html['营收趋势'] = fig.to_html(full_html=False, include_plotlyjs='cdn')

            html_report = generate_html_report(kpis, charts_html, title="财务数据分析报告")
            st.download_button(
                "📄 导出 HTML 报告",
                data=html_report,
                file_name=f"财务报告_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True
            )
            st.caption("提示：打开 HTML 后可用浏览器打印为 PDF")
        else:
            st.info("暂无数据可导出")

        st.divider()
        st.caption("v1.0.0 | 财务数据大屏")


def main():
    init_session_state()
    render_sidebar()

    render_filters()
    render_breadcrumb()
    render_kpi_cards()
    render_charts()

    if st.session_state.auto_refresh_interval > 0:
        time.sleep(st.session_state.auto_refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
