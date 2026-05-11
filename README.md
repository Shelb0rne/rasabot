# HRBot для первичного интервью

HRBot - это MVP Telegram-бота для первой линии подбора в команду ML-проекта. Бот проводит короткое структурированное интервью, собирает первичную информацию о кандидате и помогает понять, на какую из ролей кандидат потенциально подходит.

Проект сделан на Rasa и работает через Telegram. После интервью бот отправляет итоговый отчет в отдельный админский чат: данные кандидата, Telegram-ник, выбранную роль, опыт, зарплатные ожидания, ответы на вопросы и предварительное заключение.

Важно: это MVP, а не полноценная HR-система. Бот помогает отфильтровать кандидатов на первом этапе, но финальное решение должен принимать человек.

## Какие роли проверяет бот

- Project Manager - координация команды и взаимодействие с бизнесом.
- Data Analyst - анализ данных и формулирование бизнес-требований.
- Data Engineer - пайплайны сбора, обработки и подготовки данных.
- Data Scientist - разработка и улучшение ML-моделей.
- MLOps Engineer - инфраструктура, деплой и production-окружение моделей.

Если кандидат не подходит ни на одну из ролей или у него недостаточно опыта, бот завершает интервью и формирует соответствующее заключение.

## Что собирает бот

- имя кандидата;
- Telegram-профиль кандидата;
- интересующую роль;
- опыт работы;
- ожидаемую зарплату;
- ключевые навыки;
- релевантный проектный опыт;
- ответы на ролевые вопросы;
- информацию о коммуникации и работе с командой;
- предварительную оценку и рекомендацию для HR.

## Структура репозитория

```text
.
├── actions/
│   ├── __init__.py
│   └── actions.py
├── custom_channels/
│   ├── __init__.py
│   └── fixed_telegram.py
├── data/
│   ├── nlu.yml
│   ├── rules.yml
│   └── stories.yml
├── scripts/
│   ├── start_action_server.ps1
│   └── start_rasa_server.ps1
├── tests/
│   └── test_stories.yml
├── config.yml
├── credentials.yml
├── domain.yml
├── endpoints.yml
├── .env.example
└── README.md
```

### Основные файлы

- `domain.yml` - домен Rasa: интенты, сущности, слоты, формы, ответы и кастомные actions.
- `data/nlu.yml` - обучающие примеры для распознавания интентов.
- `data/stories.yml` - примеры диалогов для обучения поведения бота.
- `data/rules.yml` - правила, которые должны выполняться стабильно.
- `actions/actions.py` - основная бизнес-логика: валидация формы, разбор опыта, ролевые вопросы, оценка кандидата и отправка отчета админу.
- `custom_channels/fixed_telegram.py` - кастомный Telegram-канал для Rasa.
- `credentials.yml` - подключение каналов Rasa, включая Telegram.
- `endpoints.yml` - настройки подключения Rasa к action server.
- `config.yml` - настройки NLU pipeline и dialogue policies.
- `scripts/start_action_server.ps1` - запуск action server.
- `scripts/start_rasa_server.ps1` - запуск Rasa server с Telegram-каналом.
- `tests/test_stories.yml` - тестовые диалоги.
- `.env.example` - пример переменных окружения.

## Переменные окружения

Создайте файл `.env` на основе `.env.example` и заполните значения:

```env
TELEGRAM_BOT_TOKEN=123456789:replace_with_botfather_token
TELEGRAM_BOT_USERNAME=your_bot_username_without_at
TELEGRAM_WEBHOOK_URL=https://your-public-url/webhooks/telegram/webhook
ADMIN_CHAT_ID=123456789
```

Описание:

- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота из BotFather.
- `TELEGRAM_BOT_USERNAME` - username бота без символа `@`.
- `TELEGRAM_WEBHOOK_URL` - публичный HTTPS-адрес webhook. (Для локальной разработки удобно использовать ngrok.)
- `ADMIN_CHAT_ID` - id Telegram-чата, куда бот отправляет результаты интервью.


## Подготовка Telegram

1. Создайте бота через BotFather.
2. Скопируйте токен в `TELEGRAM_BOT_TOKEN`.
3. Укажите username бота в `TELEGRAM_BOT_USERNAME` без `@`.
4. Узнайте chat id админского чата и запишите его в `ADMIN_CHAT_ID`.
5. Запустите публичный HTTPS-туннель на локальный порт Rasa `5005`.

Пример для ngrok:

```powershell
ngrok http 5005
```

После запуска ngrok возьмите HTTPS-адрес и добавьте к нему путь:

```text
https://your-ngrok-url.ngrok-free.app/webhooks/telegram/webhook
```

Именно это значение нужно записать в `TELEGRAM_WEBHOOK_URL`.

## Запуск проекта

Перед запуском активируйте виртуальное окружение:

```powershell
.\.venv\Scripts\Activate.ps1
```

Если модель еще не обучена или вы меняли `domain.yml`, `data/nlu.yml`, `data/stories.yml`, `data/rules.yml`, выполните:

```powershell
rasa train
```

Дальше нужно открыть два терминала.

### Терминал 1: action server

```powershell
.\scripts\start_action_server.ps1
```

Action server нужен для кастомной логики из `actions/actions.py`: формы интервью, проверки опыта, оценки ответов и отправки отчета админу.

### Терминал 2: Rasa server

```powershell
.\scripts\start_rasa_server.ps1
```

Rasa server поднимает основного бота и регистрирует Telegram webhook.

После запуска напишите боту в Telegram `/start` или начните интервью обычным сообщением.

## Проверка и обучение

Проверить корректность данных Rasa:

```powershell
rasa data validate
```

Переобучить модель:

```powershell
rasa train
```

Запустить core-тесты:

```powershell
rasa test core --stories tests\test_stories.yml
```


## Текущий статус

Проект находится в состоянии MVP. Уже реализованы:

- Telegram-интеграция;
- интервью через Rasa form;
- сбор основной информации о кандидате;
- раннее завершение интервью при недостатке опыта;
- ролевые вопросы для ML-команды;
- автоматическая предварительная оценка;
- отправка результатов в админский Telegram-чат.

Дальнейшие улучшения могут включать более точную scoring-модель, расширение NLU-примеров, хранение результатов в базе данных и отдельную HR-панель для просмотра кандидатов.
