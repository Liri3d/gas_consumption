# modules/clustering.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
import base64
from utils.visualization import create_cluster_scatter, create_cluster_profiles

def render(df):
    """Рендеринг вкладки кластеризации"""
    st.header("🔍 Кластеризация абонентов по паттернам потребления (UC-ANL-01)")
    
    st.info("""
    **Цель:** Сегментировать базу абонентов для тарифного планирования и анализа.
    Система анализирует исторические данные, применяет ML-модели, формирует кластеры.
    """)
    
    # Настройки кластеризации
    col1, col2 = st.columns(2)
    
    with col1:
        algorithm = st.selectbox(
            "Выберите алгоритм кластеризации",
            ["K-means", "Иерархическая кластеризация"],
            help="US-ANL-01 критерий 4: не менее 2 алгоритмов",
            key="clustering_algorithm"
        )
        
        if algorithm == "K-means":
            n_clusters = st.slider("Количество кластеров", 2, 10, 5, key="n_clusters_kmeans")
        else:
            n_clusters = st.slider("Количество кластеров", 2, 10, 5, key="n_clusters_hierarchical")
    
    with col2:
        features = st.multiselect(
            "Выберите признаки для кластеризации",
            ['mean_consumption', 'total_consumption', 'consumption_variance', 'seasonality'],
            default=['mean_consumption', 'total_consumption'],
            key="clustering_features"
        )
    
    if st.button("🚀 Запустить кластеризацию", type="primary", key="run_clustering"):
        with st.spinner("Выполняется кластеризация..."):
            try:
                # Подготовка данных
                customer_stats = prepare_customer_stats(df)
                
                # Кластеризация
                results = perform_clustering(customer_stats, features, algorithm, n_clusters)
                
                # Сохранение результатов
                st.session_state.clusters = results
                
                # Отображение результатов
                display_clustering_results(results, n_clusters)
                
                # Экспорт
                display_export_section(results, n_clusters)
                
            except Exception as e:
                st.error(f"Ошибка кластеризации: {str(e)}")

def prepare_customer_stats(df):
    """Подготовка статистики по клиентам"""
    customer_stats = df.groupby('subscriber_id').agg({
        'gas_consumption': ['mean', 'sum', 'std', 'count']
    }).round(2)
    
    customer_stats.columns = ['mean_consumption', 'total_consumption', 
                            'consumption_std', 'n_records']
    customer_stats = customer_stats.reset_index()
    
    # Добавляем сезонность
    df['month'] = df['date_parsed'].dt.month
    monthly_avg = df.groupby(['subscriber_id', 'month'])['gas_consumption'].mean().unstack()
    seasonality = (monthly_avg.max(axis=1) - monthly_avg.min(axis=1)) / monthly_avg.mean(axis=1)
    customer_stats['seasonality'] = seasonality.fillna(0).values
    
    return customer_stats

def perform_clustering(customer_stats, features, algorithm, n_clusters):
    """Выполнение кластеризации"""
    # Выбор признаков
    X = customer_stats[features].fillna(0)
    
    # Масштабирование
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Кластеризация
    if algorithm == "K-means":
        model = KMeans(n_clusters=n_clusters, random_state=42)
    else:
        model = AgglomerativeClustering(n_clusters=n_clusters)
    
    labels = model.fit_predict(X_scaled)
    customer_stats['cluster'] = labels
    
    return customer_stats

def display_clustering_results(customer_stats, n_clusters):
    """Отображение результатов кластеризации"""
    # 1. Статистика по кластерам
    st.subheader("📊 Результаты кластеризации")
    
    cluster_stats = customer_stats.groupby('cluster').agg({
        'subscriber_id': 'count',
        'mean_consumption': 'mean',
        'total_consumption': 'mean',
        'seasonality': 'mean'
    }).round(2)
    
    cluster_stats.columns = ['Количество абонентов', 'Среднее потребление', 
                           'Суммарное потребление', 'Сезонность']
    
    st.dataframe(cluster_stats)
    
    # 2. Визуализация кластеров
    fig_clusters = create_cluster_scatter(customer_stats)
    st.plotly_chart(fig_clusters, use_container_width=True)
    
    # 3. Типовые профили нагрузки
    st.subheader("📈 Типовые профили нагрузки по кластерам")
    profiles_fig = create_cluster_profiles(customer_stats, n_clusters)
    st.plotly_chart(profiles_fig, use_container_width=True)

def display_export_section(customer_stats, n_clusters):
    """Отображение секции экспорта"""
    st.subheader("📤 Экспорт данных")
    
    export_col1, export_col2 = st.columns(2)
    with export_col1:
        if st.button("📄 Экспорт кластеров в CSV", key="export_clusters_csv"):
            csv = customer_stats.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="кластеры_абонентов.csv">Скачать CSV</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with export_col2:
        cluster_to_export = st.selectbox("Выберите кластер для экспорта", range(n_clusters), key="select_cluster_export")
        cluster_customers = customer_stats[customer_stats['cluster'] == cluster_to_export]
        csv_cluster = cluster_customers.to_csv(index=False)
        b64_cluster = base64.b64encode(csv_cluster.encode()).decode()
        href_cluster = f'<a href="data:file/csv;base64,{b64_cluster}" download="кластер_{cluster_to_export}.csv">Скачать кластер {cluster_to_export}</a>'
        st.markdown(href_cluster, unsafe_allow_html=True)