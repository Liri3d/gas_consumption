# modules/data_loader.py
import streamlit as st
import pandas as pd
import numpy as np

def render_sidebar():
    """Рендеринг боковой панели для загрузки данных"""
    st.sidebar.subheader("📥 Импорт данных (UC-DAT-01)")
    
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите CSV файл с показаниями ПУ", 
        type="csv",
        help="Формат: разделитель ';', кодировка UTF-8"
    )
    
    if uploaded_file is not None:
        load_data(uploaded_file)

def load_data(uploaded_file):
    """Загрузка и обработка данных из CSV файла"""
    try:
        # Загрузка данных
        df = pd.read_csv(
            uploaded_file, 
            sep=';', 
            quotechar='"',
            encoding='utf-8',
            header=None,
            names=["management", "subscriber_id", "md_id", "date", "gas_consumption", "source"]
        )
        
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
        df['date_parsed'] = pd.to_datetime(df['date'], format='%d.%m.%Y', errors='coerce')
        df['gas_consumption'] = pd.to_numeric(df['gas_consumption'], errors='coerce')
        
        # Удаление некорректных данных
        df = df.dropna(subset=['date_parsed', 'gas_consumption'])
        
        # Сохранение в session_state
        st.session_state.df = df
        st.session_state.processed = True
        
        st.sidebar.success(f"✅ Данные загружены: {len(df):,} записей")
        st.sidebar.info(f"📊 После обработки: {len(df):,} из {original_rows:,} записей")
        
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ Ошибка загрузки: {str(e)}")
        return None