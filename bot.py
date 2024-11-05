# main.py
import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import dotenv_values
from pathlib import Path
from datetime import date
from helpers import get_aspect_ratio, convert_to_jpeg
import shutil



# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
config = dotenv_values(".env")
BOT_TOKEN = config['BOT_API']
API_URL = config['API_URL']
# BASE_PATH = Path(config['BASE_ORDER_PATH'])  # Основной путь к папке для заказов из .env
ALLOWED_PATH = config['ALLOWED_PATH']  # для проверки чтобы не перезаписать что-нибудь.

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния
class OrderStates(StatesGroup):
    waiting_for_order_number = State()
    waiting_for_photos = State()
    processing_photos = State()
    order_complete = State()
    sending_to_print = State()

# Хэндлер для команды /start
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(f"User {message.from_user.id} started a session.")
    await message.answer("Вас приветствует система приемки заказов <b>Идея Принт</b>.")
    await message.answer("Введите номер вашего заказа:")
    await state.set_state(OrderStates.waiting_for_order_number)

# Хэндлер для номера заказа
@dp.message(OrderStates.waiting_for_order_number)
async def process_order_number(message: types.Message, state: FSMContext):
    order_number = message.text
    logger.info(f"User {message.from_user.id} entered order number: {order_number}")
    
    # Запрос к API-серверу для получения данных о заказе
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}{order_number}") as response:
            if response.status == 200:
                data = await response.json()
                print(f'{data}')
                if data["result"]:
                    number_of_photos = data["quantity"]
                    order_folder = Path(data["path"])
                    if not str(order_folder).startswith(ALLOWED_PATH):
                        await message.answer("Ошибка программы. Получен неверный путь к папке заказа.")
                        await state.set_state(OrderStates.waiting_for_order_number)
                        await state.finish()
                        return
 
                    order_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Сохраняем данные заказа в состоянии
                    await state.update_data(order_number=order_number, order_folder=order_folder, 
                                            number_of_photos=number_of_photos, uploaded_photos=0)
                    logger.info(f"Order folder created: {order_folder}")
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(text="Отменить", callback_data=f"cancel_order:{order_number}")
                            ]
                        ]
                    )
                    await message.answer(
                        f"Отправляйте мне фотографии, которые хотите напечатать в альбоме.\n"
                        f"У вас {number_of_photos} фотографий для загрузки.\n"
                        f"<i>Только чтобы мессенджер не ухудшил качество фотографии присылайте её в виде файла. Сейчас пришлю инструкцию как это сделать</i>", 
                        reply_markup=keyboard
                    )
                    await state.set_state(OrderStates.waiting_for_photos)
                else:
                    await message.answer(f"Заказ с номером {order_number} не найден.")
            else:
                logger.info(f"API 1c return answer: {response.status}")
                await message.answer("Приношу свои извинения, у нас технический сбой.\nПопробуйте позже или свяжитесь с нашим менеджером по телефону 495 2223322")


# Хэндлер для получения фотографий как документ
@dp.message(F.content_type.in_({"document"}), OrderStates.waiting_for_photos)
async def process_photo(message: types.Message, state: FSMContext):
    # Получаем данные о состоянии
    data = await state.get_data()
    order_folder = data['order_folder']
    number_of_photos = data['number_of_photos']
    uploaded_photos = data.get('uploaded_photos', 0)  # Получаем текущее количество загруженных фотографий
    order_number = data['order_number']

    # Получаем список документов
    documents = message.document if isinstance(message.document, list) else [message.document]

    for document in documents:
        if document:
            file_id = document.file_id  # Получаем file_id
            file_path = order_folder / document.file_name  # Определяем путь для сохранения файла
            
            # Скачиваем и сохраняем файл
            file_info = await bot.get_file(file_id)
            await bot.download_file(file_info.file_path, file_path)
            
            # Конвертируем в JPEG, если это необходимо
            jpeg_path = convert_to_jpeg(file_path)

            # Получаем соотношение сторон
            aspect_ratio = get_aspect_ratio(jpeg_path)

            # Увеличиваем счетчик загруженных фотографий
            uploaded_photos += 1
            logger.info(f"Photo saved for user {message.from_user.id} at {file_path}. {uploaded_photos} of {number_of_photos} uploaded.")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Отменить", callback_data=f"cancel_order:{order_number}")
                    ]
                ]
            )
            await message.answer(f"Файл {uploaded_photos} из {number_of_photos} получен.\n"
                                 f"Aspect ratio: {aspect_ratio:0.1f}.\n"
                                 f"Жду еще.",
                                 reply_markup=keyboard)

    # Проверяем, завершен ли процесс загрузки фотографий
    if uploaded_photos >= number_of_photos:
        await state.set_state(OrderStates.order_complete)

        logger.info(f"All photos for order {order_number} by {message.from_user.id} uploaded.")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Отправить в печать", callback_data=f"print_order:{order_number}"),
                    InlineKeyboardButton(text="Отменить", callback_data=f"cancel_order:{order_number}")
                ]
            ]
        )
        await message.answer(f"Все файлы для заказа {order_number} загружены.", reply_markup=keyboard)

    # Обновляем состояние с новым значением загруженных фотографий
    await state.update_data(uploaded_photos=uploaded_photos)
        
@dp.message(F.content_type.in_({"text", 'photo'}), OrderStates.waiting_for_photos)
async def process_photo_wrong_type(message: types.Message, state: FSMContext):
    await message.answer("Вы отправили фото не файлом, а изображением. Качество будет хуже. Продолжить/Отменить/Больше не спрашивать")
    logger.warning(f"User {message.from_user.id} sent an image not as file.")


# Хэндлер для обработки callback "Отправить в печать"
@dp.callback_query(F.data.startswith("print_order:"))
async def process_print_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    logger.info(f"Order {order_number} marked for printing by user {callback.from_user.id}")
    await callback.message.answer("Заказ отправлен в печать.")
    await callback.answer(f"Это сообщение для менеджера.\n"
                         f"Заказ {order_number} собран и подтверджен, надо печатать.") #flash message
    await callback.answer()
    await state.reset_data()  # Сброс данных состояния
    await state.finish()
    await cmd_start(callback.message, state)
    

# Хэндлер для обработки callback "Отменить"
@dp.callback_query(F.data.startswith("cancel_order:"))
async def process_cancel_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    logger.info(f"Order {order_number} canceled by user {callback.from_user.id}")
    await state.set_state(OrderStates.waiting_for_order_number)
    await callback.message.answer("Данные заказа сброшены.")
    await callback.answer()
    data = await state.get_data()
    order_folder = data.get('order_folder')
    
    if order_folder:
        order_folder_path = Path(order_folder)
        if order_folder_path.exists():
            try:
                # Удаляем каталог
                shutil.rmtree(order_folder_path)
                logger.info(f"Order folder {order_folder_path} removed.")
            except Exception as e:
                logger.error(f"Failed to remove order folder {order_folder_path}: {e}")
        else:
            logger.warning(f"Order folder {order_folder_path} does not exist.")
    
    # Сбрасываем данные состояния
    await state.reset_data()
    # await state.finish()      # Сброс состояния и данных состояния
    
    await callback.message.answer("Данные заказа сброшены.")
    await callback.answer()
    await cmd_start(callback.message, state)
    

# Запуск бота
async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
