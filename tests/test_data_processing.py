# tests/test_data_processing.py
import pytest
from src.data_processing.loader import GasDataLoader
from src.data_processing.cleaner import GasDataCleaner

def test_loader_initialization():
    loader = GasDataLoader("data/raw")
    assert loader.data_dir.exists()

def test_date_normalization():
    cleaner = GasDataCleaner()
    # Тестовые данные
    # Проверка преобразования дат