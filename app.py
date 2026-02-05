import streamlit as st
from modules import data_loader, overview, clustering, anomalies, forecasting, reports, config

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

# Боковая панель - загрузка данных
st.sidebar.header("⚙️ Настройки системы")
data_loader.render_sidebar()

# Основное содержимое
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Создание вкладок
    tab1, tab2, tab4, tab6 = st.tabs([ # tab3, tab5,
        "📊 Обзор данных (US-VIE-01)",
        "🔍 Кластеризация (US-ANL-01)", 
        # "⚠️ Аномалии (US-ANL-02)",
        "📈 Прогноз (US-ANL-03)",
        # "📋 Отчеты (US-VIE-02)",
        "⚙️ Настройки"
    ])
    
    with tab1:
        overview.render(df)
    
    with tab2:
        clustering.render(df)
    
    # with tab3:
    #     anomalies.render(df)
    
    with tab4:
        forecasting.render(df)
    
    # with tab5:
    #     reports.render(df)
    
    with tab6:
        config.render_settings(df)

else:
    # Экран загрузки данных
    config.render_welcome_screen()

st.markdown("---")
st.caption("Система анализа потребления газа | Прототип | Реализованы все UC/US требования")