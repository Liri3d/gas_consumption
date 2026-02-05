import polars as pl
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GasDataLoader:
    def __init__(self, data_dir: str = "data/raw"):
        self.data_dir = Path(data_dir)
        
    def load_single_file(self, file_path: Path) -> pl.DataFrame:
        """Загрузка одного CSV файла с помощью Polars"""
        try:
            df = pl.read_csv(
                file_path,
                separator=';',
                quote_char='"',
                encoding='utf-8',
                has_header=False,
                new_columns=[
                    "management", "subscriber_id", "md_id", 
                    "date", "gas_consumption", "source"
                ],
                dtypes={
                    "subscriber_id": pl.Utf8,
                    "md_id": pl.Int64,
                    "gas_consumption": pl.Float32,
                    "date": pl.Utf8
                }
            )
            logger.info(f"Loaded {df.height} rows from {file_path.name}")
            return df
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def load_from_upload(self, uploaded_file) -> pl.DataFrame:
        """Загрузка данных из загруженного файла Streamlit"""
        import tempfile
        import io
        
        try:
            # Читаем содержимое файла
            content = uploaded_file.getvalue().decode('utf-8')
            
            # Используем StringIO для имитации файла
            df = pl.read_csv(
                io.StringIO(content),
                separator=';',
                quote_char='"',
                has_header=False,
                new_columns=[
                    "management", "subscriber_id", "md_id", 
                    "date", "gas_consumption", "source"
                ],
                dtypes={
                    "subscriber_id": pl.Utf8,
                    "md_id": pl.Int64,
                    "gas_consumption": pl.Float32,
                    "date": pl.Utf8
                }
            )
            logger.info(f"Loaded {df.height} rows from uploaded file")
            return df
        except Exception as e:
            logger.error(f"Error loading uploaded file: {e}")
            return None