import glob
import os
import pandas as pd
import chardet

def detect_encoding(file_path):
    """Определяет кодировку файла."""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result['encoding']

def clean_csv_data(file_path, output_folder):
    """Очищает и обрабатывает CSV файл."""
    filename = os.path.basename(file_path)
    print(f"\nОбработка файла: {filename}")
    
    try:
        # Определяем кодировку файла
        encoding = detect_encoding(file_path)
        print(f"  Определенная кодировка: {encoding}")
        
        # Пробуем разные кодировки
        encodings_to_try = [encoding, 'windows-1251', 'cp1251', 'utf-8-sig', 'utf-8', 'MacCyrillic']
        
        for enc in encodings_to_try:
            try:
                # Читаем CSV БЕЗ заголовков (header=None) с указанием типов для оптимизации
                df = pd.read_csv(file_path, sep=';', encoding=enc, quotechar='"', 
                                dtype=str, header=None, engine='python')
                print(f"  Успешно прочитано с кодировкой: {enc}")
                print(f"  Размер: {len(df):,} строк, {len(df.columns)} столбцов")
                break
            except UnicodeDecodeError:
                continue
        else:
            print(f"  ✗ Не удалось определить кодировку файла")
            return False
        
        # Проверяем количество столбцов
        if len(df.columns) < 6:
            print(f"  ✗ Недостаточно столбцов: {len(df.columns)}")
            return False
        
        # Назначаем имена столбцов
        df.columns = ['city', 'account_number', 'meter_number', 'reading_date', 
                     'consumption', 'reading_method']
        
        print(f"  Первые 3 строки для проверки:")
        for i, row in df.head(3).iterrows():
            print(f"    Строка {i}: {row['city']} | {row['account_number']} | {row['meter_number']} | "
                  f"{row['reading_date']} | {row['consumption']} | {row['reading_method'][:30]}...")
        
        # ОЧИСТКА ДАННЫХ - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
        
        # 1. Сначала обработаем даты - это важно для фильтрации
        print("  Обработка дат...")
        if 'reading_date' in df.columns:
            # Векторизованная обработка дат
            def convert_date_vectorized(series):
                result = []
                for date_str in series:
                    try:
                        date_str = str(date_str).strip()
                        if pd.isna(date_str) or date_str.lower() in ['nan', 'none', '']:
                            result.append(None)
                            continue
                        
                        if '.' in date_str:
                            parts = date_str.split('.')
                            if len(parts) == 3:
                                day, month, year = parts
                                # Очищаем от нецифровых символов
                                day = ''.join(c for c in day if c.isdigit())
                                month = ''.join(c for c in month if c.isdigit())
                                year = ''.join(c for c in year if c.isdigit())
                                
                                if not (day and month and year):
                                    result.append(None)
                                    continue
                                
                                # Форматируем год
                                if len(year) == 2:
                                    year = '20' + year if int(year) < 50 else '19' + year
                                elif len(year) == 4:
                                    pass
                                else:
                                    result.append(None)
                                    continue
                                
                                result.append(f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}")
                                continue
                        result.append(date_str)
                    except:
                        result.append(None)
                return result
            
            df['reading_date'] = convert_date_vectorized(df['reading_date'])
        
        # 2. Обработка meter_number - убираем все пробелы
        print("  Обработка номеров счетчиков...")
        if 'meter_number' in df.columns:
            df['meter_number'] = df['meter_number'].astype(str).apply(
                lambda x: ''.join(c for c in str(x) if c.isdigit())
            )
        
        # 3. Обработка consumption - убираем пробелы, заменяем запятую на точку
        print("  Обработка показаний...")
        if 'consumption' in df.columns:
            def clean_consumption_simple(value):
                try:
                    value_str = str(value).strip()
                    if not value_str or value_str.lower() in ['nan', 'none']:
                        return None
                    
                    # Убираем все пробелы и неразрывные пробелы
                    value_str = value_str.replace(' ', '').replace('\xa0', '')
                    # Заменяем запятую на точку
                    value_str = value_str.replace(',', '.')
                    
                    # Извлекаем только цифры, точку и минус
                    cleaned = ''.join(c for c in value_str if c.isdigit() or c in '.-')
                    
                    if not cleaned or cleaned == '-':
                        return None
                    
                    # Конвертируем в float
                    return float(cleaned)
                except:
                    return None
            
            df['consumption'] = df['consumption'].apply(clean_consumption_simple)
        
        # 4. Обработка текстовых полей - делаем это в последнюю очередь
        print("  Обработка текстовых полей...")
        text_columns = ['city', 'account_number', 'reading_method']
        for col in text_columns:
            if col in df.columns:
                # Быстрая очистка без сложных regex
                df[col] = df[col].astype(str).apply(
                    lambda x: str(x).strip().replace('"', '').replace('\xa0', ' ')
                )
        
        # 5. Удаляем пустые строки
        print("  Удаление пустых строк...")
        initial_count = len(df)
        
        # Создаем маску для фильтрации
        mask = df['account_number'].apply(lambda x: str(x).strip() != '') & \
               df['reading_date'].notna() & \
               df['meter_number'].apply(lambda x: str(x).strip() != '')
        
        df = df[mask].copy()
        
        print(f"  Удалено пустых строк: {initial_count - len(df):,}")
        
        # 6. Сохраняем очищенный файл частями если очень большой
        output_filename = filename.replace('.csv', '_cleaned.csv')
        output_path = os.path.join(output_folder, output_filename)
        
        # Если файл очень большой (>500к строк), сохраняем частями
        if len(df) > 500000:
            print(f"  Файл очень большой, сохраняем частями...")
            # Разбиваем на части по 200к строк
            chunks = [df[i:i + 200000] for i in range(0, len(df), 200000)]
            
            # Сохраняем первую часть с заголовком
            chunks[0].to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
            
            # Добавляем остальные части без заголовка
            for i, chunk in enumerate(chunks[1:], 1):
                chunk.to_csv(output_path, mode='a', index=False, sep=';', 
                           encoding='utf-8-sig', header=False)
                print(f"    Часть {i+1} добавлена")
        else:
            # Сохраняем целиком
            df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
        
        print(f"  ✓ Файл сохранен: {output_filename}")
        print(f"  Структура данных:")
        print(f"    - Всего строк: {len(df):,}")
        print(f"    - Всего столбцов: {len(df.columns)}")
        print(f"    - Размер файла: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        
        # Пример данных после очистки
        if len(df) > 0:
            print(f"  Пример после очистки:")
            row = df.iloc[0]
            print(f"    Город: '{row['city'][:20]}...'")
            print(f"    Счет: {row['account_number']}")
            print(f"    Счетчик: {row['meter_number']}")
            print(f"    Дата: {row['reading_date']}")
            print(f"    Потребление: {row['consumption']}")
            print(f"    Метод: '{row['reading_method'][:30]}...'")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"  ✗ Ошибка при обработке файла {filename}: {str(e)}")
        traceback.print_exc()
        return False

# Основной код
if __name__ == "__main__":
    # Укажите путь к папке с CSV файлами
    input_folder = r"E:\magistr\KursProj\gas_consumption\data\raw"
    
    # Проверяем существование папки
    if not os.path.exists(input_folder):
        print(f"Папка не существует: {input_folder}")
        exit()
    
    # Получаем все CSV файлы
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
    
    if not csv_files:
        print(f"CSV файлы не найдены в папке: {input_folder}")
        exit()
    
    print(f"Найдено файлов для обработки: {len(csv_files)}")
    
    # Создаем папку для очищенных файлов
    cleaned_folder = os.path.join(input_folder, "cleaned")
    os.makedirs(cleaned_folder, exist_ok=True)
    
    # Обрабатываем все файлы
    successful = 0
    for csv_file in csv_files:
        if clean_csv_data(csv_file, cleaned_folder):
            successful += 1
    
    print(f"\n{'='*50}")
    print("ОБРАБОТКА ЗАВЕРШЕНА!")
    print(f"Успешно обработано: {successful} из {len(csv_files)} файлов")
    print(f"Очищенные файлы сохранены в: {cleaned_folder}")