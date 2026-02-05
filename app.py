# import streamlit as st
# from modules import db_loader, overview, clustering, anomalies, forecasting, reports, config

# # Настройка страницы
# st.set_page_config(
#     page_title="Система анализа потребления ТЭР",
#     layout="wide",
#     page_icon="⛽"
# )

# st.title("⛽ Интеллектуальная система анализа потребления газа")
# st.markdown("---")

# # Инициализация состояния сессии
# config.init_session_state()

# # Боковая панель - загрузка данных
# st.sidebar.header("⚙️ Настройки системы")
# db_loader.render_sidebar()

# # Основное содержимое
# if st.session_state.df is not None:
#     df = st.session_state.df
    
#     # Создание вкладок
#     tab1, tab2, tab4, tab6 = st.tabs([ # tab3, tab5,
#         "📊 Обзор данных (US-VIE-01)",
#         "🔍 Кластеризация (US-ANL-01)", 
#         # "⚠️ Аномалии (US-ANL-02)",
#         "📈 Прогноз (US-ANL-03)",
#         # "📋 Отчеты (US-VIE-02)",
#         "⚙️ Настройки"
#     ])
    
#     with tab1:
#         overview.render(df)
    
#     with tab2:
#         clustering.render(df)
    
#     # with tab3:
#     #     anomalies.render(df)
    
#     with tab4:
#         forecasting.render(df)
    
#     # with tab5:
#     #     reports.render(df)
    
#     with tab6:
#         config.render_settings(df)

# else:
#     # Экран загрузки данных
#     config.render_welcome_screen()

# st.markdown("---")
# st.caption("Система анализа потребления газа | Прототип | Реализованы все UC/US требования")







import streamlit as st
from modules import db_loader, overview, clustering, anomalies, forecasting, reports, config
import time
from datetime import datetime

# Настройка страницы
st.set_page_config(
    page_title="Система анализа потребления ТЭР",
    layout="wide",
    page_icon="⛽"
)

st.title("⛽ Интеллектуальная система анализа потребления газа")
st.markdown("---")

# Инициализация состояния сессии
config.init_session_state()

# Боковая панель - загрузка данных из БД
st.sidebar.header("⚙️ Настройки системы")
filters = db_loader.render_sidebar()

# Автообновление данных
if filters.get('auto_refresh', False):
    if 'last_update' not in st.session_state:
        st.session_state.last_update = datetime.now()
    
    # Проверяем, прошло ли 30 минут с последнего обновления
    time_since_update = (datetime.now() - st.session_state.last_update).seconds
    if time_since_update > 1800:  # 30 минут
        if st.session_state.df is not None:
            with st.sidebar.spinner("🔄 Автообновление данных..."):
                db_loader.load_data_from_db(
                    days_back=filters['days_back'],
                    limit_rows=filters['limit_rows']
                )

# Основное содержимое
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Информация о загруженных данных
    if 'data_meta' in st.session_state:
        meta = st.session_state.data_meta
        st.sidebar.info(f"""
        **📊 Данные загружены:**
        - Записей: {meta['total_records']:,}
        - Абонентов: {meta['unique_subscribers']:,}
        - Управлений: {meta['unique_managements']:,}
        - Период: {meta['date_range']['min'].strftime('%d.%m.%Y')} - {meta['date_range']['max'].strftime('%d.%m.%Y')}
        - Обновлено: {meta['loaded_at'].strftime('%H:%M:%S')}
        """)
    
    # Создание вкладок
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Обзор данных (US-VIE-01)",
        "🔍 Кластеризация (US-ANL-01)",
        "⚠️ Аномалии (US-ANL-02)",
        "📈 Прогноз (US-ANL-03)",
        "📋 Отчеты (US-VIE-02)",
        "⚙️ Настройки"
    ])
    
    with tab1:
        overview.render(df)
    
    with tab2:
        clustering.render(df)
    
    with tab3:
        anomalies.render(df)
    
    with tab4:
        forecasting.render(df)
    
    with tab5:
        reports.render(df)
    
    with tab6:
        config.render_settings(df)

else:
    # Экран загрузки данных
    config.render_welcome_screen()
    
    # Информация о подключении к БД
    st.sidebar.info("""
    **🔗 Настройки БД:**
    Для подключения к PostgreSQL необходимо настроить переменные окружения в файле `.env`:
    ```
    DB_HOST=localhost
    DB_NAME=gas_consumption
    DB_USER=postgres
    DB_PASSWORD=your_password
    DB_PORT=5432
    ```
    """)

st.markdown("---")
st.caption("Система анализа потребления газа | PostgreSQL версия | Реализованы все UC/US требования")

# Кнопка принудительного обновления данных
if st.session_state.df is not None:
    if st.sidebar.button("🔄 Обновить данные", key="force_refresh"):
        with st.spinner("Обновление данных..."):
            db_loader.load_data_from_db(
                days_back=filters['days_back'],
                limit_rows=filters['limit_rows']
            )
            st.rerun()