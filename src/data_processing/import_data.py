import psycopg2
import pandas as pd
from datetime import datetime
import os

# Конфигурация БД
DB_CONFIG = {
    'dbname': 'meter_data',
    'user': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

class MeterDataImporter:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
            print("✅ Подключение к БД установлено")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            raise
    
    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()
    
    def parse_date(self, date_str):
        """Преобразование даты из формата dd.mm.yyyy в datetime"""
        try:
            return datetime.strptime(date_str, '%d.%m.%Y').date()
        except:
            # Пробуем другой формат, если есть проблемы
            return datetime.strptime(date_str, '%d.%m.%y').date()
    
    def import_from_csv(self, file_path, delimiter=';'):
        """Импорт данных из CSV файла"""
        try:
            # Читаем CSV файл
            df = pd.read_csv(file_path, 
                            delimiter=delimiter, 
                            header=None,
                            names=['location', 'meter_code', 'serial', 'date', 'value', 'type'],
                            quotechar='"',
                            encoding='utf-8')
            
            print(f"📊 Загружено {len(df)} строк из файла")
            
            cursor = self.conn.cursor()
            
            # Импортируем данные
            imported_count = 0
            skipped_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Очистка данных
                    location = str(row['location']).strip().replace('"', '')
                    meter_code = str(row['meter_code']).strip().replace('"', '')
                    serial = str(row['serial']).strip()
                    date_str = str(row['date']).strip()
                    value = int(row['value'])
                    reading_type = str(row['type']).strip().replace('"', '')
                    
                    # Преобразуем дату
                    reading_date = self.parse_date(date_str)
                    
                    # 1. Добавляем или получаем location
                    cursor.execute(
                        "SELECT id FROM locations WHERE location_name = %s",
                        (location,)
                    )
                    location_result = cursor.fetchone()
                    
                    if location_result:
                        location_id = location_result[0]
                    else:
                        cursor.execute(
                            "INSERT INTO locations (location_name) VALUES (%s) RETURNING id",
                            (location,)
                        )
                        location_id = cursor.fetchone()[0]
                    
                    # 2. Добавляем или получаем прибор учета
                    cursor.execute(
                        """SELECT id FROM meters 
                           WHERE meter_code = %s AND location_id = %s""",
                        (meter_code, location_id)
                    )
                    meter_result = cursor.fetchone()
                    
                    if meter_result:
                        meter_id = meter_result[0]
                        # Обновляем серийный номер, если изменился
                        cursor.execute(
                            "UPDATE meters SET meter_serial = %s WHERE id = %s",
                            (serial, meter_id)
                        )
                    else:
                        cursor.execute(
                            """INSERT INTO meters (meter_code, location_id, meter_serial) 
                               VALUES (%s, %s, %s) RETURNING id""",
                            (meter_code, location_id, serial)
                        )
                        meter_id = cursor.fetchone()[0]
                    
                    # 3. Добавляем показание
                    cursor.execute(
                        """INSERT INTO readings 
                           (meter_id, reading_date, value, reading_type, source_file)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (meter_id, reading_date) 
                           DO UPDATE SET 
                               value = EXCLUDED.value,
                               reading_type = EXCLUDED.reading_type,
                               source_file = EXCLUDED.source_file""",
                        (meter_id, reading_date, value, reading_type, os.path.basename(file_path))
                    )
                    
                    imported_count += 1
                    
                except Exception as e:
                    skipped_count += 1
                    print(f"⚠️ Пропущена строка: {row.to_dict()} - ошибка: {str(e)[:100]}")
            
            self.conn.commit()
            print(f"\n📈 Импорт завершен:")
            print(f"   ✅ Успешно импортировано: {imported_count} записей")
            print(f"   ⚠️  Пропущено: {skipped_count} записей")
            
            # Выводим статистику
            self.show_statistics()
            
            return imported_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Ошибка при импорте: {e}")
            return 0
    
    def show_statistics(self):
        """Показать статистику по импортированным данным"""
        cursor = self.conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) as total_readings FROM readings")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT meter_id) as unique_meters FROM readings")
        unique_meters = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT location_id) as unique_locations FROM meters")
        unique_locations = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT reading_type, COUNT(*) as count 
            FROM readings 
            GROUP BY reading_type 
            ORDER BY count DESC
        """)
        types_stats = cursor.fetchall()
        
        print(f"\n📊 Статистика базы данных:")
        print(f"   Всего показаний: {total}")
        print(f"   Уникальных приборов: {unique_meters}")
        print(f"   Уникальных населенных пунктов: {unique_locations}")
        print(f"\n   Распределение по типам показаний:")
        for type_name, count in types_stats:
            print(f"     {type_name}: {count}")
    
    def export_to_csv(self, output_file, location=None):
        """Экспорт данных в CSV"""
        try:
            query = """
            SELECT 
                location_name,
                meter_code,
                meter_serial,
                TO_CHAR(reading_date, 'DD.MM.YYYY') as reading_date,
                value,
                reading_type
            FROM v_full_readings
            """
            
            params = []
            if location:
                query += " WHERE location_name = %s"
                params.append(location)
            
            query += " ORDER BY location_name, meter_code, reading_date"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            # Экспортируем в CSV
            df.to_csv(output_file, 
                     sep=';', 
                     index=False, 
                     header=False,
                     quotechar='"',
                     encoding='utf-8')
            
            print(f"✅ Данные экспортированы в {output_file}")
            print(f"   Экспортировано {len(df)} записей")
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")

def main():
    importer = MeterDataImporter()
    
    try:
        # Импортируем данные
        print("🔄 Начинаем импорт данных...")
        imported = importer.import_from_csv('data.csv')
        
        if imported > 0:
            # Экспортируем для проверки
            importer.export_to_csv('exported_data.csv')
            
            # Пример запроса данных
            cursor = importer.conn.cursor()
            cursor.execute("""
                SELECT location_name, COUNT(*) as readings_count
                FROM v_full_readings
                GROUP BY location_name
                ORDER BY readings_count DESC
            """)
            
            print("\n📍 Показания по населенным пунктам:")
            for location, count in cursor.fetchall():
                print(f"   {location}: {count} показаний")
        
    except Exception as e:
        print(f"❌ Ошибка в основном процессе: {e}")
    finally:
        importer.close()

if __name__ == "__main__":
    main()