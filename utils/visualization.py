# utils/visualization.py
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_consumption_chart(daily_data):
    """Создание графика потребления"""
    fig = px.line(
        daily_data,
        x='date_parsed',
        y='gas_consumption',
        title='Общее потребление газа по дням',
        labels={'date_parsed': 'Дата', 'gas_consumption': 'Потребление (м³)'}
    )
    return fig

def create_cluster_scatter(customer_stats):
    """Создание scatter plot для кластеров"""
    fig = px.scatter(
        customer_stats,
        x='mean_consumption',
        y='total_consumption',
        color='cluster',
        title='Кластеризация абонентов',
        hover_data=['subscriber_id', 'n_records'],
        labels={'mean_consumption': 'Среднее потребление', 
               'total_consumption': 'Суммарное потребление'}
    )
    return fig

def create_cluster_profiles(customer_stats, n_clusters):
    """Создание профилей нагрузки по кластерам"""
    # Создание типовых профилей
    cluster_profiles = []
    for cluster_id in range(n_clusters):
        cluster_customers = customer_stats[customer_stats['cluster'] == cluster_id]['subscriber_id']
        # Здесь нужен доступ к исходным данным df
        # Для демо создаем синтетические данные
        profile_df = pd.DataFrame({
            'Месяц': list(range(1, 13)),
            'Потребление': [1000 + cluster_id * 200 + i * 50 for i in range(12)],
            'Кластер': f'Кластер {cluster_id}'
        })
        cluster_profiles.append(profile_df)
    
    profiles_df = pd.concat(cluster_profiles)
    
    fig = px.line(
        profiles_df,
        x='Месяц',
        y='Потребление',
        color='Кластер',
        title='Типовые профили нагрузки по кластерам',
        markers=True
    )
    return fig
