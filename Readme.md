Старт:
```
sudo docker compose up --build
```

Получить все сообщения:
```
curl -X GET http://localhost/api/v1/messages/
```

Добавить сообщение:
```
curl -X POST http://localhost/api/v1/message/ \
-H "Content-Type: application/json" \
-d '{"message": "Hello from API!"}'
```