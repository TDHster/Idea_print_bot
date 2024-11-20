#helpers.py
import aiohttp
from PIL import Image
from pathlib import Path
import cv2
import numpy as np
import hashlib
from pillow_heif import register_heif_opener
from time import time
from collections import defaultdict
from config import *
import os

print(f'{cv2.__version__=}')


# def convert_to_jpeg(file_path: Path) -> Path:
    # """Конвертирует изображение в JPEG, если оно в другом формате."""
    # with Image.open(file_path) as img:
    #     if img.format != 'JPEG':
    #         jpeg_path = file_path.with_suffix(".jpg")  # Создаем новый путь с расширением .jpg
    #         img = img.convert("RGB")  # Конвертируем в RGB для JPEG
    #         img.save(jpeg_path, "JPEG")
    #         # print(f"Изображение сохранено в формате JPEG по пути {jpeg_path}")
    #         return jpeg_path  # Возвращаем путь к новому JPEG файлу
    #     # print("Изображение уже в формате JPEG, конвертация не требуется.")
    #     return file_path  # Возвращаем исходный путь, если конвертация не нужна


# Регистрируем HEIF/HEIC открыватель в PIL
register_heif_opener()

def convert_to_jpeg(file_path):
    """
    Конвертирует файл в формат JPEG, если это необходимо, и удаляет исходный файл в случае успешной конвертации.

    :param file_path: Путь к файлу.
    :return: Путь к конвертированному файлу.
    """
    # Преобразуем путь в объект Path
    file_path = Path(file_path)
    
    # Проверяем, является ли файл HEIC
    if file_path.suffix.lower() in ('.heic', '.heif'):
        # Открываем файл с помощью PIL
        with Image.open(file_path) as img:
            # Создаем путь для сохранения JPEG файла
            image_path = file_path.with_suffix(f'.{IMG_WORK_FORMAT}')
            
            # Сохраняем изображение в формате JPEG
            # img.save(image_path, "JPEG")
            img.save(image_path)
            
            # Удаляем исходный файл
            file_path.unlink()
            
            return image_path
    else:
        # Если файл не является HEIC, возвращаем исходный путь
        return file_path


def get_aspect_ratio(file_path: Path) -> float:
    """Возвращает соотношение сторон изображения."""
    with Image.open(file_path) as img:
        width, height = img.size
        aspect_ratio = width / height
        # print(f"Aspect Ratio: {aspect_ratio:.2f}")
        return aspect_ratio


def estimate_blur(image_path):
    """
    Оценивает степень размытия изображения по заданному пути.

    :param image_path: Путь к изображению.
    :return: Дисперсия Лапласиана изображения. Чем выше значение, тем более четким считается изображение.
    """
    # Нормализация пути
    normalized_path = os.path.normpath(image_path)
    # Кодирование пути в байты
    encoded_path = os.fsencode(normalized_path)
    
    # Проверка существования файла
    if not os.path.exists(normalized_path):
        # raise FileNotFoundError(f"Файл не найден по пути: {normalized_path}")
        print(f"Файл не найден по пути: {normalized_path}")
    
    try:
        # Загружаем изображение в оттенках серого
        image = cv2.imread(encoded_path.decode('utf-8'), cv2.IMREAD_GRAYSCALE)
        
        if image is None:
            raise ValueError(f"Не удалось загрузить изображение по пути: {normalized_path}")
        
        # Применяем оператор Лапласа для вычисления градиента
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        
        # Вычисляем дисперсию Лапласиана, чем она больше тем больше резких деталей на изображении.
        variance = laplacian.var()
        
        return variance
    except Exception as e:
        # logger.error(f"Ошибка при обработке изображения: {normalized_path}, ошибка: {e}")
        print(f"Ошибка при обработке изображения: {normalized_path}, ошибка: {e}")
        return 1000 # for look like ok, workaround when cann't open path in windows with cyrrillic symbols
    
def generate_unique_filename(original_filename):
    timestamp = int(time() * 1000)  # Метка времени в миллисекундах
    return f"{timestamp}_{original_filename}"


def get_original_filename(unique_filename):
    unique_filename_str = str(unique_filename)
    # Разделяем по первому символу "_" и возвращаем оригинальное имя файла
    return unique_filename_str.split("_", 1)[1]


def get_number_photo_files(directory_path: str) -> int:
    """
    Подсчитывает количество файлов с расширением .jpg в указанном каталоге.

    :param directory_path: Путь к каталогу.
    :return: Количество файлов с расширением .jpg.
    """
    # Создаем объект Path из строки пути
    path = Path(directory_path)
    
    # Проверяем, существует ли каталог и является ли он каталогом
    if not path.exists() or not path.is_dir():
        raise ValueError(f"Путь {directory_path} не существует или не является каталогом.")
        return None
    
    # Ищем все файлы с расширением .jpg в каталоге
    jpg_files = list(path.glob(f"*.{IMG_WORK_FORMAT}"))
    
    # Возвращаем количество найденных файлов
    return len(jpg_files)


def calculate_md5(file_path):
    """Вычисляет MD5 хеш для файла по указанному пути."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def find_matching_files_by_md5(directory, target_file=None):
    """
    Ищет файлы с расширением .jpg в указанном каталоге и возвращает список попарных совпадений по MD5.
    Если указан target_file, возвращает только совпадения с этим файлом.
    """
    # Преобразуем directory и target_file в объекты Path
    directory = Path(directory)
    target_file = Path(target_file) if target_file else None
    
    # Словарь для хранения списка файлов по их MD5-хешу
    md5_dict = defaultdict(list)
    matching_pairs = []

    # Проходим по всем файлам в каталоге и его подкаталогах
    for file_path in directory.rglob(f"*.{IMG_WORK_FORMAT}"):
        file_md5 = calculate_md5(file_path)
        md5_dict[file_md5].append(file_path)

    # Если указан целевой файл, проверяем его MD5 и ищем совпадения
    if target_file and target_file.exists():
        target_md5 = calculate_md5(target_file)
        if target_md5 in md5_dict:
            matching_pairs = [(target_file, file) for file in md5_dict[target_md5] if file != target_file]
        return matching_pairs

    # Ищем все совпадения по MD5
    for file_list in md5_dict.values():
        if len(file_list) > 1:
            matching_pairs.extend([(file_list[i], file_list[j]) for i in range(len(file_list)) for j in range(i + 1, len(file_list))])

    return matching_pairs