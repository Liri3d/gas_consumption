
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def visualize_dataset(df):
    """
    Визуализация данных - адаптирована под новый формат
    """
    plt.figure(figsize=(15, 10))

    # 1. Потребление по месяцам и сезонам
    plt.subplot(2, 2, 1)
    
    # Создаем цветовую карту для сезонов
    season_colors = {
        'winter': 'blue',
        'spring': 'green', 
        'summer': 'yellow',
        'autumn': 'orange'
    }
    
    for season in df['season'].unique():
        season_data = df[df['season'] == season]
        plt.scatter(season_data['date'], season_data['gas_consumption'], 
                   color=season_colors.get(season, 'gray'),
                   label=season, alpha=0.7, s=60)
    
    plt.title('Потребление газа по месяцам и сезонам')
    plt.xlabel('Дата')
    plt.ylabel('Потребление газа (м^3)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)

    # 2. Распределение по сезонам (боксплот)
    plt.subplot(2, 2, 2)
    season_data = [
        df[df['season'] == 'winter']['gas_consumption'],
        df[df['season'] == 'spring']['gas_consumption'],
        df[df['season'] == 'summer']['gas_consumption'],
        df[df['season'] == 'autumn']['gas_consumption']
    ]
    
    plt.boxplot(season_data, labels=['Зима', 'Весна', 'Лето', 'Осень'])
    plt.title('Распределение потребления по сезонам')
    plt.ylabel('Потребление газа (м^3)')
    plt.grid(True, alpha=0.3)

    # 3. Отопительный и неотопительный сезон
    plt.subplot(2, 2, 3)
    heating_avg = df.groupby('heating_season')['gas_consumption'].mean()
    
    # Создаем DataFrame для барплота
    heating_df = pd.DataFrame({
        'Тип сезона': ['Неотопительный', 'Отопительный'],
        'Среднее потребление': [heating_avg.get(0, 0), heating_avg.get(1, 0)]
    })
    
    colors = ['blue', 'red'] if 1 in heating_avg.index else ['blue']
    plt.bar(heating_df['Тип сезона'], heating_df['Среднее потребление'], color=colors)
    plt.title('Среднее потребление по типам сезона')
    plt.xlabel('Тип сезона')
    plt.ylabel('Среднее потребление газа (м^3)')
    plt.grid(True, alpha=0.3)

    # 4. Среднее потребление по месяцам
    plt.subplot(2, 2, 4)
    monthly_avg = df.groupby('month_name')['gas_consumption'].mean()
    
    # Порядок месяцев
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Переиндексируем по порядку месяцев
    monthly_avg = monthly_avg.reindex([m for m in month_order if m in monthly_avg.index])
    
    # Цвета для месяцев
    colors = plt.cm.tab20c(np.linspace(0, 1, len(monthly_avg)))
    monthly_avg.plot(kind='bar', color=colors)
    plt.title('Среднее потребление по месяцам года')
    plt.xlabel('Месяц')
    plt.ylabel('Среднее потребление (м^3)')
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
    
    # Статистика
    print(f"{'='*40} СТАТИСТИКА {'='*40}\n")
    
    # Статистика по сезонам
    for season in ['winter', 'spring', 'summer', 'autumn']:
        if season in df['season'].unique():
            season_data = df[df['season'] == season]
            print(f"{season.capitalize()}:")
            print(f"  Количество месяцев: {len(season_data)}")
            print(f"  Среднее потребление: {season_data['gas_consumption'].mean():.1f} м^3")
            print(f"  Мин/Макс: {season_data['gas_consumption'].min():.1f} - {season_data['gas_consumption'].max():.1f} м^3")
            print()

    # Статистика по отопительному сезону
    if 'heating_season' in df.columns:
        heating_data = df[df['heating_season'] == 1]
        non_heating_data = df[df['heating_season'] == 0]
        
        if len(heating_data) > 0 and len(non_heating_data) > 0:
            print(f"Отопительный сезон:")
            print(f"  Месяцев: {len(heating_data)}")
            print(f"  Среднее потребление: {heating_data['gas_consumption'].mean():.1f} м^3")
            print(f"\nНеотопительный сезон:")
            print(f"  Месяцев: {len(non_heating_data)}")
            print(f"  Среднее потребление: {non_heating_data['gas_consumption'].mean():.1f} м^3")
            
            if non_heating_data['gas_consumption'].mean() > 0:
                ratio = heating_data['gas_consumption'].mean() / non_heating_data['gas_consumption'].mean()
                print(f"\nКоэффициент сезонности: {ratio:.2f}")
    
    print(f"\n{'='*80}")

def prepare_ml_features(df):
    """
    Подготовка признаков для ML - адаптирована под новый формат
    """
    df_ml = df.copy()
    
    # Убедимся, что дата в правильном формате
    if not pd.api.types.is_datetime64_any_dtype(df_ml['date']):
        df_ml['date'] = pd.to_datetime(df_ml['date'])
    
    # Базовые временные признаки
    df_ml['month'] = df_ml['date'].dt.month
    df_ml['year'] = df_ml['date'].dt.year
    df_ml['day'] = df_ml['date'].dt.day
    
    # Лаги потребления
    for lag in [1, 2, 3, 12]:
        df_ml[f'consumption_lag_{lag}'] = df_ml['gas_consumption'].shift(lag)
    
    # Скользящие средние
    df_ml['consumption_rolling_mean_3'] = df_ml['gas_consumption'].rolling(window=3, min_periods=1).mean()
    df_ml['consumption_rolling_mean_12'] = df_ml['gas_consumption'].rolling(window=12, min_periods=1).mean()
    
    # Циклические признаки месяцев
    df_ml['month_sin'] = np.sin(2 * np.pi * df_ml['month'] / 12)
    df_ml['month_cos'] = np.cos(2 * np.pi * df_ml['month'] / 12)
    
    # Признаки сезонов (бинарные)
    if 'season' in df_ml.columns:
        df_ml['is_winter'] = (df_ml['season'] == 'winter').astype(int)
        df_ml['is_spring'] = (df_ml['season'] == 'spring').astype(int)
        df_ml['is_summer'] = (df_ml['season'] == 'summer').astype(int)
        df_ml['is_autumn'] = (df_ml['season'] == 'autumn').astype(int)
    
    # Дополнительные признаки
    df_ml['day_of_year'] = df_ml['date'].dt.dayofyear
    df_ml['quarter'] = df_ml['date'].dt.quarter
    
    # Удаляем нечисловые и временные колонки
    columns_to_drop = ['date', 'management', 'source', 'subscriber_id', 'md_id']
    
    # Удаляем только существующие колонки
    existing_columns = [col for col in columns_to_drop if col in df_ml.columns]
    df_ml = df_ml.drop(existing_columns, axis=1)
    
    # Удаляем текстовые колонки сезонов
    if 'season' in df_ml.columns:
        df_ml = df_ml.drop('season', axis=1)
    if 'month_name' in df_ml.columns:
        df_ml = df_ml.drop('month_name', axis=1)
    
    # Удаляем строки с пропущенными значениями
    df_ml = df_ml.dropna()
    
    logger.info(f"Признаки подготовлены. Колонок: {len(df_ml.columns)}")
    logger.info(f"Колонки: {list(df_ml.columns)}")
    
    return df_ml

def test_catboost_monthly(df_ml, original_df):
    """
    Тестирование модели CatBoost
    """
    # Определяем признаки и целевую переменную
    feature_columns = [col for col in df_ml.columns if col != 'gas_consumption']
    X = df_ml[feature_columns]
    y = df_ml['gas_consumption']
    
    # Разделяем на train/test
    split_idx = int(len(X) * 0.7)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info(f"Размер данных: {X.shape}")
    logger.info(f"Обучающая выборка: {X_train.shape}")
    logger.info(f"Тестовая выборка: {X_test.shape}")
    
    # Создаем и обучаем модель
    model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.1,
        depth=6,
        random_seed=42,
        verbose=100,
        loss_function='RMSE'
    )
    
    model.fit(X_train, y_train, eval_set=(X_test, y_test), verbose=100)
    
    # Прогноз
    y_pred = model.predict(X_test)
    
    # Метрики
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    print(f"\n{'='*60}")
    print("РЕЗУЛЬТАТЫ МОДЕЛИ CATBOOST")
    print(f"{'='*60}")
    print(f"MAE: {mae:.2f} м^3")
    print(f"RMSE: {rmse:.2f} м^3")
    print(f"Среднее потребление в тестовой выборке: {y_test.mean():.2f} м^3")
    print(f"Относительная ошибка (RMSE/mean): {rmse/y_test.mean()*100:.1f}%")
    
    # Важность признаков
    feature_importance = model.get_feature_importance()
    feature_names = X.columns
    
    plt.figure(figsize=(12, 8))
    indices = np.argsort(feature_importance)
    plt.barh(range(len(indices)), feature_importance[indices], color='steelblue')
    plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
    plt.title('Важность признаков в CatBoost модели', fontsize=14, fontweight='bold')
    plt.xlabel('Важность признака', fontsize=12)
    plt.tight_layout()
    plt.show()
    
    # Визуализация прогнозов
    plt.figure(figsize=(14, 7))
    
    # Получаем даты для тестовой выборки
    dates_test = original_df['date'].iloc[split_idx:split_idx+len(y_test)].reset_index(drop=True)
    
    plt.plot(dates_test, y_test.values, label='Фактические значения', 
             marker='o', linewidth=2, markersize=6, color='blue')
    plt.plot(dates_test, y_pred, label='Прогноз CatBoost', 
             marker='s', linewidth=2, markersize=6, color='red', linestyle='--')
    
    plt.title('Прогноз месячного потребления газа - CatBoost', fontsize=14, fontweight='bold')
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel('Потребление газа (м^3)', fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    
    return model, X, y

def main(df):
    """
    Основная функция ML пайплайна
    """
    logger.info("Запуск ML пайплайна...")
    
    # 1. Визуализация данных
    logger.info("Визуализация данных...")
    visualize_dataset(df)
    
    # 2. Подготовка признаков
    logger.info("Подготовка признаков для ML...")
    df_ml = prepare_ml_features(df)
    
    # Сохраняем признаки
    os.makedirs('second_version/data/processed', exist_ok=True)
    df_ml.to_csv('second_version/data/processed/ml_features.csv', index=False, encoding='utf-8')
    logger.info("Признаки сохранены в second_version/data/processed/ml_features.csv")
    
    # 3. Обучение и тестирование модели
    logger.info("Обучение модели CatBoost...")
    model, X, y = test_catboost_monthly(df_ml, df)
    
    logger.info("ML пайплайн завершен!")
    return model, df_ml

# if __name__ == "__main__":
#     # Для тестирования загрузим данные
#     try:
#         df = pd.read_csv(
#             'E:/magistr/KursProj/second_version/data/processed/normalized_data.csv',
#             parse_dates=['date'],
#             encoding='utf-8'
#         )
#         main(df)
#     except Exception as e:
#         logger.error(f"Ошибка при запуске ML: {e}")