# Photo Print shop helper Bot

## Description

The Photo Print Bot is a Telegram bot designed to facilitate the collection and processing of photos for print orders. This bot enables users to upload multiple images simultaneously, convert them into the appropriate format (JPEG), and retrieve their aspect ratios. It provides a user-friendly interface and efficient file handling to streamline the ordering process for print services.

## Features

- **Multi-File Upload**: Users can send one or multiple photos in a single message.
- **Automatic File Conversion**: Uploaded files are automatically converted to JPEG format if they are not already in that format.
- **Aspect Ratio Calculation**: The bot calculates and displays the aspect ratio of each uploaded image.
- **State Management**: Utilizes finite state machines to manage the state of the order process.
- **Inline Keyboard Integration**: Provides options for users to either send the order for printing or cancel it.
- **Logging**: Comprehensive logging of user interactions and processes for debugging and tracking purposes.

## Interface prototype
<img width="859" alt="image" src="https://github.com/user-attachments/assets/9472c7b4-7e86-4fa6-a6cd-5a040560874f">


## Installation

### Шаг 1: Клонирование репозитория
```bash
git clone https://github.com/TDHster/Idea_print_bot.git
cd Idea_print_bot
```

### Шаг 2: Создание виртуального окружения 
```bash
python -m venv venv
```
Активируйте виртуальное окружение:
Для PowerShell:
```bash
.\venv\Scripts\Activate.ps1
```
Для командной строки (cmd):
```bash
.\venv\Scripts\activate.bat
```

### Шаг 3: Установка зависимостей
```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка переменных окружения 
Создайте файл .env в корневой директории проекта и добавьте необходимые переменные:

```bash
BOT_API=
ALLOWED_PATH=C:\\1C\\
API_URL = "http://localhost:8000/markets/hs/api_bot/getpath/"
ERROR_MESSAGE_FOR_USER = "Приношу свои извинения, у нас технический сбой.\nПопробуйте позже или свяжитесь с нашим менеджером по телефону +74951113322"
MANAGER_TELEGRAM_ID=здесь_цифры_айди_пользователя (можно узнать через @idbot)
```
### Шаг 5: Запуск бота
```bash
python ideaprint_bot.py
```

## Usage
Once the bot is running, users can start interacting with it through Telegram. They can send their photos for printing, and the bot will handle the rest by saving, converting, and calculating the aspect ratios.

