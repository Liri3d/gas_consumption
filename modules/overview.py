# modules/overview.py
import streamlit as st
import pandas as pd
import plotly.express as px
import io
import base64
from utils.visualization import create_consumption_chart

def render(df):
    """Рендеринг вкладки обзора данных"""
    st.header("📊 Обзор данных и статистики (UC-VIEW-01)")
    
    # Фильтры
    col1, col2, col3 = st.columns(3)
    with col1:
        management_filter = st.selectbox(
            "Выберите управление",
            ["Все"] + sorted(df['management'].unique().tolist()),
            key="overview_management_filter"
        )
    
    with col2:
        data_type = st.selectbox(
            "Выберите тип данных",
            ["Абоненты", "Аномалии", "Прогнозы"],
            key="overview_data_type"
        )
    
    with col3:
        date_range = st.date_input(
            "Выберите период",
            [df['date_parsed'].min(), df['date_parsed'].max()],
            min_value=df['date_parsed'].min(),
            max_value=df['date_parsed'].max(),
            key="overview_date_range"
        )
    
    # Применение фильтров
    filtered_df = apply_filters(df, management_filter, date_range)
    
    # Основные метрики
    render_metrics(filtered_df)
    
    # График потребления
    render_consumption_chart(filtered_df)
    
    # Предпросмотр данных
    render_data_preview(filtered_df)
    
    # Экспорт данных
    render_export_section(filtered_df)

def apply_filters(df, management_filter, date_range):
    """Применение фильтров к данным"""
    filtered_df = df.copy()
    
    if management_filter != "Все":
        filtered_df = filtered_df[filtered_df['management'] == management_filter]
    
    if len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['date_parsed'] >= pd.to_datetime(date_range[0])) &
            (filtered_df['date_parsed'] <= pd.to_datetime(date_range[1]))
        ]
    
    return filtered_df

def render_metrics(filtered_df):
    """Отображение основных метрик"""
    st.subheader("📈 Основные показатели")
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("Всего записей", f"{len(filtered_df):,}")
    with metric_col2:
        st.metric("Уникальных абонентов", filtered_df["subscriber_id"].nunique())
    with metric_col3:
        min_date = filtered_df['date_parsed'].min().strftime('%d.%m.%Y')
        max_date = filtered_df['date_parsed'].max().strftime('%d.%m.%Y')
        st.metric("Период", f"{min_date} - {max_date}")
    with metric_col4:
        avg_consumption = filtered_df['gas_consumption'].mean()
        st.metric("Среднее потребление", f"{avg_consumption:,.1f} м³")

def render_consumption_chart(filtered_df):
    """Отображение графика потребления"""
    st.subheader("📊 График потребления")
    
    # Агрегация по дате
    daily_data = filtered_df.groupby('date_parsed')['gas_consumption'].sum().reset_index()
    
    fig = create_consumption_chart(daily_data)
    st.plotly_chart(fig, use_container_width=True)

def render_data_preview(filtered_df):
    """Предпросмотр данных"""
    with st.expander("👁️ Просмотр данных", expanded=True):
        st.dataframe(filtered_df.head(100)) 

def render_export_section(filtered_df):
    """Экспорт данных"""
    st.subheader("📥 Экспорт данных")
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        if st.button("📄 Экспорт в CSV", key="export_csv"):
            csv = filtered_df.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="газ_данные.csv">Скачать CSV файл</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with export_col2:
        if st.button("📊 Экспорт в Excel", key="export_excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Данные')
            b64 = base64.b64encode(output.getvalue()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="газ_данные.xlsx">Скачать Excel файл</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with export_col3:
        if st.button("📈 Статистический отчет", key="export_stats"):
            stats_report = generate_stats_report(filtered_df)
            st.dataframe(stats_report)

def generate_stats_report(df):
    """Генерация статистического отчета"""
    return pd.DataFrame({
        'Показатель': [
            'Всего записей', 'Уникальных абонентов', 
            'Среднее потребление', 'Максимальное потребление',
            'Минимальное потребление', 'Стандартное отклонение'
        ],
        'Значение': [
            len(df),
            df["subscriber_id"].nunique(),
            f"{df['gas_consumption'].mean():.1f} м³",
            f"{df['gas_consumption'].max():.1f} м³",
            f"{df['gas_consumption'].min():.1f} м³",
            f"{df['gas_consumption'].std():.1f}"
        ]
    })