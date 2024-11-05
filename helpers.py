#helpers.py
from PIL import Image
from pathlib import Path
import cv2
import numpy as np
import hashlib

print(cv2.__version__)


def convert_to_jpeg(file_path: Path) -> Path:
    """Конвертирует изображение в JPEG, если оно в другом формате."""
    with Image.open(file_path) as img:
        if img.format != 'JPEG':
            jpeg_path = file_path.with_suffix(".jpg")  # Создаем новый путь с расширением .jpg
            img = img.convert("RGB")  # Конвертируем в RGB для JPEG
            img.save(jpeg_path, "JPEG")
            # print(f"Изображение сохранено в формате JPEG по пути {jpeg_path}")
            return jpeg_path  # Возвращаем путь к новому JPEG файлу
        # print("Изображение уже в формате JPEG, конвертация не требуется.")
        return file_path  # Возвращаем исходный путь, если конвертация не нужна


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
    # Загружаем изображение в оттенках серого
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    if image is None:
        raise ValueError(f"Не удалось загрузить изображение по пути: {image_path}")
    
    # Применяем оператор Лапласа для вычисления градиента
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    
    # Вычисляем дисперсию Лапласиана
    variance = laplacian.var()
    
    return variance


def calculate_md5(file_path):
    """
    Вычисляет MD5 хеш файла по заданному пути.

    :param file_path: Путь к файлу.
    :return: MD5 хеш файла в виде строки.
    """
    # Создаем объект хеша
    md5_hash = hashlib.md5()
    
    # Открываем файл в бинарном режиме
    with open(file_path, "rb") as f:
        # Читаем файл блоками по 4096 байт
        for chunk in iter(lambda: f.read(4096), b""):
            # Обновляем хеш с каждым блоком данных
            md5_hash.update(chunk)
    
    # Возвращаем MD5 хеш в виде шестнадцатеричной строки
    return md5_hash.hexdigest()