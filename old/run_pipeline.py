
import logging
import pandas as pd
from download_normalize import main as load_and_normalize_data
from machine_learning import main as run_ml_pipeline

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_full_pipeline():
    """
    Запускает полный пайплайн: загрузка → нормализация → ML
    """
    logger.info("=" * 60)
    logger.info("ЗАПУСК ПОЛНОГО ПАЙПЛАЙНА")
    logger.info("=" * 60)
    
    # Шаг 1: Загрузка и нормализация данных
    logger.info("\n1. ЗАГРУЗКА И НОРМАЛИЗАЦИЯ ДАННЫХ")
    logger.info("-" * 40)
    
    df_normalized = load_and_normalize_data()
    
    if df_normalized is None:
        logger.error("Не удалось загрузить и нормализовать данные!")
        return
    
    # Шаг 2: ML пайплайн
    logger.info("\n2. ЗАПУСК ML ПАЙПЛАЙНА")
    logger.info("-" * 40)
    
    try:
        model, df_ml = run_ml_pipeline(df_normalized)
        logger.info("\n✓ Пайплайн успешно завершен!")
        
        # Дополнительная информация
        logger.info(f"\nИтоговая информация:")
        logger.info(f"  - Оригинальных записей: {len(df_normalized)}")
        logger.info(f"  - ML признаков: {len(df_ml.columns)}")
        logger.info(f"  - Данные сохранены в:")
        logger.info(f"      second_version/data/processed/normalized_data.csv")
        logger.info(f"      second_version/data/processed/ml_features.csv")
        
    except Exception as e:
        logger.error(f"Ошибка в ML пайплайне: {e}")

if __name__ == "__main__":
    run_full_pipeline()