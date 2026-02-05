
import logging
import pandas as pd
from datetime import datetime
import locale
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_or_normalize_data():
    """
    Проверяет наличие нормализованного файла и загружает его,
    если нет - создает из сырых данных
    """
    # Пути к файлам
    raw_file = 'E:/magistr/KursProj/second_version/data/raw/АУГГ.csv'
    normalized_file = 'second_version/data/processed/normalized_data.csv'
    
    # 1. Проверяем есть ли уже нормализованный файл
    if os.path.exists(normalized_file):
        print(f"✓ Нормализованный файл найден: {normalized_file}")
        df = pd.read_csv(normalized_file, parse_dates=['date'], encoding='utf-8')
        print(f"  Загружено {len(df)} строк")
        return df
    
    # 2. Если нет - создаем из сырых данных
    print("Нормализованный файл не найден, создаем...")
    
    # Загружаем сырые данные
    df = pd.read_csv(
        raw_file,
        sep=';',
        quotechar='"',
        encoding='utf-8',
        header=None,
        names=["management", "subscriber_id", "md_id", "date", "gas_consumption", "source"]
    )
    
    normalized_df = normalize_data(df)

    
    
    # Создаем директорию если нет
    os.makedirs(os.path.dirname(normalized_file), exist_ok=True)
    
    # Сохраняем
    normalized_df.to_csv(normalized_file, index=False, encoding='utf-8')
    print(f"✓ Нормализованный файл сохранен: {normalized_file}")
    
    return df

def normalize_data(df):
    """Нормализует данные в формат для ML"""
    df_normalized = df.copy()
    
    # Преобразуем дату
    df_normalized['date'] = pd.to_datetime(df_normalized['date'], format='%d.%m.%Y')
    
    # Преобразуем числовые колонки
    df_normalized['gas_consumption'] = pd.to_numeric(df_normalized['gas_consumption'], errors='coerce')
    df_normalized['md_id'] = pd.to_numeric(df_normalized['md_id'], errors='coerce')
    df_normalized['subscriber_id'] = df_normalized['subscriber_id'].astype(str)
    
    # Добавляем сезонность
    def get_season(month):
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    df_normalized['month'] = df_normalized['date'].dt.month
    df_normalized['year'] = df_normalized['date'].dt.year
    df_normalized['season'] = df_normalized['month'].apply(get_season)
    
    # Отопительный сезон
    df_normalized['heating_season'] = df_normalized['month'].apply(
        lambda x: 1 if x in [10, 11, 12, 1, 2, 3, 4] else 0
    )
    
    # Название месяца на английском
    df_normalized['month_name'] = df_normalized['date'].dt.strftime('%B')
  
    # Сортируем по дате
    df_normalized = df_normalized.sort_values('date')
    
    return df_normalized

def main():
    try:
        logger.info("Загрузка данных...")

        # df = pd.read_csv('E:/magistr/KursProj/second_version/data/raw/АУГГ.csv', sep=';', quotechar='"', encoding='utf-8', names=["management", "subscriber_id", "md_id", "date", "gas_consumption", "source"])
        # df.to_csv('second_version/data/processed/start_df.csv', index=False, encoding='utf-8')
        
        # Загружаем данные (создаст если нет)
        df = load_or_normalize_data()

        logger.info(f"Загружено строк: {len(df)}")
        logger.info(f"Колонки: {list(df.columns)}")
        logger.info(f"Диапазон дат: {df['date'].min()} - {df['date'].max()}")

        return df
        
    except Exception as e:
        logger.error(f'Ошибка: {e}', exc_info=True)
        return None
        
if __name__ == "__main__":
    main()