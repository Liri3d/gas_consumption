import polars as pl
import numpy as np

class GasDataCleaner:
    @staticmethod
    def clean_data(df: pl.DataFrame) -> pl.DataFrame:
        """Основная функция очистки данных"""
        # Создаем копию
        df_clean = df.clone()
        
        # Преобразуем дату
        df_clean = df_clean.with_columns([
            pl.col("date")
            .str.strptime(pl.Date, format="%d.%m.%Y")
            .alias("date_norm")
        ])
        
        # Конвертируем потребление в число
        df_clean = df_clean.with_columns([
            pl.col("gas_consumption").cast(pl.Float64)
        ])
        
        # Удаляем отрицательные значения
        df_clean = df_clean.filter(pl.col("gas_consumption") > 0)
        
        # Добавляем сезонные признаки
        df_clean = df_clean.with_columns([
            pl.col("date_norm").dt.month().alias("month"),
            pl.col("date_norm").dt.year().alias("year"),
            pl.col("date_norm").dt.quarter().alias("quarter"),
            
            # Сезоны
            pl.when(pl.col("date_norm").dt.month().is_in([12, 1, 2]))
                .then(pl.lit("winter"))
            .when(pl.col("date_norm").dt.month().is_in([3, 4, 5]))
                .then(pl.lit("spring"))
            .when(pl.col("date_norm").dt.month().is_in([6, 7, 8]))
                .then(pl.lit("summer"))
            .otherwise(pl.lit("autumn"))
            .alias("season"),
            
            # Отопительный сезон
            pl.when(pl.col("date_norm").dt.month().is_in([10, 11, 12, 1, 2, 3, 4]))
                .then(1)
                .otherwise(0)
                .alias("heating_season")
        ])
        
        return df_clean