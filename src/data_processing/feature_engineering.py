import polars as pl

class FeatureEngineer:
    @staticmethod
    def create_customer_features(df: pl.DataFrame) -> pl.DataFrame:
        """Создание признаков на уровне абонента"""
        # Сначала собираем все агрегации, кроме тех, что зависят от других
        customer_features = df.group_by("subscriber_id").agg([
            pl.col("gas_consumption").mean().alias("mean_consumption"),
            pl.col("gas_consumption").std().alias("std_consumption"),
            pl.col("gas_consumption").max().alias("max_consumption"),
            pl.col("gas_consumption").min().alias("min_consumption"),
            pl.col("gas_consumption").median().alias("median_consumption"),
            
            # Коэффициент вариации
            (pl.col("gas_consumption").std() / pl.col("gas_consumption").mean())
            .alias("cv_consumption"),
            
            # Количество записей
            pl.count().alias("n_records"),
            
            # Период наблюдения
            (pl.col("date_norm").max() - pl.col("date_norm").min())
            .dt.total_days()
            .alias("observation_days"),
            
            # Среднее по сезонам - отдельные выражения
            pl.col("gas_consumption")
            .filter(pl.col("season") == "winter")
            .mean()
            .alias("winter_mean"),
            
            pl.col("gas_consumption")
            .filter(pl.col("season") == "summer")
            .mean()
            .alias("summer_mean"),
        ])
        
        # Теперь вычисляем производные признаки
        customer_features = customer_features.with_columns([
            # Отношение зимнее/летнее (защита от деления на 0)
            pl.when(pl.col("summer_mean") > 0)
                .then(pl.col("winter_mean") / pl.col("summer_mean"))
                .otherwise(pl.lit(1.0))
                .alias("seasonality_ratio"),
            
            # Заполняем NaN значения
            pl.col("winter_mean").fill_nan(0),
            pl.col("summer_mean").fill_nan(0),
            pl.col("seasonality_ratio").fill_nan(1.0),
        ])
        
        # Добавляем категорию сезонности
        customer_features = customer_features.with_columns([
            # Категория сезонности
            pl.when(pl.col("seasonality_ratio") > 2.0)
                .then(pl.lit("high"))
                .when(pl.col("seasonality_ratio") > 1.5)
                .then(pl.lit("medium"))
                .otherwise(pl.lit("low"))
                .alias("seasonality_category"),
            
            # Заполняем пропуски в других колонках
            pl.col("cv_consumption").fill_nan(0),
            pl.col("std_consumption").fill_nan(0),
        ])
        
        return customer_features