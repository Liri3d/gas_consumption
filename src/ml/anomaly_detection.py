import polars as pl
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from prophet import Prophet
import plotly.graph_objects as go
from typing import Dict, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

class AnomalyDetector:
    def __init__(self, contamination: float = 0.01, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.iso_forest = None
        self.scaler = StandardScaler()
        
    def isolation_forest_anomalies(self, customer_features: pl.DataFrame) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Обнаружение аномалий с помощью Isolation Forest"""
        # Подготовка признаков
        feature_cols = [
            'mean_consumption', 'std_consumption', 'cv_consumption',
            'seasonality_ratio'
        ]
        
        existing_cols = [col for col in feature_cols 
                        if col in customer_features.columns]
        
        features_df = customer_features.select(existing_cols)
        X = features_df.to_numpy()
        
        # Масштабирование
        X_scaled = self.scaler.fit_transform(X)
        
        # Обучение Isolation Forest
        self.iso_forest = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        
        predictions = self.iso_forest.fit_predict(X_scaled)
        # Преобразование: 1 = норма, -1 = аномалия
        anomalies = (predictions == -1).astype(int)
        
        # Статистика
        n_anomalies = sum(anomalies)
        total = len(anomalies)
        
        metrics = {
            'n_anomalies': n_anomalies,
            'anomaly_rate': n_anomalies / total * 100,
            'decision_function': self.iso_forest.decision_function(X_scaled)
        }
        
        return anomalies, metrics
    
    def prophet_anomalies(self, time_series: pl.DataFrame, 
                         customer_id: str) -> Tuple[pl.DataFrame, Dict[str, Any]]:
        """Обнаружение аномалий во временном ряду с помощью Prophet"""
        # Подготовка данных для Prophet
        prophet_data = time_series.filter(
            pl.col("subscriber_id") == customer_id
        ).select([
            pl.col("date_normalized").alias("ds"),
            pl.col("gas_consumption").alias("y")
        ]).to_pandas()
        
        # Модель Prophet
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode='multiplicative'
        )
        
        model.fit(prophet_data)
        
        # Прогноз
        future = model.make_future_dataframe(periods=0)
        forecast = model.predict(future)
        
        # Объединение с фактическими значениями
        merged = forecast.merge(prophet_data, on='ds', how='left')
        
        # Вычисление остатков
        merged['residual'] = merged['y'] - merged['yhat']
        merged['residual_std'] = merged['residual'].std()
        
        # Определение аномалий (3 сигмы)
        merged['is_anomaly'] = (
            (merged['residual'].abs() > 3 * merged['residual_std']).astype(int)
        )
        
        # Обратно в polars
        result_df = pl.from_pandas(merged)
        
        metrics = {
            'n_anomalies': merged['is_anomaly'].sum(),
            'total_points': len(merged),
            'anomaly_rate': merged['is_anomaly'].sum() / len(merged) * 100,
            'model_params': {
                'seasonalities': model.seasonalities,
                'changepoints': len(model.changepoints)
            }
        }
        
        return result_df, metrics
    
    def visualize_anomalies(self, time_series: pl.DataFrame, 
                          prophet_results: pl.DataFrame = None,
                          customer_id: str = None) -> go.Figure:
        """Визуализация аномалий"""
        if customer_id:
            customer_data = time_series.filter(
                pl.col("subscriber_id") == customer_id
            )
        else:
            customer_data = time_series
        
        fig = go.Figure()
        
        # Фактические значения
        fig.add_trace(go.Scatter(
            x=customer_data["date_normalized"].to_numpy(),
            y=customer_data["gas_consumption"].to_numpy(),
            mode='lines+markers',
            name='Фактическое потребление',
            line=dict(color='blue', width=2),
            marker=dict(size=4)
        ))
        
        # Если есть прогноз Prophet
        if prophet_results is not None:
            fig.add_trace(go.Scatter(
                x=prophet_results["ds"].to_numpy(),
                y=prophet_results["yhat"].to_numpy(),
                mode='lines',
                name='Прогноз Prophet',
                line=dict(color='green', width=2, dash='dash')
            ))
            
            # Верхняя и нижняя границы
            fig.add_trace(go.Scatter(
                x=prophet_results["ds"].to_numpy(),
                y=prophet_results["yhat_upper"].to_numpy(),
                mode='lines',
                name='Верхняя граница',
                line=dict(color='gray', width=1),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=prophet_results["ds"].to_numpy(),
                y=prophet_results["yhat_lower"].to_numpy(),
                mode='lines',
                name='Нижняя граница',
                fill='tonexty',
                fillcolor='rgba(128, 128, 128, 0.2)',
                line=dict(color='gray', width=1),
                showlegend=False
            ))
            
            # Аномалии
            anomalies = prophet_results.filter(pl.col("is_anomaly") == 1)
            if anomalies.height > 0:
                fig.add_trace(go.Scatter(
                    x=anomalies["ds"].to_numpy(),
                    y=anomalies["y"].to_numpy(),
                    mode='markers',
                    name='Аномалии',
                    marker=dict(
                        color='red',
                        size=10,
                        symbol='x'
                    )
                ))
        
        fig.update_layout(
            title=f'Потребление газа и обнаруженные аномалии' + 
                  (f' (Абонент: {customer_id})' if customer_id else ''),
            xaxis_title='Дата',
            yaxis_title='Потребление газа (м³)',
            hovermode='x unified',
            width=1000,
            height=600,
            showlegend=True
        )
        
        return fig