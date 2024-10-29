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

## Installation

#### Clone the repository:
   ```bash
   git clone https://github.com/yourusername/photo-print-bot.git
Navigate to the project directory:
```bash
cd photo-print-bot
```
#### Install the required dependencies:

```bash
pip install -r requirements.txt
```
#### Set up your Telegram bot token in the environment variables or configuration file.

Run the bot:

```bash
python bot.py
```
## Usage
Once the bot is running, users can start interacting with it through Telegram. They can send their photos for printing, and the bot will handle the rest by saving, converting, and calculating the aspect ratios.

