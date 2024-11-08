# main.py
import asyncio
import aiohttp
import logging
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import dotenv_values
from pathlib import Path
import os
from helpers import get_aspect_ratio, convert_to_jpeg, estimate_blur, find_matching_files_by_md5, generate_unique_filename, get_original_filename, get_number_photo_files
from config import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
# config = dotenv_values(".env")
# BOT_TOKEN = config['BOT_API']
# API_URL = config['API_URL']
# ALLOWED_PATH = config['ALLOWED_PATH']  # для проверки пути сохранения файлов чтобы не перезаписать что-нибудь.
# ERROR_MESSAGE_FOR_USER = config['ERROR_MESSAGE_FOR_USER']
# MANAGER_TELEGRAM_ID = config['MANAGER_TELEGRAM_ID']
# MIN_ASPECT_RATIO=float(config['MIN_ASPECT_RATIO'])
# MAX_ASPECT_RATIO=1/MIN_ASPECT_RATIO
# BLURR_THRESHOLD=float(config['BLURR_THRESHOLD'])
# FORMAT_FOR_CONVERSION = config['BLURR_THRESHOLD']
 
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
    await state.set_data({})
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Знаю номер заказа", callback_data=f"entering_order_number"),
                InlineKeyboardButton(text="+Заказ", callback_data=f"new_order")
            ]
        ]
    )
    await message.answer("Я – бот сборщик заказов типографии <b>Идеяпринт</b>.\n"
                         "Если вы уже оплатили заказ, то потребуется ввести его номер (можно с пробелами и без).\n"
                         "Для нового заказа нажмите “+Заказ”", 
                         reply_markup=keyboard)


@dp.callback_query(F.data.startswith("entering_order_number"))
# async def entering_order_number(message: types.Message, state: FSMContext):
async def entering_order_number(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите номер вашего заказа:")
    await state.set_state(OrderStates.waiting_for_order_number)
    await callback_query.answer()


 # Нет в ТЗ
@dp.callback_query(F.data.startswith("new_order"))
async def entering_order_number(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(ERROR_MESSAGE_FOR_USER)
    await bot.send_message(callback_query.from_user.id, "Эта функция не реализована. Перезапуск бота.")
    await callback_query.answer()
    await cmd_start(callback_query.message, state)


# Функция для получения данных о заказе
async def fetch_order_data_via_API(order_number: str) -> tuple:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}{order_number}") as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"API 1c return answer: {data}")
                
                if data["result"]:
                    number_of_photos = data["quantity"]
                    order_folder = Path(data["path"])
                    return number_of_photos, order_folder
                else:
                    return None, None
            else:
                logger.info(f"API 1c return answer: {response.status}")
                return None, None


# Хэндлер для номера заказа
@dp.message(OrderStates.waiting_for_order_number)
async def process_order_number(message: types.Message, state: FSMContext):
    order_number = message.text.strip().replace(" ", "")  # Удаляем все пробелы.
    logger.info(f"User {message.from_user.id} entered order number: {order_number}")
    
    # Получаем данные о заказе
    number_of_photos, order_folder = await fetch_order_data_via_API(order_number)
    
    if number_of_photos is None or order_folder is None:
        await message.answer(ERROR_MESSAGE_FOR_USER)
        await state.set_state(OrderStates.waiting_for_order_number)
        return
    
    if not str(order_folder).startswith(ALLOWED_PATH):
        await message.answer(f"Ошибка программы. Получен неверный путь к папке заказа.")
        await message.answer(ERROR_MESSAGE_FOR_USER)
        await state.set_state(OrderStates.waiting_for_order_number)
        return
    
    order_folder.mkdir(parents=True, exist_ok=True)
    
    uploaded_photos = get_number_photo_files(order_folder)  # на случай если заказ уже существует и было с ним взаимодействие.
    
    # Сохраняем данные заказа в состоянии
    await state.update_data(order_number=order_number, order_folder=order_folder, 
                            number_of_photos=number_of_photos, uploaded_photos=uploaded_photos)
    logger.info(f"Order folder created: {order_folder}")
    
    keyboard_cancel_order = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отменить", callback_data=f"cancel_order:{order_number}")
            ]
        ]
    )
    
    await message.answer(
        f"Отправляйте мне фотографии, которые хотите напечатать в альбоме.\n"
        f"У вас {number_of_photos} фотографий для загрузки.\n"
        f"<i>Чтобы мессенджер не ухудшил качество фотографии присылайте её в виде файла. Сейчас пришлю инструкцию как это сделать</i>", 
        reply_markup=keyboard_cancel_order
    )
    
    await state.set_state(OrderStates.waiting_for_photos)


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
            # file_path = Path("orders/2024-10-29/1_Новый") / generate_file_name(uploaded_photos, original_file_name)

            # filename_with_number = generate_file_name(uploaded_photos, document.file_name)
            filename_with_unique = generate_unique_filename(document.file_name)
            # file_path = order_folder / document.file_name  # Определяем путь для сохранения файла
            file_path = order_folder / filename_with_unique  # Определяем путь для сохранения файла
            
            # Скачиваем и сохраняем файл
            file_info = await bot.get_file(file_id)
            await bot.download_file(file_info.file_path, file_path)
            
            # Конвертируем, если это необходимо
            img_path = convert_to_jpeg(file_path)
            if not os.path.exists(img_path):
                logger.error(f"Файл {img_path} не существует после конвертации.")
                continue
            
            # Получаем соотношение сторон
            aspect_ratio = get_aspect_ratio(img_path)
            blur = estimate_blur(img_path)

            uploaded_photos  = get_number_photo_files(order_folder)
            
            logger.info(f"Photo saved for user {message.from_user.id} at {file_path}. {uploaded_photos} of {number_of_photos} uploaded.")
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Отменить весь заказ", callback_data=f"cancel_order:{order_number}")
                    ]
                ]
            )
            await message.answer(f"Файл {uploaded_photos} из {number_of_photos} получен.\n"
                                 f"Исходное имя файла: {document.file_name}\n"
                                 f"Aspect ratio: {aspect_ratio:0.1f}.\n"
                                 f"Коэффициент размытия фото: {blur:.1f}\n",
                                 reply_markup=keyboard)
            
            keyboard_cancel_file = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Отменить последнее фото", 
                                             callback_data=f"cancel_last_photo"),
                    ]
                ]
            )
            if not MAX_ASPECT_RATIO > aspect_ratio > MIN_ASPECT_RATIO:
                await message.answer('У этой фотографии соотношение сторон выходит за рамки рекомендованного,'
                                     'она слишком узкая/широкая', 
                                     reply_markup=keyboard_cancel_file)
            if blur < BLURR_THRESHOLD:
                await message.answer('Изображение на фотографии слишком "размыто".',
                                     reply_markup=keyboard_cancel_file)
            
            logger.info(f'{order_folder=} {img_path=}')
            matches = find_matching_files_by_md5(order_folder, img_path)
            if matches:
                await message.answer(f'Загруженное фото совпадает с предыдущими {matches}',
                        reply_markup=keyboard_cancel_file)
                for match in matches:
                    print("Совпадения по MD5:")
                    for file_name in match:
                        print(get_original_filename(file_name))
            else:
                print("Совпадений по MD5 не найдено.")

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
    else:
        await message.answer(f"Жду еще фото.")

    # Обновляем состояние с новым значением загруженных фотографий
    # await state.update_data(uploaded_photos=uploaded_photos)


#cancel_photo:{order}:
@dp.callback_query(F.data.startswith("cancel_last_photo"))
async def cancel_last_photo(callback: CallbackQuery, state: FSMContext):
    # order = callback.data.split(":")[1]
    data = await state.get_data()
    order_folder = data['order_folder']
    photos_in_order = data['number_of_photos']

    path = Path(order_folder)
    
    # Проверяем, существует ли каталог и является ли он каталогом
    if not path.exists() or not path.is_dir():
        logger.error(f"Path {order_folder} not exist or not directory.")
    
    # Ищем все файлы с заданным расширением  в каталоге
    jpg_files = list(path.glob(f"*.{IMG_WORK_FORMAT}"))
    
    # Сортируем файлы по имени
    jpg_files.sort(key=lambda x: x.name)
    
    # Проверяем, есть ли файлы для удаления
    if jpg_files:
        # Удаляем последний файл в списке
        last_file = jpg_files[-1]
        last_file.unlink()
        await bot.send_message(callback.message.chat.id, 
                               f'Файл {get_original_filename(last_file.name)} отменен.')
        # callback.message.answer(f'Файл {last_file} отменен.')
        number_uploaded_photos = get_number_photo_files(order_folder)
        logger.info(f"Удален файл по запросу пользователя: {last_file}")
        await callback.answer("Файл отменен.")
        await state.set_state(OrderStates.waiting_for_photos)
    else:
        logger.info(f"Error: В {order_folder} no {IMG_WORK_FORMAT} files")
        await callback.answer("Ошибка: В каталоге нет файлов для удаления.")

    await bot.send_message(callback.message.chat.id, 
                           f'Сейчас загружено {number_uploaded_photos} из {photos_in_order} в заказе.')
    if number_uploaded_photos < photos_in_order:
        await bot.send_message(callback.message.chat.id, f'Ожидаю фотографий.')
    # callback.answer()
     
        
@dp.message(F.content_type.in_({"text", 'photo'}), OrderStates.waiting_for_photos)
async def process_photo_wrong_type(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_number = data['order_number']
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                # TODO InlineKeyboardButton(text="Продолжить", callback_data=f"cancel_order:{order_number}"),  # TODO
                InlineKeyboardButton(text="Отменить", callback_data=f"cancel_order:{order_number}"),
                # TODO InlineKeyboardButton(text="Больше не спрашивать", callback_data=f"cancel_order:{order_number}") # TODO
            ]
        ]
    )
    await message.answer("Вы отправили фото не файлом, а изображением. Качество будет хуже.\n"
                         f"Продолжить/Отменить/Больше не спрашивать",
                         reply_markup=keyboard)
    logger.warning(f"User {message.from_user.id} sent an image not as file.")


# Хэндлер для обработки callback "Отправить в печать"
@dp.callback_query(F.data.startswith("print_order:"))
async def process_print_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    logger.info(f"Order {order_number} marked for printing by user {callback.from_user.id}")
    await callback.message.answer("Заказ отправлен в печать.")
    await callback.answer()
    bot.send_message(chat_id=MANAGER_TELEGRAM_ID, text=f"Заказ {order_number} собран и подтверджен, надо печатать.")
    await state.update_data({}) # Сброс данных состояния    
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
    await state.update_data({}) # Сброс состояния и данных состояния    
    await callback.message.answer("Данные заказа сброшены.")
    await callback.answer()
    await cmd_start(callback.message, state)
    

# Запуск бота
async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
