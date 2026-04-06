---
name: robokassa-readiness
description: Invoke whenever the user mentions робокасса or robokassa in any form. Invoke when the user asks to write, review, or check an оферта, политика конфиденциальности, условия возврата, or any legal/compliance page needed for selling products or services online. Invoke when checking a site or URL before connecting a payment gateway — even without naming Robokassa. Invoke for questions about ИНН, реквизиты, or seller info requirements on landing pages. Covers drafting legal documents for digital and physical products (subscriptions, bots, courses, SaaS), auditing HTML or live sites, and advising on moderation readiness. Supports ИП, ООО, самозанятый. Not for Stripe, Тинькофф, general web dev, or non-payment tasks.
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
- `--diff URL` for comparing local HTML against a live site (requires `--path`)
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

The checker assigns severity automatically:

- **blocker** — must fix before moderation: missing pages, missing requisites, abbreviated seller name, missing legal links, no refund wording, HTTP (not HTTPS), missing offer structure sections.
- **warning** — should clarify for manual review: delivery wording, checkout-flow wording, trial language, short page content, tariff markers.
- **ok** — check passed.

Treat this skill as a deterministic smoke test. Do not present it as Robokassa's official approval mechanism.
If a project uses non-self-employed seller data, make the config explicit in the answer so future reviewers can see why the checker passed.

## Output

Results are grouped by severity (blockers first, then warnings, then passed). Terminal output is color-coded (red for blockers, yellow for warnings, green for OK) when connected to a TTY.

`--json` output includes `blockers` and `warnings` counts plus `severity` per check.

`--diff` output shows only differences between local and remote, ignoring natural variation like content length.
