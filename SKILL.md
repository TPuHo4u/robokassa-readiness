---
name: robokassa-readiness
description: Audit a site or generated HTML for Robokassa moderation readiness. Use whenever the user mentions Robokassa, payment moderation, payment gateway approval, or asks to check whether a public landing page is ready for accepting payments. Also trigger when the user says "проверь сайт перед подключением оплаты", "что нужно для модерации", "подготовить сайт к оплате", "робокасса модерация", or asks about missing legal pages, offer/terms/privacy compliance, or seller requisites on a landing page — even if they don't mention Robokassa by name but clearly need a payment-surface readiness check. The bundled checker ships with a strict Russian self-employed preset, but supports configuration for other seller types, page names, and checkout wording.
---

# Robokassa Readiness

Use the bundled checker instead of re-deriving the same landing-page checklist by hand.

This skill is for fast readiness audits of a public payment surface: landing page, offer, terms, privacy page, requisites, tariffs, refund wording, delivery terms, and checkout-flow wording. The default config is intentionally strict for a Russian self-employed digital product. Adjust it for other seller types or site structures instead of editing the script first.

It is not an official Robokassa validator, so when the user asks about the latest requirements, verify the current Robokassa rules first and then use this skill to check the actual site.

## Quick Start

Pick the source to inspect:

- Local generated HTML:

```bash
python3 <path-to-skill>/scripts/check_robokassa_readiness.py --path data/html
```

- Live site:

```bash
python3 <path-to-skill>/scripts/check_robokassa_readiness.py --url https://example.com
```

- Default config template:

```bash
python3 <path-to-skill>/scripts/check_robokassa_readiness.py --print-default-config
```

- Custom project config:

```bash
python3 <path-to-skill>/scripts/check_robokassa_readiness.py \
  --config robokassa-readiness.json \
  --url https://example.com
```

## Workflow

1. Identify the scope: local generated HTML or live URL.
2. Decide whether the default config fits. If seller type, page names, legal-link structure, tariffs, phone format, tax-id format, or checkout wording differ, create a JSON config first. See `references/configuration.md`.
3. Run the checker.
4. Read failures as concrete action items for the landing/legal pages.
5. If the user asks for compliance against the latest Robokassa policy, compare the findings with the current official Robokassa pages before making a final claim.

## scripts/

Use `scripts/check_robokassa_readiness.py` as the canonical implementation. It supports:

- `--path` for local generated HTML
- `--url` for a live public site
- `--config` for JSON overrides
- `--json` for machine-readable output (CI pipelines, other skills)
- `--print-default-config` to bootstrap reuse in another project

The highest-value overrides are:

- `seller_name_mode`
- `seller_id_patterns` and `seller_id_label`
- `phone_patterns`
- `about_page`, `faq_page`, `required_pages`
- `required_link_targets_on_index`, `required_link_targets_on_terms`

## references/

Read `references/configuration.md` only when the default assumptions do not fit or when you need to explain which fields another team should customize.

## Interpretation Rules

- Treat missing pages, missing requisites, abbreviated seller name, and missing offer/terms/privacy links as moderation blockers.
- Treat delivery wording and checkout-flow wording as clarity blockers: they often matter during manual review even when the code or payment flow already works.
- Treat this skill as a deterministic smoke test. Do not present it as Robokassa's official approval mechanism.
- If a project uses non-self-employed seller data, make the config explicit in the answer so future reviewers can see why the checker passed.

## Output

When reporting results, group findings into:

- `must fix before moderation`
- `should clarify for manual review`
- `already compliant`
