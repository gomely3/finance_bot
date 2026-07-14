import os
from dotenv import load_dotenv
from pathlib import Path

# Указываем путь к файлу .env
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Загружаем переменные
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///finance.db')

# Проверяем, что токен загружен
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в файле .env. Проверьте наличие файла .env и правильность токена.")