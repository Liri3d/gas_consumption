# modules/reports.py
import streamlit as st
import pandas as pd
import io
import base64
from datetime import datetime

def render(df):
    """Рендеринг вкладки отчетов"""
    st.header("📋 Формирование отчетов (US-VIE-02)")
    
    st.info("""
    **Цель:** Сформировать отчеты по эффективности с выбором формата файла.
    """)
    
    # Настройки отчета
    col1, col2 = st.columns(2)
    
    with col1:
        report_type = st.selectbox(
            "Тип отчета",
            ["Общий отчет по анализам", "Отчет по кластеризации", 
             "Отчет по аномалиям", "Отчет по прогнозам", "Комплексный отчет"],
            key="report_type"
        )
        
        report_format = st.selectbox(
            "Формат отчета",
            ["PDF", "CSV", "Excel", "HTML"],
            key="report_format"
        )
    
    with col2:
        report_period = st.date_input(
            "Период отчета",
            [df['date_parsed'].min(), df['date_parsed'].max()],
            min_value=df['date_parsed'].min(),
            max_value=df['date_parsed'].max(),
            key="report_period"
        )
        
        include_charts = st.checkbox("Включать графики в отчет", value=True, key="include_charts")
    
    if st.button("📄 Сформировать отчет", type="primary", key="generate_report"):
        with st.spinner("Формирование отчета..."):
            try:
                # Создание отчета
                report_data = generate_report_data(df, report_type, report_period)
                
                # Предварительный просмотр
                display_report_preview(report_data)
                
                # Экспорт
                export_report(report_data, report_type, report_format)
                
                st.success("✅ Отчет успешно сформирован!")
                
            except Exception as e:
                st.error(f"Ошибка формирования отчета: {str(e)}")

def generate_report_data(df, report_type, report_period):
    """Генерация данных для отчета"""
    report_data = {
        "Общая информация": {
            "Дата формирования": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "Период отчета": f"{report_period[0]} - {report_period[1]}",
            "Всего записей": len(df),
            "Уникальных абонентов": df['subscriber_id'].nunique(),
            "Период данных": f"{df['date_parsed'].min().strftime('%d.%m.%Y')} - {df['date_parsed'].max().strftime('%d.%m.%Y')}"
        }
    }
    
    # Добавление данных в зависимости от типа отчета
    if report_type in ["Общий отчет по анализам", "Комплексный отчет"]:
        if 'clusters' in st.session_state and st.session_state.clusters is not None:
            report_data["Кластеризация"] = get_clustering_report_data()
        
        if 'anomalies' in st.session_state and st.session_state.anomalies is not None:
            report_data["Обнаружение аномалий"] = get_anomalies_report_data()
        
        if 'forecast' in st.session_state and st.session_state.forecast is not None:
            report_data["Прогнозирование"] = get_forecast_report_data()
    
    elif report_type == "Отчет по кластеризации":
        if 'clusters' in st.session_state and st.session_state.clusters is not None:
            report_data["Детали кластеризации"] = get_detailed_clustering_report_data()
    
    return report_data

def get_clustering_report_data():
    """Получение данных по кластеризации для отчета"""
    clusters = st.session_state.clusters
    return {
        "Количество кластеров": clusters['cluster'].nunique(),
        "Распределение по кластерам": clusters['cluster'].value_counts().to_dict()
    }

def get_anomalies_report_data():
    """Получение данных по аномалиям для отчета"""
    anomalies = st.session_state.anomalies
    anomalies_found = anomalies['is_anomaly'].sum()
    return {
        "Найдено аномалий": int(anomalies_found),
        "Процент аномалий": f"{(anomalies_found / len(anomalies) * 100):.2f}%"
    }

def get_forecast_report_data():
    """Получение данных по прогнозам для отчета"""
    forecast = st.session_state.forecast
    return {
        "Средний прогноз": f"{forecast['yhat'].mean():.1f} м³",
        "Период прогноза": f"{len(forecast)} дней"
    }

def get_detailed_clustering_report_data():
    """Получение детальных данных по кластеризации для отчета"""
    clusters = st.session_state.clusters
    return {
        "Алгоритм": "K-means / Иерархическая",
        "Количество кластеров": clusters['cluster'].nunique(),
        "Статистика по кластерам": clusters.groupby('cluster').agg({
            'mean_consumption': 'mean',
            'total_consumption': 'sum',
            'subscriber_id': 'count'
        }).round(2).to_dict()
    }

def display_report_preview(report_data):
    """Предварительный просмотр отчета"""
    st.subheader("👁️ Предварительный просмотр отчета")
    
    for section, data in report_data.items():
        with st.expander(f"📑 {section}"):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        st.write(f"**{key}:**")
                        for subkey, subvalue in value.items():
                            st.write(f"  {subkey}: {subvalue}")
                    else:
                        st.write(f"**{key}:** {value}")
            else:
                st.write(data)

def export_report(report_data, report_type, report_format):
    """Экспорт отчета в выбранном формате"""
    st.subheader("📤 Экспорт отчета")
    
    if report_format == "CSV":
        export_csv(report_data, report_type)
    elif report_format == "Excel":
        export_excel(report_data, report_type)
    elif report_format == "PDF":
        st.info("📄 PDF экспорт требует дополнительных библиотек (reportlab, fpdf).")
    else:  # HTML
        export_html(report_data, report_type)

def export_csv(report_data, report_type):
    """Экспорт в CSV"""
    report_df = pd.DataFrame([
        {"Раздел": key, "Параметр": subkey, "Значение": subvalue}
        for key, value in report_data.items()
        for subkey, subvalue in (value.items() if isinstance(value, dict) else [("Значение", value)])
    ])
    
    csv_report = report_df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv_report.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="отчет_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv">Скачать отчет в CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

def export_excel(report_data, report_type):
    """Экспорт в Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for section, data in report_data.items():
            if isinstance(data, dict):
                section_df = pd.DataFrame(list(data.items()), columns=['Параметр', 'Значение'])
                section_df.to_excel(writer, index=False, sheet_name=section[:30])
    
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="отчет_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx">Скачать отчет в Excel</a>'
    st.markdown(href, unsafe_allow_html=True)

def export_html(report_data, report_type):
    """Экспорт в HTML"""
    html_report = "<html><head><title>Отчет анализа потребления газа</title></head><body>"
    html_report += "<h1>Отчет анализа потребления газа</h1>"
    
    for section, data in report_data.items():
        html_report += f"<h2>{section}</h2>"
        if isinstance(data, dict):
            html_report += "<table border='1'><tr><th>Параметр</th><th>Значение</th></tr>"
            for key, value in data.items():
                html_report += f"<tr><td>{key}</td><td>{value}</td></tr>"
            html_report += "</table>"
        else:
            html_report += f"<p>{data}</p>"
    
    html_report += f"<p><i>Сформировано: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</i></p>"
    html_report += "</body></html>"
    
    b64 = base64.b64encode(html_report.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="отчет_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html">Скачать отчет в HTML</a>'
    st.markdown(href, unsafe_allow_html=True)