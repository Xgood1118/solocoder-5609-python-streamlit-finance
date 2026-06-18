import io
import base64
import pandas as pd
from typing import Dict, List, Optional
import json

try:
    import plotly.io as pio
    _KALEIDO_AVAILABLE = True
except Exception:
    _KALEIDO_AVAILABLE = False

try:
    from weasyprint import HTML
    _WEASYPRINT_AVAILABLE = True
except Exception:
    _WEASYPRINT_AVAILABLE = False


def fig_to_svg_base64(fig) -> Optional[str]:
    if not _KALEIDO_AVAILABLE:
        return None
    try:
        svg_bytes = pio.to_image(fig, format='svg', width=900, height=500)
        return base64.b64encode(svg_bytes).decode('utf-8')
    except Exception:
        return None


def fig_to_png_base64(fig) -> Optional[str]:
    if not _KALEIDO_AVAILABLE:
        return None
    try:
        png_bytes = pio.to_image(fig, format='png', width=900, height=500, scale=2)
        return base64.b64encode(png_bytes).decode('utf-8')
    except Exception:
        return None


def export_to_excel(dataframes: Dict[str, pd.DataFrame],
                    sheet_names: Optional[List[str]] = None) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#2E86DE',
            'font_color': 'white',
            'border': 1,
        })

        for i, (name, df) in enumerate(dataframes.items()):
            sheet_name = (sheet_names[i] if sheet_names and i < len(sheet_names) else name)[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            worksheet = writer.sheets[sheet_name]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                column_len = max(df[value].astype(str).str.len().max(), len(str(value))) + 2
                worksheet.set_column(col_num, col_num, min(column_len, 30))

    output.seek(0)
    return output.read()


def generate_html_report(kpis: Dict, charts_html: Dict[str, str],
                         annotations: Dict = None,
                         title: str = "财务数据分析报告") -> str:
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            background: #f5f6fa;
            color: #2D3436;
            padding: 20px;
        }}
        .report-header {{
            background: linear-gradient(135deg, #2E86DE 0%, #6C5CE7 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .report-header h1 {{
            font-size: 28px;
            margin-bottom: 8px;
        }}
        .report-header p {{
            opacity: 0.9;
        }}
        .kpi-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .kpi-label {{
            font-size: 14px;
            color: #636E72;
            margin-bottom: 8px;
        }}
        .kpi-value {{
            font-size: 28px;
            font-weight: bold;
            color: #2D3436;
        }}
        .kpi-change {{
            font-size: 13px;
            margin-top: 6px;
        }}
        .kpi-change.up {{ color: #26DE81; }}
        .kpi-change.down {{ color: #FC5C65; }}
        .kpi-change.flat {{ color: #A4B0BE; }}
        .chart-section {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .chart-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 16px;
            color: #2D3436;
        }}
        .chart-container {{
            width: 100%;
        }}
        .annotations-section {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .annotation-item {{
            padding: 12px;
            border-left: 4px solid #2E86DE;
            background: #F8F9FA;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
        .annotation-meta {{
            font-size: 12px;
            color: #636E72;
            margin-bottom: 4px;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .chart-section, .kpi-card, .annotations-section {{
                break-inside: avoid;
                box-shadow: none;
                border: 1px solid #eee;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{title}</h1>
        <p>生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="kpi-section">
"""

    kpi_items = [
        ('本月营收', kpis.get('revenue', 0), kpis.get('revenue_yoy'), kpis.get('revenue_mom'), 'amount'),
        ('本月利润', kpis.get('profit', 0), kpis.get('profit_yoy'), kpis.get('profit_mom'), 'amount'),
        ('本月成本', kpis.get('cost', 0), kpis.get('cost_yoy'), kpis.get('cost_mom'), 'amount'),
        ('利润率', kpis.get('profit_margin', 0), None, None, 'percent'),
    ]

    for label, value, yoy, mom, val_type in kpi_items:
        if val_type == 'amount':
            from core.metrics import format_number
            value_str = format_number(value)
        else:
            from core.metrics import format_percent
            value_str = format_percent(value)

        change_text = ""
        if yoy is not None:
            from core.metrics import format_percent
            direction = "up" if yoy > 0 else ("down" if yoy < 0 else "flat")
            arrow = "↑" if yoy > 0 else ("↓" if yoy < 0 else "→")
            change_text += f'<div class="kpi-change {direction}">同比 {arrow} {format_percent(abs(yoy))}</div>'
        if mom is not None:
            from core.metrics import format_percent
            direction = "up" if mom > 0 else ("down" if mom < 0 else "flat")
            arrow = "↑" if mom > 0 else ("↓" if mom < 0 else "→")
            change_text += f'<div class="kpi-change {direction}">环比 {arrow} {format_percent(abs(mom))}</div>'

        html += f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value_str}</div>
            {change_text}
        </div>
"""

    html += """
    </div>
"""

    for chart_id, chart_html_content in charts_html.items():
        html += f"""
    <div class="chart-section">
        <div class="chart-title">{chart_id}</div>
        <div class="chart-container">
            {chart_html_content}
        </div>
    </div>
"""

    if annotations:
        html += """
    <div class="annotations-section">
        <h3>图表注释</h3>
"""
        for chart_id, ann_list in annotations.items():
            if ann_list:
                html += f"<h4>{chart_id}</h4>"
                for ann in ann_list:
                    html += f"""
        <div class="annotation-item">
            <div class="annotation-meta">{ann.get('author', '匿名')} · {ann.get('created_at', '')}</div>
            <div>{ann.get('content', '')}</div>
        </div>
"""
        html += """
    </div>
"""

    html += """
</body>
</html>
"""
    return html


def replace_template(template_text: str, data: Dict) -> str:
    result = template_text
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        if isinstance(value, float):
            from core.metrics import format_number
            value_str = format_number(value)
        elif isinstance(value, pd.DataFrame):
            value_str = value.to_html(index=False)
        else:
            value_str = str(value)
        result = result.replace(placeholder, value_str)
    return result


def export_raw_data(df: pd.DataFrame, filename: str = "raw_data.xlsx") -> bytes:
    return export_to_excel({"原始数据": df}, [filename.replace('.xlsx', '')])


def generate_pdf_report(kpis: Dict, charts: Dict[str, object],
                        annotations: Dict = None,
                        title: str = "财务数据分析报告") -> bytes:
    if not _WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint 未安装，请先执行 pip install weasyprint")

    chart_images = {}
    for chart_id, fig in charts.items():
        img_b64 = fig_to_png_base64(fig)
        if img_b64:
            chart_images[chart_id] = f'<img src="data:image/png;base64,{img_b64}" style="width:100%;max-width:800px;">'
        else:
            chart_images[chart_id] = f'<div style="padding:40px;text-align:center;color:#999;border:1px dashed #ddd;">[图表：{chart_id}]</div>'

    html_content = generate_html_report(kpis, chart_images, annotations, title)

    buf = io.BytesIO()
    HTML(string=html_content).write_pdf(buf)
    buf.seek(0)
    return buf.read()


def is_pdf_available() -> bool:
    return _WEASYPRINT_AVAILABLE and _KALEIDO_AVAILABLE


def get_pdf_dependencies_status() -> Dict[str, bool]:
    return {
        'weasyprint': _WEASYPRINT_AVAILABLE,
        'kaleido': _KALEIDO_AVAILABLE,
    }
