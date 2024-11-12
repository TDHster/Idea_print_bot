from dotenv import dotenv_values

# Загружаем переменные окружения
config = dotenv_values(".env")

BOT_TOKEN = config['BOT_API']
API_URL = config['API_URL']
ALLOWED_PATH = config['ALLOWED_PATH']
ERROR_MESSAGE_FOR_USER = config['ERROR_MESSAGE_FOR_USER']
MANAGER_TELEGRAM_ID = config['MANAGER_TELEGRAM_ID']
MIN_ASPECT_RATIO = 0.67
MAX_ASPECT_RATIO = 1 / MIN_ASPECT_RATIO
BLURR_THRESHOLD = 30.0
IMG_WORK_FORMAT = 'jpg'
SEND_AS_FILE_IOS = '''Для отправки фотографии как файл в телеграм, в максимальном исходном качестве на iPhone сделайте следующее:\n
Нажмите скрепку в левом нижнем углу.\n
Внизу нажмите кнопку «Файл».Нажмите «Выбрать из галереи».\n
Выберете одно или несколько фото.\n
Нажмите кнопку "Отправить".'''
SEND_AS_FILE_ANDROID = '''Для отправки фотографии как файл в Telegram на устройстве Android, чтобы сохранить максимальное качество, выполните следующие шаги:
Нажмите на скрепку в правом нижнем углу экрана.\n
Выберите опцию «Файл».\n
Нажмите «Выбрать из галереи», чтобы загрузить фото с устройства.\n
Выберите одно или несколько фото.\n
Нажмите кнопку "Отправить".\n
'''