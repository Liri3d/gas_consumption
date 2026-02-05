# # modules/data_loader.py
# import streamlit as st
# import pandas as pd
# import numpy as np

# def render_sidebar():
#     """Рендеринг боковой панели для загрузки данных"""
#     st.sidebar.subheader("📥 Импорт данных (UC-DAT-01)")
    
#     uploaded_file = st.sidebar.file_uploader(
#         "Загрузите CSV файл с показаниями ПУ", 
#         type="csv",
#         help="Формат: разделитель ';', кодировка UTF-8"
#     )
    
#     if uploaded_file is not None:
#         load_data(uploaded_file)

# def load_data(uploaded_file):
#     """Загрузка и обработка данных из CSV файла"""
#     try:
#         # Загрузка данных
#         df = pd.read_csv(
#             uploaded_file, 
#             sep=';', 
#             quotechar='"',
#             encoding='utf-8',
#             header=None,
#             names=["management", "subscriber_id", "md_id", "date", "gas_consumption", "source"]
#         )
        
#         # Валидация данных
#         original_rows = len(df)
        
#         # Проверка дубликатов
#         duplicates = df.duplicated().sum()
#         if duplicates > 0:
#             st.sidebar.warning(f"Найдено {duplicates} дубликатов. Будут удалены.")
#             df = df.drop_duplicates()
        
#         # Проверка пропусков
#         missing_values = df.isnull().sum().sum()
#         if missing_values > 0:
#             st.sidebar.warning(f"Найдено {missing_values} пропущенных значений.")
        
#         # Преобразование данных
#         df['date_parsed'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')
#         df['gas_consumption'] = pd.to_numeric(df['gas_consumption'], errors='coerce')
        
#         # Удаление некорректных данных
#         df = df.dropna(subset=['date_parsed', 'gas_consumption'])
        
#         # Сохранение в session_state
#         st.session_state.df = df
#         st.session_state.processed = True
        
#         st.sidebar.success(f"✅ Данные загружены: {len(df):,} записей")
#         st.sidebar.info(f"📊 После обработки: {len(df):,} из {original_rows:,} записей")
        
#         return df
        
#     except Exception as e:
#         st.sidebar.error(f"❌ Ошибка загрузки: {str(e)}")
#         return None




# modules/db_loader.py
import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

def get_db_connection():
    """Создание подключения к PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "gas_consumption"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            port=os.getenv("DB_PORT", "5432")
        )
        return conn
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка подключения к БД: {str(e)}")
        return None

def render_sidebar():
    """Рендеринг боковой панели для загрузки данных из БД"""
    st.sidebar.subheader("📥 Загрузка данных из БД (UC-DAT-01)")
    
    # Кнопка загрузки данных
    if st.sidebar.button("🔄 Загрузить данные из БД", key="load_db_data"):
        load_data_from_db()
    
    # Параметры фильтрации
    st.sidebar.subheader("Фильтры данных")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        days_back = st.number_input(
            "Дней назад",
            min_value=1,
            max_value=365,
            value=30,
            help="Загрузить данные за последние N дней"
        )
    
    with col2:
        limit_rows = st.number_input(
            "Лимит строк",
            min_value=1000,
            max_value=1000000,
            value=100000,
            step=10000,
            help="Максимальное количество строк для загрузки"
        )
    
    # Дополнительные параметры
    auto_refresh = st.sidebar.checkbox(
        "Автообновление данных",
        value=False,
        help="Автоматически обновлять данные каждые 30 минут"
    )
    
    return {
        'days_back': days_back,
        'limit_rows': limit_rows,
        'auto_refresh': auto_refresh
    }

def load_data_from_db(days_back=30, limit_rows=100000):
    """Загрузка и обработка данных из PostgreSQL"""
    try:
        with st.spinner("📥 Загрузка данных из БД..."):
            conn = get_db_connection()
            if conn is None:
                return None
            
            # Рассчитываем дату начала
            start_date = datetime.now() - timedelta(days=days_back)
            
            # SQL запрос для загрузки данных
            query = """
            SELECT 
                management,
                subscriber_id,
                meter_id as md_id,
                reading_date as date,
                consumption as gas_consumption,
                data_source as source,
                created_at
            FROM gas_readings
            WHERE reading_date >= %s
            ORDER BY reading_date DESC
            LIMIT %s
            """
            
            # Выполняем запрос
            df = pd.read_sql_query(query, conn, params=(start_date, limit_rows))
            conn.close()
            
            if df.empty:
                st.sidebar.warning("⚠️ В БД нет данных за указанный период")
                return None
            
            # Валидация данных
            original_rows = len(df)
            
            # Проверка дубликатов
            duplicates = df.duplicated().sum()
            if duplicates > 0:
                st.sidebar.warning(f"Найдено {duplicates} дубликатов. Будут удалены.")
                df = df.drop_duplicates()
            
            # Проверка пропусков
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                st.sidebar.warning(f"Найдено {missing_values} пропущенных значений.")
            
            # Преобразование данных
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
            df['gas_consumption'] = pd.to_numeric(df['gas_consumption'], errors='coerce')
            
            # Удаление некорректных данных
            df = df.dropna(subset=['date_parsed', 'gas_consumption'])
            
            # Добавляем дополнительные поля
            df['year'] = df['date_parsed'].dt.year
            df['month'] = df['date_parsed'].dt.month
            df['day'] = df['date_parsed'].dt.day
            df['weekday'] = df['date_parsed'].dt.weekday
            
            # Сохранение в session_state
            st.session_state.df = df
            st.session_state.processed = True
            st.session_state.last_update = datetime.now()
            
            st.sidebar.success(f"✅ Данные загружены: {len(df):,} записей")
            st.sidebar.info(f"📊 После обработки: {len(df):,} из {original_rows:,} записей")
            
            # Сохраняем метаданные
            st.session_state.data_meta = {
                'loaded_at': datetime.now(),
                'total_records': len(df),
                'date_range': {
                    'min': df['date_parsed'].min(),
                    'max': df['date_parsed'].max()
                },
                'unique_subscribers': df['subscriber_id'].nunique(),
                'unique_managements': df['management'].nunique()
            }
            
            return df
            
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка загрузки из БД: {str(e)}")
        return None

def get_available_managements():
    """Получение списка доступных управлений из БД"""
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        
        query = "SELECT DISTINCT management FROM gas_readings ORDER BY management"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df['management'].tolist()
    except:
        return []

def get_subscriber_data(subscriber_id):
    """Получение данных по конкретному абоненту"""
    try:
        conn = get_db_connection()
        if conn is None:
            return None
        
        query = """
        SELECT * FROM gas_readings 
        WHERE subscriber_id = %s 
        ORDER BY reading_date DESC
        LIMIT 1000
        """
        
        df = pd.read_sql_query(query, conn, params=(subscriber_id,))
        conn.close()
        
        return df
    except Exception as e:
        st.error(f"Ошибка получения данных абонента: {str(e)}")
        return None

def save_analysis_results(results, analysis_type):
    """Сохранение результатов анализа в БД"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        
        # Создание таблицы для результатов анализа, если её нет
        create_table_query = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id SERIAL PRIMARY KEY,
            analysis_type VARCHAR(50),
            subscriber_id VARCHAR(50),
            cluster_id INTEGER,
            anomaly_score FLOAT,
            forecast_value FLOAT,
            confidence_interval JSON,
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
        """
        cursor.execute(create_table_query)
        
        # Здесь должна быть логика сохранения конкретных результатов
        # В зависимости от analysis_type
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        st.error(f"Ошибка сохранения результатов: {str(e)}")
        return False