from dotenv import dotenv_values

# Загружаем переменные окружения
config = dotenv_values(".env")

# print(f'{config=}')

BOT_TOKEN = config['BOT_API']
API_URL = config['API_URL']
ALLOWED_PATH = config['ALLOWED_PATH']
ERROR_MESSAGE_FOR_USER = config['ERROR_MESSAGE_FOR_USER']
MANAGER_TELEGRAM_ID = config['MANAGER_TELEGRAM_ID']
MIN_ASPECT_RATIO = 0.67
MAX_ASPECT_RATIO = 1 / MIN_ASPECT_RATIO
BLURR_THRESHOLD = 0.0
IMG_WORK_FORMAT = 'jpg'
SEND_AS_FILE_INSTRUCTION = '''Для отправки фотографии как файл в телеграм, в максимальном исходном качестве сделайте следующее:\n
Нажмите скрепку в левом нижнем углу.\n
Нажмите кнопку «Файл/Документ». Нажмите «Выбрать из галереи».\n
Выберете одно или несколько фото.\n
Нажмите кнопку "Отправить".'''
