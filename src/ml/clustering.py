import numpy as np
import polars as pl  # Добавьте эту строку
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import plotly.express as px
import pandas as pd

class GasConsumerClustering:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        
    def prepare_features(self, customer_features):
        """Подготовка признаков для кластеризации"""
        # Получаем список всех числовых колонок
        numeric_columns = [
            col for col in customer_features.columns 
            if customer_features[col].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]
            and col not in ['subscriber_id']  # Исключаем нечисловые
        ]
        
        # Проверяем наличие стандартных признаков
        available_features = []
        feature_options = ['mean_consumption', 'std_consumption', 'cv_consumption',
                          'seasonality_ratio', 'observation_days', 'n_records']
        
        for feature in feature_options:
            if feature in customer_features.columns:
                available_features.append(feature)
        
        if not available_features:
            # Если нет стандартных признаков, используем все числовые
            available_features = numeric_columns[:5]  # Берем первые 5
        
        # Выбираем доступные признаки
        features_df = customer_features.select(available_features).to_pandas()
        
        # Заполняем NaN средними значениями
        features_df = features_df.fillna(features_df.mean())
        
        # Заполняем оставшиеся NaN нулями
        features_df = features_df.fillna(0)
        
        # Масштабируем
        X_scaled = self.scaler.fit_transform(features_df)
        
        return X_scaled, features_df, available_features
    
    def kmeans_clustering(self, X, n_clusters=5):
        """Кластеризация K-Means"""
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10
        )
        
        labels = kmeans.fit_predict(X)
        
        # Метрики (только если есть больше 1 кластера)
        if len(set(labels)) > 1:
            silhouette = silhouette_score(X, labels)
        else:
            silhouette = 0
        
        metrics = {
            'inertia': kmeans.inertia_,
            'silhouette': silhouette,
            'n_clusters': n_clusters
        }
        
        return labels, metrics, kmeans
    
    def visualize_clusters(self, X, labels, title="Кластеризация потребителей"):
        """Визуализация кластеров с помощью PCA"""
        # Уменьшение размерности
        pca = PCA(n_components=2, random_state=self.random_state)
        X_pca = pca.fit_transform(X)
        
        # Создание DataFrame для визуализации
        viz_df = pd.DataFrame({
            'PC1': X_pca[:, 0],
            'PC2': X_pca[:, 1],
            'cluster': labels.astype(str)
        })
        
        # Процент объясненной дисперсии
        explained_var = pca.explained_variance_ratio_
        
        fig = px.scatter(
            viz_df, x='PC1', y='PC2', color='cluster',
            title=f"{title} (Объяснено: {explained_var[0]:.1%} + {explained_var[1]:.1%})",
            labels={'PC1': f'PC1 ({explained_var[0]:.1%})', 
                   'PC2': f'PC2 ({explained_var[1]:.1%})'},
            hover_data=['cluster']
        )
        
        fig.update_layout(
            width=800, 
            height=600,
            legend_title_text='Кластер'
        )
        
        return fig
    
    def get_cluster_statistics(self, customer_features, labels):
        """Получение статистики по кластерам"""
        # Добавляем метки кластеров
        clustered_df = customer_features.with_columns(
            pl.Series("cluster", labels)
        )
        
        # Вычисляем статистику по кластерам
        # Проверяем наличие колонок
        agg_exprs = [
            pl.count().alias("n_абонентов")
        ]
        
        # Добавляем доступные колонки
        for col in ['mean_consumption', 'seasonality_ratio', 'cv_consumption', 'n_records']:
            if col in clustered_df.columns:
                agg_exprs.append(pl.col(col).mean().alias(f"avg_{col}"))
        
        cluster_stats = clustered_df.group_by("cluster").agg(agg_exprs).sort("cluster")
        
        return cluster_stats