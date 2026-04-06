# Configuration

Use the bundled checker with default settings when the project matches a typical Russian self-employed digital product submitted to Robokassa:

- public landing page at `index.html`
- legal pages at `offer.html`, `terms.html`, `privacy.html`
- separate `about.html` and `faq.html`
- seller requisites on the landing and offer
- checkout explained as happening in a Telegram bot

Print the default config first:

```bash
python3 <path-to-skill>/scripts/check_robokassa_readiness.py --print-default-config
```

Use a JSON config file when seller type, page names, legal-link structure, price points, phone format, tax-id format, or purchase wording differ.

## Fields

- `index_page`, `offer_page`, `terms_page`, `privacy_page`
  Select which page gets each content-specific check.
- `about_page`, `faq_page`
  Optional named pages used by the default page list and default link targets.
- `required_pages`
  List of files that must exist and be non-empty.
- `required_link_targets_on_index`
  Exact filenames that must be linked from the landing page. Set `[]` to skip this check.
- `required_link_targets_on_terms`
  Exact filenames that must be linked from the terms page. Set `[]` to skip this check.
- `price_markers`
  Strings that must appear on the landing page. Set `[]` to skip price checks.
- `seller_name_mode`
  One of `full_name`, `any_non_placeholder`, `skip`.
- `delivery_terms_keywords_any`
  Any one of these phrases must appear on the offer page.
- `operator_identity_keywords_any`
  Any one of these phrases must appear on the privacy page.
- `index_purchase_keywords_all`
  All of these substrings must appear on the landing page. Use `[]` to skip checkout-flow wording checks.
- `index_seller_name_patterns`, `offer_seller_name_patterns`
  Regex patterns used to extract the seller name. The first capture group should contain the name.
- `seller_id_patterns`
  Regex patterns for the seller identifier to require, for example 12-digit INN, 10-digit company tax ID, or another local identifier.
- `seller_id_label`
  Human-readable label used in the result messages.
- `phone_patterns`
  Regex patterns for contact phone detection. Set `[]` to skip phone validation.
- `min_content_length`
  Minimum character count for a page to not be flagged as a stub. Default: `500`. Set `0` to skip.

## Example: Telegram Bot Checkout

```json
{
  "seller_name_mode": "full_name",
  "seller_id_patterns": ["\\b\\d{12}\\b"],
  "seller_id_label": "seller INN",
  "price_markers": ["25", "100", "250"],
  "index_purchase_keywords_all": ["telegram", "бот", "оплат"]
}
```

## Example: Different File Names

```json
{
  "index_page": "landing.html",
  "about_page": "company.html",
  "offer_page": "oferta.html",
  "terms_page": "rules.html",
  "privacy_page": "privacy-policy.html",
  "faq_page": "questions.html",
  "required_pages": [
    "landing.html",
    "company.html",
    "privacy-policy.html",
    "rules.html",
    "oferta.html",
    "questions.html"
  ],
  "required_link_targets_on_index": [
    "oferta.html",
    "privacy-policy.html",
    "rules.html",
    "questions.html"
  ],
  "required_link_targets_on_terms": ["oferta.html"]
}
```

If you rename files, update the internal links in the HTML too. The checker validates the public page graph, not only file existence.

## Example: Company Or Sole Proprietor Preset

```json
{
  "seller_name_mode": "any_non_placeholder",
  "seller_id_patterns": ["\\b\\d{10}\\b", "\\b\\d{13}\\b"],
  "seller_id_label": "seller tax ID",
  "phone_patterns": ["\\+1\\s\\d{3}\\s\\d{3}\\s\\d{4}"],
  "price_markers": ["990", "2490"],
  "index_purchase_keywords_all": ["оплат", "на сайте"]
}
```

## Example: Website Checkout Instead Of Bot Checkout

```json
{
  "index_purchase_keywords_all": ["оплат", "на сайте"],
  "price_markers": ["990", "2490"]
}
```

This checker is a smoke test, not an official Robokassa validator. If the user asks whether the site meets the latest Robokassa rules, verify the current official requirements first and treat this script as an accelerator, not as the final authority.
