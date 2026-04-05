# Robokassa Readiness Skill

Переиспользуемый Codex skill для проверки публичного сайта или сгенерированного HTML на готовность к модерации Robokassa.

В репозитории лежат:

- `SKILL.md` — описание триггеров и workflow для Codex
- `agents/openai.yaml` — UI-метаданные
- `scripts/check_robokassa_readiness.py` — standalone checker
- `references/configuration.md` — поля конфига и примеры

## Что проверяет

- наличие обязательных публичных страниц
- ссылки на юридические страницы на лендинге
- реквизиты продавца
- email и телефон поддержки
- тарифы
- условия возврата
- условия оказания услуги
- wording про checkout flow
- регрессии вроде `trial language`

## Дефолтный пресет

Дефолтная конфигурация специально сделана строгой для цифрового продукта самозанятого в РФ:

- полное ФИО без инициалов
- 12-значный ИНН
- российский формат телефона
- страницы `index.html`, `about.html`, `offer.html`, `terms.html`, `privacy.html`, `faq.html`
- wording о том, что оплата происходит через Telegram-бота

Если ваш кейс другой, лучше использовать JSON-конфиг, а не редактировать скрипт вручную.

## Использование

Проверка локально по сгенерированному HTML:

```bash
python3 scripts/check_robokassa_readiness.py --path data/html
```

Проверка живого сайта:

```bash
python3 scripts/check_robokassa_readiness.py --url https://example.com
```

Показать дефолтный конфиг:

```bash
python3 scripts/check_robokassa_readiness.py --print-default-config
```

Запуск с кастомным конфигом:

```bash
python3 scripts/check_robokassa_readiness.py \
  --config robokassa-readiness.json \
  --url https://example.com
```

## Конфиг

См. [references/configuration.md](references/configuration.md).

Самые полезные override-поля:

- `seller_name_mode`
- `seller_id_patterns`
- `seller_id_label`
- `phone_patterns`
- `about_page`, `faq_page`, `required_pages`
- `required_link_targets_on_index`
- `required_link_targets_on_terms`

## Как использовать как Codex skill

Скопируйте папку в директорию skills:

```bash
cp -R robokassa-readiness ~/.codex/skills/robokassa-readiness
```

Или клонируйте репозиторий прямо в `~/.codex/skills/`.

## Важно

Это детерминированный smoke test, а не официальный валидатор Robokassa. Если нужно ответить, соответствует ли сайт актуальным требованиям Robokassa, сначала проверьте текущие официальные требования, а потом используйте этот checker для аудита самого сайта.

## Лицензия

MIT
