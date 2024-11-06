#helpers.py
from PIL import Image
from pathlib import Path
import cv2
import numpy as np
import hashlib
from pillow_heif import register_heif_opener


print(cv2.__version__)


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
            jpeg_path = file_path.with_suffix('.jpg')
            
            # Сохраняем изображение в формате JPEG
            img.save(jpeg_path, "JPEG")
            
            # Удаляем исходный файл
            file_path.unlink()
            
            return jpeg_path
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


def generate_file_name(number, original_file_name, num_digits=3):
    """
    Генерирует имя файла в формате "число_оригинальное_имя_файла.расширение".

    :param number: Число загруженных фотографий.
    :param original_file_name: Оригинальное имя файла.
    :param num_digits: Количество знаков, до которых нужно дополнить число нулями (по умолчанию 3).
    :return: Новое имя файла.
    """
    # Дополняем число нулями до указанного количества знаков
    number_str = f"{number:0{num_digits}d}"
    
    # Получаем расширение файла
    file_extension = Path(original_file_name).suffix
    
    # Убираем расширение из оригинального имени файла
    base_name = Path(original_file_name).stem
    
    # Формируем новое имя файла
    new_file_name = f"{number_str}_{base_name}{file_extension}"
    
    print(f'{new_file_name=}')
    
    return new_file_name

def extract_original_file_name(file_path):
    """
    Извлекает оригинальное имя файла из пути, исключая пять цифр и подчеркивание в начале.

    :param file_path: Путь к файлу.
    :return: Оригинальное имя файла.
    """
    # Получаем имя файла из пути
    file_name = Path(file_path).name
    
    # Проверяем, что имя файла начинается с пяти цифр и подчеркивания
    if file_name[:6].isdigit() and file_name[5] == '_':
        # Извлекаем оригинальное имя файла
        original_file_name = file_name[6:]
    else:
        # Если формат не соответствует ожидаемому, возвращаем исходное имя файла
        original_file_name = file_name
    
    return original_file_name
    # Пример использования
    # file_path = Path("orders/2024-10-29/1_Новый/00003_img4312.jpg")
    # original_file_name = extract_original_file_name(file_path)
    # print(original_file_name)  # Вывод: img4312.jpg