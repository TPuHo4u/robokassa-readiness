"""Configurable Robokassa readiness checker.

Usage:
    python3 check_robokassa_readiness.py --path data/html
    python3 check_robokassa_readiness.py --url https://example.com
    python3 check_robokassa_readiness.py --config robokassa-readiness.json --url https://example.com
    python3 check_robokassa_readiness.py --print-default-config
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.request import urlopen


CheckResult = tuple[bool, str]

DEFAULT_INDEX_PAGE = "index.html"
DEFAULT_ABOUT_PAGE = "about.html"
DEFAULT_OFFER_PAGE = "offer.html"
DEFAULT_TERMS_PAGE = "terms.html"
DEFAULT_PRIVACY_PAGE = "privacy.html"
DEFAULT_FAQ_PAGE = "faq.html"
DEFAULT_PHONE_PATTERNS = (
    r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
)
DEFAULT_SELLER_ID_PATTERNS = (
    r"\b\d{12}\b",
)
SELLER_NAME_MODES = frozenset({"full_name", "any_non_placeholder", "skip"})

DEFAULT_INDEX_SELLER_PATTERNS = (
    r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",
)
DEFAULT_OFFER_SELLER_PATTERNS = (
    r"ФИО[^<]*?:\s*([^<]+)",
)


def _default_required_pages(
    index_page: str,
    about_page: str,
    privacy_page: str,
    terms_page: str,
    offer_page: str,
    faq_page: str,
) -> tuple[str, ...]:
    return tuple(
        page for page in (
            index_page,
            about_page,
            privacy_page,
            terms_page,
            offer_page,
            faq_page,
        )
        if page
    )


def _coerce_string(raw: object, key: str, default: str) -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    value = raw.strip()
    if not value:
        raise ValueError(f"{key} must not be empty")
    return value


def _coerce_optional_string(raw: object, key: str, default: str) -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    return raw.strip()


def _coerce_string_list(raw: object, key: str) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a JSON array of strings")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"{key} must contain strings only")
        values.append(item.strip())
    return tuple(values)


def _coerce_enum(raw: object, key: str, default: str, allowed: frozenset[str]) -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    value = raw.strip()
    if value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{key} must be one of: {allowed_values}")
    return value


def _is_full_name_part(part: str) -> bool:
    cleaned = part.replace("-", "").replace("'", "")
    return len(cleaned) >= 2 and cleaned.isalpha()


def _looks_like_full_legal_name(value: str) -> bool:
    normalized = " ".join(value.split())
    if not normalized or "." in normalized:
        return False
    parts = [part for part in normalized.split(" ") if part]
    return len(parts) >= 2 and all(_is_full_name_part(part) for part in parts)


@dataclass(frozen=True)
class CheckerConfig:
    index_page: str = DEFAULT_INDEX_PAGE
    about_page: str = DEFAULT_ABOUT_PAGE
    offer_page: str = DEFAULT_OFFER_PAGE
    terms_page: str = DEFAULT_TERMS_PAGE
    privacy_page: str = DEFAULT_PRIVACY_PAGE
    faq_page: str = DEFAULT_FAQ_PAGE
    required_pages: tuple[str, ...] = ()
    required_link_targets_on_index: tuple[str, ...] = ()
    required_link_targets_on_terms: tuple[str, ...] = ()
    price_markers: tuple[str, ...] = ("25", "100", "250")
    delivery_terms_keywords_any: tuple[str, ...] = (
        "порядок оказания",
        "предоставляется доступ",
    )
    operator_identity_keywords_any: tuple[str, ...] = (
        "оператор",
        "исполнитель",
    )
    index_purchase_keywords_all: tuple[str, ...] = (
        "telegram",
        "бот",
        "оплат",
    )
    seller_name_mode: str = "full_name"
    index_seller_name_patterns: tuple[str, ...] = DEFAULT_INDEX_SELLER_PATTERNS
    offer_seller_name_patterns: tuple[str, ...] = DEFAULT_OFFER_SELLER_PATTERNS
    seller_id_patterns: tuple[str, ...] = DEFAULT_SELLER_ID_PATTERNS
    seller_id_label: str = "seller INN"
    phone_patterns: tuple[str, ...] = DEFAULT_PHONE_PATTERNS

    def __post_init__(self) -> None:
        if self.seller_name_mode not in SELLER_NAME_MODES:
            allowed_values = ", ".join(sorted(SELLER_NAME_MODES))
            raise ValueError(f"seller_name_mode must be one of: {allowed_values}")
        if not self.required_pages:
            object.__setattr__(
                self,
                "required_pages",
                _default_required_pages(
                    self.index_page,
                    self.about_page,
                    self.privacy_page,
                    self.terms_page,
                    self.offer_page,
                    self.faq_page,
                ),
            )
        if not self.required_link_targets_on_index:
            default_links = [
                self.offer_page,
                self.privacy_page,
                self.terms_page,
            ]
            if self.faq_page and self.faq_page in self.required_pages:
                default_links.append(self.faq_page)
            object.__setattr__(
                self,
                "required_link_targets_on_index",
                tuple(link for link in default_links if link),
            )
        if not self.required_link_targets_on_terms and self.offer_page:
            object.__setattr__(
                self,
                "required_link_targets_on_terms",
                (self.offer_page,),
            )

    @classmethod
    def from_dict(cls, raw: dict[str, object] | None) -> "CheckerConfig":
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise ValueError("config root must be a JSON object")

        base = cls()
        index_page = _coerce_string(raw.get("index_page"), "index_page", base.index_page)
        about_page = _coerce_optional_string(raw.get("about_page"), "about_page", base.about_page)
        offer_page = _coerce_string(raw.get("offer_page"), "offer_page", base.offer_page)
        terms_page = _coerce_string(raw.get("terms_page"), "terms_page", base.terms_page)
        privacy_page = _coerce_string(raw.get("privacy_page"), "privacy_page", base.privacy_page)
        faq_page = _coerce_optional_string(raw.get("faq_page"), "faq_page", base.faq_page)

        required_pages = _coerce_string_list(raw.get("required_pages"), "required_pages")
        if required_pages is None:
            required_pages = _default_required_pages(
                index_page,
                about_page,
                privacy_page,
                terms_page,
                offer_page,
                faq_page,
            )
        required_link_targets_on_index = _coerce_string_list(
            raw.get("required_link_targets_on_index"),
            "required_link_targets_on_index",
        )
        required_link_targets_on_terms = _coerce_string_list(
            raw.get("required_link_targets_on_terms"),
            "required_link_targets_on_terms",
        )

        price_markers = _coerce_string_list(raw.get("price_markers"), "price_markers")
        if price_markers is None:
            price_markers = base.price_markers

        delivery_terms_keywords_any = _coerce_string_list(
            raw.get("delivery_terms_keywords_any"),
            "delivery_terms_keywords_any",
        )
        if delivery_terms_keywords_any is None:
            delivery_terms_keywords_any = base.delivery_terms_keywords_any

        operator_identity_keywords_any = _coerce_string_list(
            raw.get("operator_identity_keywords_any"),
            "operator_identity_keywords_any",
        )
        if operator_identity_keywords_any is None:
            operator_identity_keywords_any = base.operator_identity_keywords_any

        index_purchase_keywords_all = _coerce_string_list(
            raw.get("index_purchase_keywords_all"),
            "index_purchase_keywords_all",
        )
        if index_purchase_keywords_all is None:
            index_purchase_keywords_all = base.index_purchase_keywords_all

        seller_name_mode = _coerce_enum(
            raw.get("seller_name_mode"),
            "seller_name_mode",
            base.seller_name_mode,
            SELLER_NAME_MODES,
        )
        index_seller_name_patterns = _coerce_string_list(
            raw.get("index_seller_name_patterns"),
            "index_seller_name_patterns",
        )
        if index_seller_name_patterns is None:
            index_seller_name_patterns = base.index_seller_name_patterns

        offer_seller_name_patterns = _coerce_string_list(
            raw.get("offer_seller_name_patterns"),
            "offer_seller_name_patterns",
        )
        if offer_seller_name_patterns is None:
            offer_seller_name_patterns = base.offer_seller_name_patterns
        seller_id_patterns = _coerce_string_list(
            raw.get("seller_id_patterns"),
            "seller_id_patterns",
        )
        if seller_id_patterns is None:
            seller_id_patterns = base.seller_id_patterns
        seller_id_label = _coerce_string(
            raw.get("seller_id_label"),
            "seller_id_label",
            base.seller_id_label,
        )
        phone_patterns = _coerce_string_list(
            raw.get("phone_patterns"),
            "phone_patterns",
        )
        if phone_patterns is None:
            phone_patterns = base.phone_patterns

        return cls(
            index_page=index_page,
            about_page=about_page,
            offer_page=offer_page,
            terms_page=terms_page,
            privacy_page=privacy_page,
            faq_page=faq_page,
            required_pages=required_pages,
            required_link_targets_on_index=required_link_targets_on_index or (),
            required_link_targets_on_terms=required_link_targets_on_terms or (),
            price_markers=price_markers,
            delivery_terms_keywords_any=delivery_terms_keywords_any,
            operator_identity_keywords_any=operator_identity_keywords_any,
            index_purchase_keywords_all=index_purchase_keywords_all,
            seller_name_mode=seller_name_mode,
            index_seller_name_patterns=index_seller_name_patterns,
            offer_seller_name_patterns=offer_seller_name_patterns,
            seller_id_patterns=seller_id_patterns,
            seller_id_label=seller_id_label,
            phone_patterns=phone_patterns,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "index_page": self.index_page,
            "about_page": self.about_page,
            "offer_page": self.offer_page,
            "terms_page": self.terms_page,
            "privacy_page": self.privacy_page,
            "faq_page": self.faq_page,
            "required_pages": list(self.required_pages),
            "required_link_targets_on_index": list(self.required_link_targets_on_index),
            "required_link_targets_on_terms": list(self.required_link_targets_on_terms),
            "price_markers": list(self.price_markers),
            "delivery_terms_keywords_any": list(self.delivery_terms_keywords_any),
            "operator_identity_keywords_any": list(self.operator_identity_keywords_any),
            "index_purchase_keywords_all": list(self.index_purchase_keywords_all),
            "seller_name_mode": self.seller_name_mode,
            "index_seller_name_patterns": list(self.index_seller_name_patterns),
            "offer_seller_name_patterns": list(self.offer_seller_name_patterns),
            "seller_id_patterns": list(self.seller_id_patterns),
            "seller_id_label": self.seller_id_label,
            "phone_patterns": list(self.phone_patterns),
        }


def load_config(path: str | None = None) -> CheckerConfig:
    if not path:
        return CheckerConfig()
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return CheckerConfig.from_dict(raw)


def _read_local(html_dir: Path, page: str) -> str | None:
    file_path = html_dir / page
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8")


def _read_remote(base_url: str, page: str) -> str | None:
    url = f"{base_url.rstrip('/')}/{page}"
    try:
        with urlopen(url, timeout=10) as response:
            if response.status != 200:
                return None
            return response.read().decode("utf-8")
    except urllib.error.HTTPError:
        return None
    except Exception as exc:
        print(f"  [WARN] could not fetch {url}: {exc}", file=sys.stderr)
        return None


def _check_page_exists(content: str | None, page: str) -> CheckResult:
    if content and content.strip():
        return (True, f"{page} exists")
    return (False, f"{page} missing or empty")


def _check_no_trial(content: str, page: str) -> CheckResult:
    lower = content.lower()
    if "пробный период" in lower or "бесплатный пробный период" in lower:
        return (False, f"{page}: trial language found")
    return (True, f"{page}: no trial language")


def _check_tariffs(content: str, index_page: str, price_markers: Sequence[str]) -> CheckResult:
    if not price_markers:
        return (True, f"{index_page}: tariff check skipped (no price markers configured)")
    missing = [marker for marker in price_markers if marker not in content]
    if not missing:
        return (True, f"{index_page}: configured tariffs found")
    return (False, f"{index_page}: tariffs missing ({', '.join(missing)})")


def _extract_first_match(content: str, patterns: Sequence[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        if match.lastindex:
            return (match.group(1) or "").strip()
        return match.group(0).strip()
    return None


def _check_seller_name(
    content: str,
    page: str,
    patterns: Sequence[str],
    mode: str,
) -> CheckResult:
    if mode == "skip":
        return (True, f"{page}: seller name check skipped")
    value = _extract_first_match(content, patterns)
    if not value or value in ("\u2014", "-", ""):
        return (False, f"{page}: seller name not found, placeholder, or abbreviated")
    if mode == "any_non_placeholder":
        return (True, f"{page}: seller name found")
    if _looks_like_full_legal_name(value):
        return (True, f"{page}: seller name found")
    return (False, f"{page}: seller name not found, placeholder, or abbreviated")


def _check_seller_identifier(
    content: str,
    page: str,
    patterns: Sequence[str],
    label: str,
) -> CheckResult:
    if not patterns:
        return (True, f"{page}: {label} check skipped")
    if any(re.search(pattern, content) for pattern in patterns):
        return (True, f"{page}: {label} found")
    return (False, f"{page}: {label} not found")


def _check_email(content: str, page: str) -> CheckResult:
    if re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content):
        return (True, f"{page}: support email found")
    return (False, f"{page}: support email not found")


def _check_phone(content: str, page: str, patterns: Sequence[str]) -> CheckResult:
    if not patterns:
        return (True, f"{page}: phone check skipped")
    if any(re.search(pattern, content) for pattern in patterns):
        return (True, f"{page}: phone number found")
    return (False, f"{page}: phone number not found")


def _check_refund(content: str, offer_page: str) -> CheckResult:
    if "возврат" in content.lower():
        return (True, f"{offer_page}: refund wording found")
    return (False, f"{offer_page}: refund wording not found")


def _check_keywords_any(
    content: str,
    page: str,
    keywords: Sequence[str],
    ok_message: str,
    fail_message: str,
) -> CheckResult:
    if not keywords:
        return (True, f"{page}: {ok_message} skipped")
    lower = content.lower()
    if any(keyword.lower() in lower for keyword in keywords):
        return (True, f"{page}: {ok_message}")
    return (False, f"{page}: {fail_message}")


def _check_keywords_all(
    content: str,
    page: str,
    keywords: Sequence[str],
    ok_message: str,
    fail_message: str,
) -> CheckResult:
    if not keywords:
        return (True, f"{page}: {ok_message} skipped")
    lower = content.lower()
    if all(keyword.lower() in lower for keyword in keywords):
        return (True, f"{page}: {ok_message}")
    return (False, f"{page}: {fail_message}")


def _find_href_targets(content: str) -> set[str]:
    return set(re.findall(r'href=["\']([^"\']+)["\']', content, re.IGNORECASE))


def _check_legal_links_on_index(content: str, config: CheckerConfig) -> CheckResult:
    if not config.required_link_targets_on_index:
        return (True, f"{config.index_page}: legal link check skipped")
    hrefs = _find_href_targets(content)
    missing = [
        target for target in config.required_link_targets_on_index
        if not any(href == target or href.endswith("/" + target) for href in hrefs)
    ]
    if not missing:
        return (True, f"{config.index_page}: legal page links found")
    missing_names = [target.removesuffix(".html") for target in missing]
    return (False, f"{config.index_page}: legal links missing ({', '.join(missing_names)})")


def run_checks(
    reader: Callable[[str], str | None],
    config: CheckerConfig | None = None,
) -> list[CheckResult]:
    current = config or CheckerConfig()
    results: list[CheckResult] = []

    pages: dict[str, str | None] = {}
    for page in dict.fromkeys(current.required_pages):
        content = reader(page)
        pages[page] = content
        results.append(_check_page_exists(content, page))

    index_content = pages.get(current.index_page)
    if index_content:
        results.append(_check_no_trial(index_content, current.index_page))
        results.append(_check_tariffs(index_content, current.index_page, current.price_markers))
        results.append(_check_phone(index_content, current.index_page, current.phone_patterns))
        results.append(_check_email(index_content, current.index_page))
        results.append(
            _check_seller_name(
                index_content,
                current.index_page,
                current.index_seller_name_patterns,
                current.seller_name_mode,
            )
        )
        results.append(
            _check_seller_identifier(
                index_content,
                current.index_page,
                current.seller_id_patterns,
                current.seller_id_label,
            )
        )
        results.append(
            _check_keywords_all(
                index_content,
                current.index_page,
                current.index_purchase_keywords_all,
                "purchase flow wording found",
                "purchase flow wording missing",
            )
        )
        results.append(_check_legal_links_on_index(index_content, current))

    offer_content = pages.get(current.offer_page)
    if offer_content:
        results.append(
            _check_seller_name(
                offer_content,
                current.offer_page,
                current.offer_seller_name_patterns,
                current.seller_name_mode,
            )
        )
        results.append(
            _check_seller_identifier(
                offer_content,
                current.offer_page,
                current.seller_id_patterns,
                current.seller_id_label,
            )
        )
        results.append(_check_email(offer_content, current.offer_page))
        results.append(_check_refund(offer_content, current.offer_page))
        results.append(
            _check_keywords_any(
                offer_content,
                current.offer_page,
                current.delivery_terms_keywords_any,
                "delivery terms found",
                "delivery terms not found",
            )
        )

    terms_content = pages.get(current.terms_page)
    if terms_content:
        results.append(_check_no_trial(terms_content, current.terms_page))
        if not current.required_link_targets_on_terms:
            results.append((True, f"{current.terms_page}: legal link check skipped"))
        else:
            terms_hrefs = _find_href_targets(terms_content)
            missing_terms_links = [
                target for target in current.required_link_targets_on_terms
                if not any(href == target or href.endswith("/" + target) for href in terms_hrefs)
            ]
            if not missing_terms_links:
                joined = ", ".join(current.required_link_targets_on_terms)
                results.append((True, f"{current.terms_page}: links to {joined}"))
            else:
                joined = ", ".join(missing_terms_links)
                results.append((False, f"{current.terms_page}: missing links to {joined}"))

    about_content = pages.get(current.about_page)
    if about_content:
        results.append(_check_email(about_content, current.about_page))
        results.append(
            _check_seller_identifier(
                about_content,
                current.about_page,
                current.seller_id_patterns,
                current.seller_id_label,
            )
        )

    privacy_content = pages.get(current.privacy_page)
    if privacy_content:
        results.append(
            _check_keywords_any(
                privacy_content,
                current.privacy_page,
                current.operator_identity_keywords_any,
                "operator identity present",
                "operator identity not found",
            )
        )

    return results


def check_local(html_dir: str, config: CheckerConfig | None = None) -> list[CheckResult]:
    path = Path(html_dir)
    return run_checks(lambda page: _read_local(path, page), config=config)


def check_remote(base_url: str, config: CheckerConfig | None = None) -> list[CheckResult]:
    return run_checks(lambda page: _read_remote(base_url, page), config=config)


def print_results(results: Sequence[CheckResult], *, as_json: bool = False) -> int:
    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    ready = passed == total

    if as_json:
        output = {
            "passed": passed,
            "total": total,
            "ready": ready,
            "checks": [{"ok": ok, "message": msg} for ok, msg in results],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if ready else 1

    print("Robokassa Readiness Check")
    print("=" * 40)
    for ok, message in results:
        print(f"  {'[OK]' if ok else '[FAIL]'} {message}")
    print("=" * 40)
    print(f"Result: {passed}/{total} checks passed")
    print(f"Status: {'READY' if ready else 'NOT READY'}")
    return 0 if ready else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Robokassa readiness checker")
    parser.add_argument("--path", help="Local HTML directory to check")
    parser.add_argument("--url", help="Base URL to check (for example https://example.com)")
    parser.add_argument("--config", help="Optional JSON config file")
    parser.add_argument(
        "--print-default-config",
        action="store_true",
        help="Print the default JSON config and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args(argv)

    if args.print_default_config:
        print(json.dumps(CheckerConfig().to_dict(), ensure_ascii=False, indent=2))
        return 0

    if bool(args.path) == bool(args.url):
        parser.error("exactly one of --path or --url is required unless --print-default-config is used")

    try:
        config = load_config(args.config)
    except Exception as exc:
        parser.error(f"invalid --config: {exc}")

    if args.path:
        results = check_local(args.path, config=config)
    else:
        results = check_remote(args.url, config=config)
    return print_results(results, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
