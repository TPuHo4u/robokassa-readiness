# Robokassa Readiness Skill

Configurable Codex skill for auditing a public site or generated HTML for Robokassa moderation readiness.

The repository contains:

- `SKILL.md` — trigger description and workflow for Codex
- `agents/openai.yaml` — UI metadata
- `scripts/check_robokassa_readiness.py` — standalone checker
- `references/configuration.md` — config fields and examples

## What It Checks

- required public pages
- legal links on the landing page
- seller requisites
- support email and phone
- tariff markers
- refund wording
- delivery wording
- checkout-flow wording
- trial-language regressions

## Default Preset

The default config is intentionally strict for a Russian self-employed digital product:

- full seller name without initials
- 12-digit seller INN
- Russian phone pattern
- `index.html`, `about.html`, `offer.html`, `terms.html`, `privacy.html`, `faq.html`
- checkout explained as happening in a Telegram bot

If your project differs, use a JSON config instead of editing the script first.

## Usage

Local generated HTML:

```bash
python3 scripts/check_robokassa_readiness.py --path data/html
```

Live site:

```bash
python3 scripts/check_robokassa_readiness.py --url https://example.com
```

Print the default config:

```bash
python3 scripts/check_robokassa_readiness.py --print-default-config
```

Run with a custom config:

```bash
python3 scripts/check_robokassa_readiness.py \
  --config robokassa-readiness.json \
  --url https://example.com
```

## Config

See [references/configuration.md](references/configuration.md).

The most useful overrides are:

- `seller_name_mode`
- `seller_id_patterns`
- `seller_id_label`
- `phone_patterns`
- `about_page`, `faq_page`, `required_pages`
- `required_link_targets_on_index`
- `required_link_targets_on_terms`

## Use As A Codex Skill

Copy the folder into your skills directory:

```bash
cp -R robokassa-readiness ~/.codex/skills/robokassa-readiness
```

Or clone the repository directly into `~/.codex/skills/`.

## Important

This is a deterministic smoke test, not an official Robokassa validator. If a user asks whether a site meets the latest Robokassa requirements, verify the current official Robokassa rules first and then use this checker to inspect the actual site.
