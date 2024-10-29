
from dotenv import dotenv_values

config = dotenv_values(".env")
BOT_TOKEN = config['BOT_API']
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, setup_dialogs
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message
from aiogram.dispatcher.router import Router

# Определение группы состояний для диалога
class MyDialogStates(StatesGroup):
    start = State()
    end = State()

# Создание экземпляров бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()  # Создаем роутер
dp.include_router(router)

# Обработчик для ввода имени
async def on_name_received(message: Message, dialog_manager: DialogManager):
    dialog_manager.dialog_data['name'] = message.text
    await dialog_manager.next()  # Переход к следующему шагу

# Создание диалога с использованием состояний из StatesGroup
dialog = Dialog(
    Window(
        Const("Введите ваше имя:"),
        MessageInput(on_name_received),
        state=MyDialogStates.start,
    ),
    Window(
        Const("Привет, {name}!"),
        state=MyDialogStates.end
    )
)

# Настройка диалогов через setup_dialogs
setup_dialogs(dp, [dialog])

# Обработчик команды /start для запуска диалога
@router.message(commands=["start"])
async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(state=MyDialogStates.start, mode=StartMode.RESET_STACK)

# Асинхронная функция для запуска бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)  # Очищаем все необработанные обновления
    await dp.start_polling(bot)  # Запуск polling режима

# Запуск бота
if __name__ == "__main__":
    asyncio.run(main())
