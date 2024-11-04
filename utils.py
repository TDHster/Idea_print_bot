from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Путь к каталогу с фотографиями
photos_dir = Path("orders/2024-10-29/1_Новый")

# Получаем список файлов в каталоге, отсортированный по имени
photo_files = sorted([f for f in photos_dir.glob("*") if f.suffix.lower() in ['.png', '.jpg', '.jpeg']])

# Размер коллажа
collage_width = 1280

# Шрифт для порядковых номеров
font_name = "Arial.ttf"
try:
    font = ImageFont.truetype(font_name, 100)
except OSError:
    # Если шрифт Arial.ttf не найден, используем встроенный шрифт
    font = ImageFont.load_default()
    print(f'Using default font {font}')

# Определяем количество строк и столбцов
num_photos = len(photo_files)
num_cols = int((num_photos ** 0.5) + 0.5)  # Округляем до ближайшего целого
num_rows = (num_photos + num_cols - 1) // num_cols  # Округляем вверх

# Определяем размер каждой фотографии
photo_width = collage_width // num_cols
photo_height = photo_width  # Мы делаем фотографии квадратными

# Создаем новое изображение для коллажа
collage_height = num_rows * photo_height
bg_col_byte = 260
collage = Image.new('RGB', (collage_width, collage_height), (bg_col_byte, bg_col_byte, bg_col_byte))

# Координаты для размещения фотографий
x, y = 0, 0

for i, photo_file in enumerate(photo_files):
    photo = Image.open(photo_file)
    
    # Масштабируем изображение по длинной стороне до размера ячейки
    if photo.width > photo.height:
        new_width = photo_width
        new_height = int(photo.height * (photo_width / photo.width))
    else:
        new_height = photo_height
        new_width = int(photo.width * (photo_height / photo.height))
    
    photo = photo.resize((new_width, new_height), Image.LANCZOS)
    
    # Создаем новое изображение с белыми полями, чтобы сохранить пропорции
    resized_photo = Image.new('RGB', (photo_width, photo_height), (bg_col_byte, bg_col_byte, bg_col_byte))
    
    # Вычисляем координаты для вставки фотографии с сохранением пропорций
    offset_x = (photo_width - new_width) // 2
    offset_y = (photo_height - new_height) // 2
    
    # Вставляем фотографию в центр нового изображения
    resized_photo.paste(photo, (offset_x, offset_y))
    
    # Добавляем порядковый номер на фотографию
    draw = ImageDraw.Draw(resized_photo)
    text_color = (255, 255, 255)  # Белый цвет текста (или черный, если необходимо)
    text_position = (50, resized_photo.height - 120)
    draw.text(text_position, f"{i+1}", font=font, fill=text_color)
    
    # Размещаем фотографию на коллаже
    collage.paste(resized_photo, (x, y))
    
    # Обновляем координаты для следующей фотографии
    x += photo_width
    
    # Если достигли конца строки, переходим на новую строку
    if (i + 1) % num_cols == 0:
        x = 0
        y += photo_height

# Сохраняем коллаж
collage.save("collage.jpg")