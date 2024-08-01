FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Копирование исходного кода
COPY . /app

# Запуск бота
CMD ["python", "bot.py"]
