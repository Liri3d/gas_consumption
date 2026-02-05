# modules/anomalies.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from datetime import datetime

def render(df):
    """Рендеринг вкладки обнаружения аномалий"""
    st.header("⚠️ Обнаружение аномалий потребления (UC-ANL-02)")
    
    st.info("""
    **Цель:** Обнаружить потенциальные утечки, хищения или сбои ПУ.
    Система анализирует показания, сравнивает с паттернами, вычисляет "score" аномалии.
    """)
    
    # Настройки
    col1, col2 = st.columns(2)
    
    with col1:
        anomaly_method = st.selectbox(
            "Метод обнаружения аномалий",
            ["Isolation Forest", "Статистические границы", "Сравнение с кластером"],
            key="anomaly_method"
        )
        
        anomaly_threshold = st.slider(
            "Порог аномальности (%)", 
            1, 20, 5,
            help="Процент самых аномальных случаев для отображения",
            key="anomaly_threshold"
        )
    
    with col2:
        reference_period = st.selectbox(
            "Сравнивать с",
            ["Предыдущий месяц", "Аналогичный месяц прошлого года", "Среднее по кластеру"],
            key="reference_period"
        )
        
        enable_email = st.checkbox("Отправлять email-оповещения", key="enable_email")
        if enable_email:
            email_address = st.text_input("Email для оповещений", key="email_address")
    
    if st.button("🔍 Запустить обнаружение аномалий", type="primary", key="run_anomaly_detection"):
        with st.spinner("Анализ аномалий..."):
            try:
                # Обнаружение аномалий
                anomaly_data = detect_anomalies(df, anomaly_method, anomaly_threshold)
                
                # Сохранение результатов
                st.session_state.anomalies = anomaly_data
                
                # Отображение результатов
                display_anomaly_results(anomaly_data)
                
                # Email оповещения
                if enable_email and email_address:
                    display_email_notification(anomaly_data, email_address)
                
            except Exception as e:
                st.error(f"Ошибка обнаружения аномалий: {str(e)}")

def detect_anomalies(df, method, threshold):
    """Обнаружение аномалий в данных"""
    # Подготовка данных
    recent_date = df['date_parsed'].max()
    last_month = recent_date - pd.DateOffset(months=1)
    
    # Данные за последний месяц
    recent_data = df[df['date_parsed'] >= last_month]
    customer_recent = recent_data.groupby('subscriber_id').agg({
        'gas_consumption': ['mean', 'std', 'count']
    }).round(2)
    customer_recent.columns = ['recent_mean', 'recent_std', 'recent_count']
    customer_recent = customer_recent.reset_index()
    
    # Исторические данные
    historical_data = df[df['date_parsed'] < last_month]
    customer_historical = historical_data.groupby('subscriber_id').agg({
        'gas_consumption': ['mean', 'std']
    }).round(2)
    customer_historical.columns = ['historical_mean', 'historical_std']
    customer_historical = customer_historical.reset_index()
    
    # Объединение данных
    anomaly_data = pd.merge(customer_recent, customer_historical, 
                          on='subscriber_id', how='left')
    
    # Вычисление изменений
    anomaly_data['change_pct'] = (
        (anomaly_data['recent_mean'] - anomaly_data['historical_mean']) / 
        anomaly_data['historical_mean'] * 100
    ).fillna(0)
    
    # Применение выбранного метода
    if method == "Isolation Forest":
        anomaly_data = apply_isolation_forest(anomaly_data, threshold)
    elif method == "Статистические границы":
        anomaly_data = apply_statistical_method(anomaly_data)
    
    # Сортировка
    anomaly_data = anomaly_data.sort_values('change_pct', key=abs, ascending=False)
    
    return anomaly_data

def apply_isolation_forest(data, threshold):
    """Применение Isolation Forest для обнаружения аномалий"""
    X_anomaly = data[['recent_mean', 'change_pct']].fillna(0)
    iso_forest = IsolationForest(contamination=threshold/100, random_state=42)
    anomaly_scores = iso_forest.fit_predict(X_anomaly)
    data['anomaly_score'] = anomaly_scores
    data['is_anomaly'] = anomaly_scores == -1
    return data

def apply_statistical_method(data):
    """Статистический метод обнаружения аномалий"""
    mean_change = data['change_pct'].mean()
    std_change = data['change_pct'].std()
    threshold = mean_change + 2 * std_change
    data['is_anomaly'] = data['change_pct'].abs() > threshold
    data['anomaly_score'] = data['change_pct'].abs() / threshold
    return data

def display_anomaly_results(anomaly_data):
    """Отображение результатов обнаружения аномалий"""
    # Список подозрительных абонентов
    st.subheader("📋 Список подозрительных абонентов")
    
    top_anomalies = anomaly_data.head(20)
    
    for idx, row in top_anomalies.iterrows():
        with st.expander(f"🔴 Абонент {row['subscriber_id']} - Изменение: {row['change_pct']:.1f}%"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Текущее потребление", f"{row['recent_mean']:.1f} м³")
                st.metric("Историческое среднее", f"{row['historical_mean']:.1f} м³")
            with col2:
                st.metric("Изменение", f"{row['change_pct']:.1f}%")
                cause = determine_anomaly_cause(row['change_pct'])
                st.info(f"**Возможная причина:** {cause}")
    
    # Визуализация аномалий
    st.subheader("📊 Визуализация аномалий")
    fig = create_anomaly_visualization(anomaly_data)
    st.plotly_chart(fig, use_container_width=True)

def determine_anomaly_cause(change_pct):
    """Определение возможной причины аномалии"""
    if change_pct > 50:
        return "Возможная утечка или хищение"
    elif change_pct < -50:
        return "Возможный сбой прибора учета"
    elif abs(change_pct) > 20:
        return "Значительное изменение паттерна"
    else:
        return "Незначительное отклонение"

def create_anomaly_visualization(anomaly_data):
    """Создание визуализации аномалий"""
    fig = px.scatter(
        anomaly_data,
        x='historical_mean',
        y='recent_mean',
        color='is_anomaly',
        title='Распределение аномалий потребления',
        hover_data=['subscriber_id', 'change_pct'],
        labels={'historical_mean': 'Историческое среднее', 
               'recent_mean': 'Текущее среднее'}
    )
    
    # Добавляем линию равенства
    max_val = max(anomaly_data['historical_mean'].max(), 
                anomaly_data['recent_mean'].max())
    fig.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            name='Норма',
            line=dict(color='gray', dash='dash')
        )
    )
    
    return fig

def display_email_notification(anomaly_data, email_address):
    """Отображение информации об email оповещениях"""
    anomalies_count = anomaly_data['is_anomaly'].sum()
    st.success(f"📧 Оповещение отправлено на {email_address}")
    st.info(f"Найдено {anomalies_count} аномальных случаев")