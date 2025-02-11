# Проект под тестовое задание.

## Задание
Написать docker-compose, в котором работают:
web приложение, на FastApi. У приложения должно быть два ендпоинта:
1) GET 'api/v1/messages/' показывает список всех сообщений;
2) POST 'api/v1/message/' позволяет написать сообщение;
Веб сервер должен быть Nginx.
Mongo как БД для сообщений.
Телеграм бот (aiogram3), который показывает сообщения и позволяет создать сообщение самому.
Будет плюсом:
1) Добавление кэширования при помощи Redis (кеш стирается, когда появляется новое сообщение)
2) Развертывание на удалённом сервере и добавление ssl через certbot.
3) Реализовать код так, чтобы было видно, кто написал сообщение.
4) Добавление пагинации.

## Реализовано
Составлен docker-compose.yml с 5-ю сервисами:
- api - для FastAPI
- db - для MongoDB
- redis
- nginx
- bot - для телеграм-бота

Код для FastAPI в папке web/api

В нем реализовано получение сообщений из MongoDB (или из кэша Redis, если он доступен) по запросу GET 'api/v1/messages/'. Проверить работу можно запустив:
```
curl -X GET http://localhost/api/v1/messages/
```
или если нужно получить данные с пагинацией, то:
```
curl -X GET "http://localhost/api/v1/messages/?page=2&limit=2"
```
Также реализована запись сообщения в БД с помощью запроса POST 'api/v1/message/', который также очищает кэш Redis. Проверить работу можно запустив:
```
curl -X POST http://localhost/api/v1/message/ \
-H "Content-Type: application/json" \
-d '{"message": "Hello from API!"}'
```

Конфигурация Nginx находится в файле nginx/default.conf

Код телеграм-бота расположен в папке bot/

В нем реализована обработка комманды /start с выдачей списка доступных команд. Также команды /add за которой должно следовать сообщение, которое запишется в БД. И команды /list которая покажет 10 первых сообщений из БД, если она передана без параметров. Если добавить параметры /list page 2 limit 10, то будет использоваться пагинация по 10 элементов, и выведется 2-я страница. На все другие сообщения бот реагирует эхо-ответом, просто для проверки что он в активен. Токен бота можно передать с помощью файла .env который нужно разместить в корне проекта, с таким содержимым:
```
TOKEN_API_BOT=9999999999:AAAAAAAAAAAAA_CCCCCCCCCCCCCCCCCCCCC  
```
или передать с переменной окружения ОС с именем TOKEN_API_BOT.

Старт проекта производится с помощью:
```
docker compose up --build
```