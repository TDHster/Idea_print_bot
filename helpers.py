#helpers.py
from PIL import Image
from pathlib import Path

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
