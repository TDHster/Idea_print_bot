from dotenv import dotenv_values

# Загружаем переменные окружения
config = dotenv_values(".env")

BOT_TOKEN = config['BOT_API']
API_URL = config['API_URL']
ALLOWED_PATH = config['ALLOWED_PATH']
ERROR_MESSAGE_FOR_USER = config['ERROR_MESSAGE_FOR_USER']
MANAGER_TELEGRAM_ID = config['MANAGER_TELEGRAM_ID']
MIN_ASPECT_RATIO = float(config['MIN_ASPECT_RATIO'])
MAX_ASPECT_RATIO = 1 / MIN_ASPECT_RATIO
BLURR_THRESHOLD = float(config['BLURR_THRESHOLD'])
IMG_WORK_FORMAT = config['IMG_WORK_FORMAT'] 