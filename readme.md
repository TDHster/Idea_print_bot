## Photo Print shop helper Bot

Idea Print Bot is a Telegram bot designed to streamline the process of collecting and processing photos for orders at the "Idea Print" printing house. The bot allows users to upload photos, check their quality, and manage orders.

### Key Features
#### Photo Collection:

Users can upload photos as files or images.

The bot automatically checks the quality of the photos, including aspect ratio and blurriness.

#### Order Management:

Users can enter their order number to access and manage their order.

The bot provides a user-friendly interface for editing, deleting, and reviewing uploaded photos.

#### Quality Control:

The bot checks for duplicate photos using MD5 hash comparisons.

It also verifies the aspect ratio and blurriness of the photos to ensure print quality.

#### Order Completion:

Once all photos are uploaded and verified, users can mark the order as complete and ready for printing.

The bot sends a notification to the manager when an order is ready for printing.



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

