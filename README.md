# Robokassa Readiness Skill

Скилл для Claude Code / Codex — проверяет публичный сайт или локальный HTML на готовность к модерации Робокассы.

## Структура

| Файл | Назначение |
|------|------------|
| `SKILL.md` | Описание триггеров и workflow для Claude Code |
| `scripts/check_robokassa_readiness.py` | Standalone чекер (без внешних зависимостей) |
| `references/configuration.md` | Поля конфига и примеры для разных типов продавцов |
| `agents/openai.yaml` | UI-метаданные для OpenAI-агентов |

## Что проверяет (24 проверки)

**Страницы:** наличие `index.html`, `about.html`, `offer.html`, `terms.html`, `privacy.html`, `faq.html`

**Лендинг (index.html):**
- ссылки на юридические страницы (проверяет `href`, а не подстроку)
- тарифы (ценовые маркеры)
- ФИО продавца (полное, без инициалов)
- ИНН (12 цифр для самозанятого)
- email и телефон поддержки
- wording про checkout flow (Telegram, бот, оплата)
- отсутствие `пробный период`

**Оферта (offer.html):** ФИО, ИНН, email, условия возврата, условия оказания услуги

**О проекте (about.html):** email, ИНН

**Условия (terms.html):** ссылка на оферту, отсутствие `пробный период`

**Конфиденциальность (privacy.html):** идентификация оператора

## Дефолтный пресет

Строгий, для **самозанятого в РФ** с цифровым продуктом:

- полное ФИО без инициалов и точек
- 12-значный ИНН
- российский формат телефона (`+7` / `8`)
- checkout через Telegram-бота
- 6 обязательных HTML-страниц

Если ваш кейс другой (ИП, ООО, сайт-checkout, другие имена файлов) — используйте JSON-конфиг.

## Использование

```bash
# Проверка локального HTML
python3 scripts/check_robokassa_readiness.py --path data/html

# Проверка живого сайта
python3 scripts/check_robokassa_readiness.py --url https://example.com

# JSON-вывод (для CI/CD и автоматизации)
python3 scripts/check_robokassa_readiness.py --url https://example.com --json

# Показать дефолтный конфиг
python3 scripts/check_robokassa_readiness.py --print-default-config

# Кастомный конфиг
python3 scripts/check_robokassa_readiness.py \
  --config robokassa-readiness.json \
  --url https://example.com
```

### Пример вывода

```
Robokassa Readiness Check
========================================
  [OK] index.html exists
  [OK] about.html exists
  ...
  [FAIL] offer.html: seller name not found, placeholder, or abbreviated
  [OK] offer.html: seller INN found
========================================
Result: 22/24 checks passed
Status: NOT READY
```

При `--json`:

```json
{
  "passed": 22,
  "total": 24,
  "ready": false,
  "checks": [
    {"ok": true, "message": "index.html exists"},
    {"ok": false, "message": "offer.html: seller name not found, placeholder, or abbreviated"}
  ]
}
```

### Обработка ошибок сети

При недоступности сайта чекер выводит предупреждения в stderr:

```
  [WARN] could not fetch https://example.com/index.html: <urlopen error ...>
```

HTTP 404 обрабатывается тихо (страница просто отсутствует). DNS-ошибки, таймауты и SSL-проблемы — с предупреждением.

## Конфигурация

Подробности: [references/configuration.md](references/configuration.md).

Ключевые поля:

| Поле | Что меняет |
|------|------------|
| `seller_name_mode` | `full_name` / `any_non_placeholder` / `skip` |
| `seller_id_patterns` | Регулярки для ИНН/ОГРН |
| `phone_patterns` | Формат телефона |
| `required_pages` | Список обязательных страниц |
| `index_purchase_keywords_all` | Wording о способе покупки |
| `price_markers` | Числа тарифов на лендинге |

## Установка как скилл

### Claude Code

```bash
cp -R robokassa-readiness ~/.claude/skills/robokassa-readiness
```

Или установите `.skill`-файл:

```bash
# если есть robokassa-readiness.skill
claude skill install robokassa-readiness.skill
```

### Codex

```bash
cp -R robokassa-readiness ~/.codex/skills/robokassa-readiness
```

## Важно

Это детерминированный smoke test, **не** официальный валидатор Робокассы. Если нужно проверить соответствие актуальным требованиям — сначала сверьтесь с официальной документацией Робокассы, а чекер используйте для аудита самого сайта.

## Лицензия

MIT
