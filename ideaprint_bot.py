# ideaprint_bot.py
import asyncio
import aiohttp
import logging
import shutil
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import dotenv_values
from pathlib import Path
import os
from time import time
from helpers import get_aspect_ratio, convert_to_jpeg, estimate_blur, find_matching_files_by_md5, generate_unique_filename, get_original_filename, get_number_photo_files
from config import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
 
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
                InlineKeyboardButton(text="Знаю номер заказа", callback_data=f"entering_order_number:"),
                InlineKeyboardButton(text="+Заказ", callback_data=f"new_order:")
            ]
        ]
    )
    await message.answer("Я – бот сборщик заказов типографии <b>Идеяпринт</b>.\n"
                         "Если вы уже оплатили заказ, то потребуется ввести его номер (можно с пробелами и без).\n"
                         "Для нового заказа нажмите “+Заказ”", 
                         reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_for_order_number)  # for intercept plain text without button


@dp.callback_query(F.data.startswith("entering_order_number:"))
# async def entering_order_number(message: types.Message, state: FSMContext):
async def entering_order_number(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer("Введите номер вашего заказа:")
    await state.set_state(OrderStates.waiting_for_order_number)
    await callback_query.answer()


@dp.callback_query(F.data.startswith("new_order:"))
async def new_order(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(ERROR_MESSAGE_FOR_USER)
    await bot.send_message(callback_query.from_user.id, "Эта функция не реализована. \nПерезапуск бота.")
    await callback_query.answer()
    await cmd_start(callback_query.message, state)


async def fetch_order_data_via_API(order_number: str) -> tuple:
    '''
    # Функция для получения данных о заказе от 1С
    order_number - номер заказа.
    return number_of_photos, order_folder or None, None
    '''
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
                logger.error(f"API 1c return answer: {response.status}")
                return None, None


# Хэндлер для номера заказа
@dp.message(OrderStates.waiting_for_order_number)
async def process_order_number(message: types.Message, state: FSMContext):
    order_number = message.text.strip().replace(" ", "")  # Удаляем все пробелы by ТЗ.
    logger.info(f"User {message.from_user.id} entered order number: {order_number}")
    
    # Получаем данные о заказе
    number_of_photos, order_folder = await fetch_order_data_via_API(order_number)
    
    if number_of_photos is None or order_folder is None:
        await message.answer(f"Ошибка.")
        # await message.answer(f"Ошибка программы. Не получен путь к папке заказа или количество фото.")
        logger.error("1C response number_of_photos is None or order_folder is None")
        # await message.answer(ERROR_MESSAGE_FOR_USER)
        await state.set_state(OrderStates.waiting_for_order_number)
        await cmd_start(message, state)
        return
    
    if not str(order_folder).startswith(ALLOWED_PATH):
        # await message.answer(f"Ошибка программы. Получен неверный путь к папке заказа.")
        logger.error("1C return not allowed path.")
        await message.answer(ERROR_MESSAGE_FOR_USER)
        await state.set_state(OrderStates.waiting_for_order_number)
        await cmd_start(message, state)
        return
    
    order_folder.mkdir(parents=True, exist_ok=True)
    
    uploaded_photos = get_number_photo_files(order_folder)  # на случай если заказ уже существует и было с ним взаимодействие.
    
    # Сохраняем данные заказа в состоянии
    await state.update_data(order_number=order_number, order_folder=order_folder, 
                            number_of_photos=number_of_photos, uploaded_photos=uploaded_photos)
    logger.info(f"Folder created: {order_folder}, for order {order_number} with {number_of_photos} number of photos.")
    

    if uploaded_photos > 0:
        await message.answer(f'Для заказа {order_number} уже загружено {uploaded_photos} фотографий.')

    await message.answer(
        f"Отправляйте мне фотографии, которые хотите напечатать в альбоме.\n"
        f"У вас {number_of_photos} фотографий для загрузки.\n"
        f"<i>Чтобы мессенджер не ухудшил качество фотографии присылайте её в виде файла. Сейчас пришлю инструкцию как это сделать</i>", 
        reply_markup=generate_keyboard_cancel_order(order_number)
    )
    await message.answer(SEND_AS_FILE_INSTRUCTION)
    
    await state.set_state(OrderStates.waiting_for_photos)


# Функция для создания клавиатуры отмены
def generate_keyboard_cancel_last_img():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отменить последнее фото", callback_data="cancel_last_photo:"),
            ]
        ]
    )


def generate_keyboard_cancel_order(order_number):
    keyboard_cancel_order = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Отменить заказ", callback_data=f"cancel_order:{order_number}")
            ]
        ]
    )
    return keyboard_cancel_order


# Функция для загрузки и сохранения файла
async def download_and_save_file(file_id, file_path):
    file_info = await bot.get_file(file_id)
    await bot.download_file(file_info.file_path, file_path)


# Функция для обработки фотографии
async def process_image(img_path, order_folder, order_number, number_of_photos, message):
    uploaded_photos = get_number_photo_files(order_folder)
    # logger.info(f"Photo saved for user {message.from_user.id} at {img_path}. {uploaded_photos} of {number_of_photos} uploaded.")
    
    await check_aspect_ratio(img_path, message)
    await check_blur(img_path, message)
    return uploaded_photos


# Функция для проверки и отправки сообщений о совпадениях по MD5
async def check_md5_matches(img_path, order_folder, message):
    logger.info(f'MD5 matches start {img_path}...')
    matches = find_matching_files_by_md5(order_folder, img_path)
    logger.info(f'MD5 matches end {img_path}...')
    if matches:
        await message.answer(
            f'Загруженное фото совпадает с предыдущими.'
            # f'Загруженное фото совпадает с предыдущими {matches}'
            # , reply_markup=create_cancel_keyboard()
        )
        for match in matches:
            match_name = match.name if isinstance(match, Path) else match[0].name
            await message.answer(f'Совпадение с: {match_name}', reply_markup=generate_keyboard_cancel_last_img())


# Функция для проверки aspect ratio и отправки сообщения
async def check_aspect_ratio(img_path, message):
    aspect_ratio = get_aspect_ratio(img_path)
    if not MAX_ASPECT_RATIO > aspect_ratio > MIN_ASPECT_RATIO:
        await message.answer(
            'Фотография узкая. Мы можем ее напечатать, но при размещении на карточке '
            'будет широкое белое поле. Рекомендуем откадрировать и загрузить снова.',
            reply_markup=generate_keyboard_cancel_last_img()
        )


# Функция для проверки размытия и отправки сообщения
async def check_blur(img_path, message):
    blur = estimate_blur(img_path)
    if blur < BLURR_THRESHOLD:
        await message.answer(
            'Изображение на фотографии слишком "размыто".',
            reply_markup=generate_keyboard_cancel_last_img()
        )


# Хэндлер для получения фотографий как документ  OrderStates.waiting_for_photos
@dp.message(F.content_type.in_({"document"}), OrderStates.waiting_for_photos)
async def process_photo_document(message: types.Message, state: FSMContext):
    processing_message = await message.answer("Идет обработка...")
    
    # Создаем задачу для process_photo
    task = asyncio.create_task(process_photo(message, state, is_document=True))
    
    try:
        # Ожидаем завершения задачи
        await asyncio.gather(task)
    except Exception as e:
        # Обрабатываем исключение
        await message.answer(f"Произошла ошибка при обработке: {e}")
    finally:
        # Удаляем сообщение "Идет обработка..."
        await processing_message.delete()
    
    # Отправляем сообщение о завершении обработки
    # await message.answer("Обработка завершена!")


# Хэндлер для получения фотографий как изображения, но не как файл
@dp.message(F.content_type.in_({"photo"}), OrderStates.waiting_for_photos)
async def handle_photo_as_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_number = data['order_number']
    ignore_warning = data.get('ignore_quality_warning', False)
    
    # Сохраняем данные фото в состояние, чтобы использовать позже при обработке callback
    # await state.update_data(last_photo=message.photo[-1].file_id)
    await state.update_data(last_photo_id=message.photo[-1].file_id)


    # Проверяем, показывать ли предупреждение о качестве
    if not ignore_warning:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Продолжить", callback_data=f"continue_upload:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Отменить фото", callback_data=f"cancel_photo_as_photo:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Отменить заказ", callback_data=f"cancel_order:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Больше не спрашивать", callback_data=f"ignore_warning:{order_number}")
                ]
            ]
        )    
        await message.answer(
            "Вы отправили фото не файлом, а изображением. Качество будет хуже.\nВыберите действие:",
            reply_markup=keyboard
        )
    else:
        await process_photo(message, state, is_document=False)


# Хэндлер для получения непонятного в режиме ожидания фотографий
@dp.message(OrderStates.waiting_for_photos)
async def handle_photo_as_unknown(message: types.Message, state: FSMContext):
        data = await state.get_data()
        order_number = data['order_number']
        await message.answer(
            "Пожалуйста, присылайте изображения.",
            reply_markup=generate_keyboard_cancel_order(order_number)
        )


@dp.callback_query(F.data.startswith("cancel_photo_as_photo:"))
async def cancel_photo_as_photo(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_number = data['order_number']
    # order_number = callback.data.split(":")[1]
    order_folder = data['order_folder']
    photos_in_order = data['number_of_photos']
    uploaded_photos  = get_number_photo_files(order_folder)
    
    await callback.answer("Фото отменено.")
    edit_keyboard = generate_edit_photo_keyboard(order_number)
    await bot.send_message(callback.message.chat.id, 
                           f"Загружено {uploaded_photos} фото из {photos_in_order}.\nЖду ещё", reply_markup=edit_keyboard)



# Обработчик кнопки "Больше не спрашивать"
@dp.callback_query(F.data.startswith("ignore_warning"))
async def ignore_warning(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(ignore_quality_warning=True)
    await callback.answer("Больше не буду предупреждать.")

    # Получаем file_id фото из состояния
    data = await state.get_data()
    photo_file_id = data.get('last_photo_id')
    
    if photo_file_id:
        await process_photo(callback.message, state, is_document=False, photo_file_id=photo_file_id)
   
   
# Обработчик кнопки "Продолжить"
@dp.callback_query(F.data.startswith("continue_upload:"))
async def continue_upload(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Продолжаю загрузку.")

    await bot.send_message(
        callback.message.chat.id, 
        '<i>Если в одном сообщении было отправлено несколько фото, загружено только последнее.\nДля загрузки сразу нескольких нажмите "Больше не спрашивать" и повторите отправку.</i>'
        )
    
    # Проверим, есть ли фото в callback.message
    if callback.message.photo:
        for photo in callback.message.photo:
            await process_photo(callback.message, state, is_document=False, photo_file_id=photo.file_id)
    else:
        # Если фото нет, нужно взять его из состояния (если оно было сохранено ранее)
        data = await state.get_data()
        photo_file_id = data.get('last_photo_id')
        
        if photo_file_id:
            # Если photo_file_id есть, передаем его для обработки
            await process_photo(callback.message, state, is_document=False, photo_file_id=photo_file_id)
           
                
# Общая функция для обработки фотографии, учитывая её тип
async def process_photo(message: types.Message, state: FSMContext, is_document: bool, photo_file_id=None):
    # Получаем данные о состоянии
    data = await state.get_data()
    order_folder = Path(data['order_folder'])
    number_of_photos = data['number_of_photos']
    order_number = data['order_number']

    # Получаем файл в зависимости от типа сообщения или переданного file_id
    if is_document:
        file = message.document
    elif photo_file_id:
        file = photo_file_id  # Используем переданный photo_file_id напрямую
    else:
        file = message.photo[-1].file_id  # Используем последнее фото, если передан массив фотографий

    # Скачиваем файл
    # logger.info(f'{file} Начинаю скачивание...')
    if isinstance(file, str):  # Если file - это строка (photo_file_id), обрабатываем его как есть
        file_id = file
        # original_filename = f"photo_{int(time() * 1000)}.jpg"  # Задаем имя, если файл передан как photo_file_id
        original_filename = f"photo.jpg"  # Задаем имя, если файл передан как photo_file_id
        logger.info(f'file is instance str {file_id=}, {original_filename=}')
    else:
        file_id = file.file_id
        # original_filename = file.file_name if is_document else f"photo_{int(time() * 1000)}.jpg"
        original_filename = file.file_name if is_document else f"photo.jpg"
        logger.info(f'file is NOT instance str {file_id=}, {original_filename=}')

    # Генерируем уникальное имя для файла
    filename_with_unique = generate_unique_filename(original_filename)
    file_path = order_folder / filename_with_unique
    logger.info(f'Unique name {filename_with_unique=}')

    # Скачиваем и сохраняем файл

    logger.info(f'Start downloading {filename_with_unique}...')
    await download_and_save_file(file_id, file_path)
    logger.info(f'Downloaded {filename_with_unique}')

    # Конвертируем, если это необходимо
    # logger.info(f'Converting {filename_with_unique}')
    img_path = convert_to_jpeg(file_path)
    if not img_path.exists():
        logger.error(f"File {img_path} doesn't exist after image conversion.")
        return

    # Обрабатываем фотографию
    # logger.info(f'process_image {filename_with_unique}...')
    uploaded_photos = await process_image(img_path, order_folder, order_number, number_of_photos, message)

    # Проверяем совпадения по MD5
    # logger.info(f'md5 matches {filename_with_unique}...')
    await check_md5_matches(img_path, order_folder, message)

    # Проверяем, завершен ли процесс загрузки фотографий
    if uploaded_photos >= number_of_photos:
        await state.set_state(OrderStates.order_complete)
        logger.info(f"All photos for order {order_number} by {message.from_user.id} uploaded.")

        if uploaded_photos >= number_of_photos:
            # Повторные проверки на соотношение сторон, качество и дубли
            for photo in order_folder.glob("*.{IMG_WORK_FORMAT}"):
                await check_aspect_ratio(photo, message)
                await check_blur(photo, message)
                await check_md5_matches(photo, order_folder, message)
        
        edit_cancel_send_keyboard = generate_edit_cancel_send_keyboard(order_number)
        await message.answer(f"Заказ сформирован. Отправляю в печать или ещё подумаете?", 
                             reply_markup=edit_cancel_send_keyboard)
    else:

        edit_keyboard = generate_edit_photo_keyboard(order_number)
        await message.answer(f"Получил {uploaded_photos} фото из {number_of_photos}. Жду ещё", reply_markup=edit_keyboard)
        

def generate_edit_cancel_send_keyboard(order_number): 
        # Клавиатура с вариантами действий
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Редактировать фото", callback_data=f"edit_photo:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Отменить заказ", callback_data=f"cancel_order:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Отправить в печать", callback_data=f"print_order:{order_number}")
                ]
            ]
        )


def generate_edit_photo_keyboard(order_number: str) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру с кнопкой "Редактировать фото".

    :param order_number: Номер заказа.
    :return: Объект InlineKeyboardMarkup.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Редактировать фото", callback_data=f"edit_photo:{order_number}")
            ],
            [
                InlineKeyboardButton(text="Отменить заказ", callback_data=f"cancel_order:{order_number}")
            ],
            [
                InlineKeyboardButton(text="Отправить в работу", callback_data=f"send_not_full_order:{order_number}")
            ]
        ]
    )


def generate_photo_block_keyboard(order_number: str, uploaded_photos: int, photos_in_order: int) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру с кнопками для выбора блока фотографий для редактирования.

    :param order_number: Номер заказа.
    :param uploaded_photos: Количество загруженных фотографий.
    :return: Объект InlineKeyboardMarkup.
    """
    keyboard = []
    block_size = 10
    total_blocks = (uploaded_photos + block_size - 1) // block_size  # Округление вверх
    
    # data = state.get_data()
    # order_folder = data['order_folder']
    # photos_in_order = data['number_of_photos']
    # uploaded_photos  = get_number_photo_files(order_folder)


    for block_number in range(1, total_blocks + 1):
        start_photo = (block_number - 1) * block_size + 1
        end_photo = min(block_number * block_size, uploaded_photos)
        button_text = f"Фото {start_photo}-{end_photo}"
        callback_data = f"edit_photo_block:{order_number}:{block_number}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton(text="Отменить всё", callback_data=f"cancel_order:{order_number}")])
    if uploaded_photos < photos_in_order:
        keyboard.append([InlineKeyboardButton(text="Отправить в работу неполный заказ", callback_data=f"send_not_full_order:{order_number}")])
    else:
        # keyboard.append([InlineKeyboardButton(text="Отправить в печать", callback_data=f"send_not_full_order:{order_number}")])
        keyboard.append([InlineKeyboardButton(text="Отправить в печать", callback_data=f"print_order:{order_number}")])


    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.callback_query(F.data.startswith("edit_photo:"))
async def handle_edit_photo(callback: types.CallbackQuery, state: FSMContext):
    # Разбираем callback данные
    _, order_number = callback.data.split(":")

    # Получаем данные о состоянии
    data = await state.get_data()
    order_folder = data['order_folder']
    uploaded_photos = get_number_photo_files(order_folder)
    photos_in_order = data['number_of_photos']

    # Генерируем клавиатуру с кнопками для выбора блока фотографий
    photo_block_keyboard = generate_photo_block_keyboard(order_number, uploaded_photos, photos_in_order)

    # Отправляем сообщение с клавиатурой
    # await callback.message.answer("Выберите блок фото для редактирования:", reply_markup=photo_block_keyboard)
    await bot.send_message(callback.message.chat.id, "Выберите блок фото для редактирования:", reply_markup=photo_block_keyboard)

    # Подтверждаем обработку коллбека
    await callback.answer()


async def edit_photo_block(callback: types.CallbackQuery, state: FSMContext):
    # Разбираем callback данные
    _, order_number, block_number = callback.data.split(":")
    block_number = int(block_number)

    # Получаем данные о состоянии
    data = await state.get_data()
    order_folder = data['order_folder']
    uploaded_photos = get_number_photo_files(order_folder)

    # Вычисляем диапазон фотографий для текущего блока
    block_size = 10
    start_photo = (block_number - 1) * block_size + 1
    end_photo = min(block_number * block_size, uploaded_photos)

    # Получаем список файлов в каталоге, отсортированный по имени (по времени загрузки)
    photo_files = sorted(order_folder.glob(f"*.{IMG_WORK_FORMAT}"))

    # print(f'{start_photo=}, {end_photo=}\n{photo_files=}')
    # Отправляем фотографии и информацию о них
    for i in range(start_photo - 1, end_photo):
        if i >= len(photo_files):
            break

        photo_path = photo_files[i]

        # Получаем информацию о файле
        file_name = photo_path.name
        # file_size = photo_path.stat().st_size
        aspect_ratio = get_aspect_ratio(photo_path)
        blur = estimate_blur(photo_path)
        matches = find_matching_files_by_md5(order_folder, photo_path)

        # Формируем текст с информацией о файле
        file_info = (
            f"Имя файла: {file_name}\n"
            # f"Размер: {file_size} байт\n"
            f"Соотношение сторон: {aspect_ratio:.2f}\n"
            f"Качество: {blur:.2f}\n"
            f"Совпадения с другими файлами: {', '.join(matches) if matches else 'Нет'}"
        )
        logger.info(f'Order {order_number}, edit photo: {file_info}')
        # Создаем клавиатуру с кнопкой "удалить фото"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Удалить фото", callback_data=f"delete_photo:{order_number}:{i + 1}")
                ]
            ]
        )

        photo_file = FSInputFile(str(photo_path))  
        await callback.message.answer_photo(photo_file, caption=file_info, reply_markup=keyboard)


    # Подтверждаем обработку коллбека
    await callback.answer()


@dp.callback_query(F.data.startswith("edit_photo_block:"))
async def handle_edit_photo_block(callback: types.CallbackQuery, state: FSMContext):
    await edit_photo_block(callback, state)
    # _, order_number= callback.data.split(":") was ValueError: too many values to unpack (expected 2)
    
    # Разбиваем callback.data на части
    parts = callback.data.split(":")
    order_number = parts[1]
    block_number = parts[2]
    
    data = await state.get_data()
    order_folder = data['order_folder']
    number_of_photos = data['number_of_photos']
    uploaded_photos = get_number_photo_files(order_folder)
    if uploaded_photos < data['number_of_photos']:
        edit_keyboard = generate_edit_photo_keyboard(order_number)
        await bot.send_message(
                callback.message.chat.id, 
                f"Получил {uploaded_photos} фото из {number_of_photos}. Жду ещё", 
                reply_markup=generate_edit_cancel_send_keyboard(order_number)
            )        


@dp.callback_query(F.data.startswith("delete_photo:"))
async def delete_photo(callback: types.CallbackQuery, state: FSMContext):
    # Разбираем callback данные
    _, order_number, photo_index = callback.data.split(":")
    photo_index = int(photo_index)

    # Получаем данные о состоянии
    data = await state.get_data()
    order_folder = data['order_folder']
    number_of_photos = data['number_of_photos']

    # Получаем список файлов в каталоге, отсортированный по имени (по времени загрузки)
    photo_files = sorted(order_folder.glob(f"*.{IMG_WORK_FORMAT}"))

    # Проверяем, существует ли файл с указанным индексом
    if 1 <= photo_index <= len(photo_files):
        photo_path = photo_files[photo_index - 1]
        photo_path.unlink()  # Удаляем файл
        await callback.message.answer(f"Фото {photo_index} удалено.")
        logger.info(f"Photo {photo_index} deleted by user {callback.from_user.id}.")
    else:
        await callback.message.answer("Ошибка: фото с таким номером не найдено.")
        logger.warning(f"Photo {photo_index} not found for user {callback.from_user.id}.")

    # Обновляем состояние заказа
    uploaded_photos = get_number_photo_files(order_folder)
    if uploaded_photos < data['number_of_photos']:
        await state.set_state(OrderStates.waiting_for_photos)
        await callback.message.answer("Ожидаю ещё фото.")

        edit_keyboard = generate_edit_photo_keyboard(order_number)
        await bot.send_message(callback.message.chat.id, 
            f"Загружено {uploaded_photos} фото из {number_of_photos}. Жду ещё", reply_markup=edit_keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("send_not_full_order:"))
async def send_not_full_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    data = await state.get_data()
    order_folder = data['order_folder']
    photos_in_order = data['number_of_photos']
    uploaded_photos  = get_number_photo_files(order_folder)

    # Проверяем, завершен ли процесс загрузки фотографий
    if uploaded_photos < photos_in_order:
        # await state.set_state(OrderStates.order_complete)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Продолжить загрузку фотографий", callback_data=f"continue_load_photo:{order_number}")
                ],
                [
                    InlineKeyboardButton(text="Отправить неполный заказ", callback_data=f"print_order:{order_number}")
                ]
            ]
        )
        await bot.send_message(callback.message.chat.id, 
                               f'У вас ещё не загружено {photos_in_order-uploaded_photos} фотографий. Деньги не возвращаются',
                               reply_markup=keyboard)
    else:
        await process_print_order(callback, state)


@dp.callback_query(F.data.startswith("continue_load_photo:"))
async def continue_load_photo(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    data = await state.get_data()
    order_folder = data['order_folder']
    photos_in_order = data['number_of_photos']
    uploaded_photos  = get_number_photo_files(order_folder)

    await state.set_state(OrderStates.waiting_for_photos)
    # await bot.send_message(callback.message.chat.id, 
                            # f'Ожидаю фотографии.')

    edit_keyboard = generate_edit_photo_keyboard(order_number)
    await bot.send_message(callback.message.chat.id, 
                           f"Получил {uploaded_photos} фото из {photos_in_order}. Жду ещё", reply_markup=edit_keyboard)


@dp.callback_query(F.data.startswith("cancel_last_photo:"))
async def cancel_last_photo(callback: CallbackQuery, state: FSMContext):
    # order = callback.data.split(":")[1]
    data = await state.get_data()
    order_folder = data['order_folder']
    photos_in_order = data['number_of_photos']

    path = Path(order_folder)
    
    # Проверяем, существует ли каталог и является ли он каталогом
    if not path.exists() or not path.is_dir():
        logger.error(f"Path {order_folder} not exist or not directory.")
    
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
     

# Хэндлер для обработки callback "Отправить в печать"
@dp.callback_query(F.data.startswith("print_order:"))
async def process_print_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]   
    logger.info(f"Order {order_number} marked for printing by user {callback.from_user.id}")
    await callback.message.answer("Заказ отправлен в печать.")
    await callback.answer()
    await bot.send_message(chat_id=MANAGER_TELEGRAM_ID, text=f"Сообщение менеджеру: Заказ {order_number} собран и подтверджен, надо печатать.")
    await state.update_data({}) # Сброс данных состояния    
    await cmd_start(callback.message, state)
    

# Хэндлер для обработки callback "Отменить"
@dp.callback_query(F.data.startswith("cancel_order:"))
async def process_cancel_order(callback: CallbackQuery, state: FSMContext):
    order_number = callback.data.split(":")[1]
    logger.info(f"Order {order_number} canceled by user {callback.from_user.id}")
    await state.set_state(OrderStates.waiting_for_order_number)
    # await callback.message.answer("Данные заказа сброшены.")
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
    logger.info(f"Starting {__name__}...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
