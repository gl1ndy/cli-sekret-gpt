# Groq API Worker для Cloudflare

Это API без HTML-страницы. Worker принимает POST с запросом и паролем, обращается к Groq и возвращает JSON.

## Установка и публикация

```bash
npm install
npx wrangler login
npx wrangler secret put GROQ_API_KEY
npx wrangler secret put API_PASSWORD
npm run deploy
```

`GROQ_API_KEY` — ключ из панели Groq. `API_PASSWORD` — пароль, который должен знать клиент вашего API.

Для локального запуска скопируйте `.dev.vars.example` в `.dev.vars`, заполните значения и выполните:

```bash
npm run dev
```

## Запрос

Рекомендуемый способ — пароль в заголовке `Authorization`:

```bash
curl -X POST "https://groq-password-api.<ваш-субдомен>.workers.dev" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ваш_пароль" \
  -d '{"prompt":"Объясни простыми словами, что такое API"}'
```

Также пароль можно передать в JSON как `password`, но заголовок безопаснее для логов и прокси:

```json
{
  "password": "ваш_пароль",
  "prompt": "Напиши короткое приветствие"
}
```

Дополнительные поля:

```json
{
  "prompt": "Сделай краткое резюме текста",
  "system": "Отвечай на русском языке",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

Успешный ответ:

```json
{
  "answer": "...",
  "model": "openai/gpt-oss-120b",
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 30,
    "total_tokens": 50
  }
}
```

Все ошибки также возвращаются в JSON. Пароль и Groq API key не пересылаются в Groq: Worker использует пароль только для проверки, а в Groq отправляет только запрос пользователя.
