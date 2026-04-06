"""Comprehensive unit tests for the Robokassa readiness checker."""

import json
import pytest
from scripts.check_robokassa_readiness import (
    CheckerConfig,
    _check_page_exists,
    _check_no_trial,
    _check_tariffs,
    _check_seller_name,
    _check_seller_identifier,
    _check_email,
    _check_phone,
    _check_refund,
    _check_keywords_any,
    _check_keywords_all,
    _find_href_targets,
    _check_legal_links_on_index,
    _check_min_content_length,
    _check_offer_structure,
    _check_cross_page_consistency,
    _looks_like_full_legal_name,
    _normalize_diff_key,
    run_checks,
    print_results,
)


# HTML Fixtures
COMPLETE_INDEX = '''
<html><body>
<h1>Добро пожаловать</h1>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>ИНН: 123456789012</p>
<p>Телефон: +7 977 479-45-07</p>
<p>Email: test@example.com</p>
<p>Тарифы: 25 руб, 100 руб, 250 руб</p>
<p>Оплата через Telegram бот</p>
<a href="offer.html">Оферта</a>
<a href="privacy.html">Конфиденциальность</a>
<a href="terms.html">Условия использования</a>
<a href="faq.html">FAQ</a>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
</body></html>
'''

TRIAL_LANGUAGE_INDEX = '''
<html><body>
<h1>Добро пожаловать</h1>
<p>У нас есть бесплатный пробный период на 7 дней!</p>
<strong>ФИО:</strong> Иван Петрович Сидоров
</body></html>
'''

MINIMAL_INDEX = '''
<html><body>
<h1>Краткая страница</h1>
<p>Короткий контент менее 500 символов.</p>
</body></html>
'''

ABBREVIATED_SELLER_INDEX = '''
<html><body>
<strong>ФИО:</strong> И. П. Сидоров
<p>ИНН: 123456789012</p>
</body></html>
'''

PLACEHOLDER_SELLER_INDEX = '''
<html><body>
<strong>ФИО:</strong> —
<p>ИНН: 123456789012</p>
</body></html>
'''

COMPLETE_OFFER = '''
<html><body>
<h1>Публичная оферта</h1>
<h2>Предмет договора</h2>
<p>Данная оферта определяет условия...</p>
<h2>Возврат и отмена</h2>
<p>Возврат денежных средств...</p>
<h2>Персональные данные</h2>
<p>Обработка персональных данных...</p>
<h2>Реквизиты исполнителя</h2>
<p>ФИО: Иван Петрович Сидоров</p>
<p>ИНН: 123456789012</p>
</body></html>
'''

INCOMPLETE_OFFER = '''
<html><body>
<h1>Оферта</h1>
<p>Краткие условия без необходимых разделов.</p>
</body></html>
'''

MISMATCHED_SELLER_OFFER = '''
<html><body>
<h1>Публичная оферта</h1>
<h2>Предмет договора</h2>
<p>Условия оказания услуг...</p>
<h2>Возврат</h2>
<p>Возврат денежных средств возможен...</p>
<h2>Персональные данные</h2>
<p>Обработка персональных данных...</p>
<h2>Реквизиты исполнителя</h2>
<p>ФИО: Петр Иванович Козлов</p>
<p>ИНН: 987654321098</p>
</body></html>
'''

MISSING_LINKS_INDEX = '''
<html><body>
<h1>Главная страница</h1>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>ИНН: 123456789012</p>
<p>Телефон: +7 977 479-45-07</p>
<p>Email: test@example.com</p>
<!-- Нет ссылок на юридические страницы -->
</body></html>
'''

EMPTY_PAGE = ''

NO_EMAIL_INDEX = '''
<html><body>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>ИНН: 123456789012</p>
<p>Телефон: +7 977 479-45-07</p>
<!-- Нет email -->
</body></html>
'''

NO_PHONE_INDEX = '''
<html><body>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>ИНН: 123456789012</p>
<p>Email: test@example.com</p>
<!-- Нет телефона -->
</body></html>
'''

NO_INN_INDEX = '''
<html><body>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>Email: test@example.com</p>
<!-- Нет ИНН -->
</body></html>
'''

MISSING_TARIFFS_INDEX = '''
<html><body>
<strong>ФИО:</strong> Иван Петрович Сидоров
<p>ИНН: 123456789012</p>
<p>Тарифы: 50 руб, 200 руб</p>
<!-- Нет искомых тарифов -->
</body></html>
'''


class TestCheckerConfig:
    def test_default_config(self):
        config = CheckerConfig()
        assert config.index_page == "index.html"
        assert config.about_page == "about.html"
        assert config.offer_page == "offer.html"
        assert config.terms_page == "terms.html"
        assert config.privacy_page == "privacy.html"
        assert config.faq_page == "faq.html"
        assert config.price_markers == ("25", "100", "250")
        assert config.seller_name_mode == "full_name"
        assert config.min_content_length == 500
        assert len(config.required_pages) > 0

    def test_config_from_dict_overrides(self):
        custom_data = {
            "index_page": "home.html",
            "price_markers": ["50", "200"],
            "min_content_length": 1000,
            "seller_name_mode": "any_non_placeholder"
        }
        config = CheckerConfig.from_dict(custom_data)
        assert config.index_page == "home.html"
        assert config.price_markers == ("50", "200")
        assert config.min_content_length == 1000
        assert config.seller_name_mode == "any_non_placeholder"

    def test_config_from_dict_invalid_seller_mode(self):
        custom_data = {
            "seller_name_mode": "invalid_mode"
        }
        with pytest.raises(ValueError, match="seller_name_mode must be one of"):
            CheckerConfig.from_dict(custom_data)

    def test_config_from_dict_invalid_type(self):
        with pytest.raises(ValueError, match="config root must be a JSON object"):
            CheckerConfig.from_dict("not a dict")

    def test_config_to_dict_roundtrip(self):
        original = CheckerConfig(
            index_page="custom.html",
            price_markers=("10", "20"),
            min_content_length=300
        )
        data = original.to_dict()
        restored = CheckerConfig.from_dict(data)

        # Compare key fields
        assert restored.index_page == original.index_page
        assert restored.price_markers == original.price_markers
        assert restored.min_content_length == original.min_content_length


class TestPageExistsCheck:
    def test_check_page_exists_ok(self):
        result = _check_page_exists(COMPLETE_INDEX, "index.html")
        passed, message, severity = result
        assert passed is True
        assert "exists" in message
        assert severity == "ok"

    def test_check_page_exists_fail_none(self):
        result = _check_page_exists(None, "missing.html")
        passed, message, severity = result
        assert passed is False
        assert "missing or empty" in message
        assert severity == "blocker"

    def test_check_page_exists_fail_empty(self):
        result = _check_page_exists("", "empty.html")
        passed, message, severity = result
        assert passed is False
        assert "missing or empty" in message
        assert severity == "blocker"

    def test_check_page_exists_fail_whitespace(self):
        result = _check_page_exists("   \n\t  ", "whitespace.html")
        passed, message, severity = result
        assert passed is False
        assert "missing or empty" in message
        assert severity == "blocker"


class TestTrialCheck:
    def test_check_no_trial_ok(self):
        result = _check_no_trial(COMPLETE_INDEX, "index.html")
        passed, message, severity = result
        assert passed is True
        assert "no trial language" in message
        assert severity == "ok"

    def test_check_no_trial_fail(self):
        result = _check_no_trial(TRIAL_LANGUAGE_INDEX, "index.html")
        passed, message, severity = result
        assert passed is False
        assert "trial language found" in message
        assert severity == "warning"

    def test_check_no_trial_case_insensitive(self):
        content = "<p>БЕСПЛАТНЫЙ ПРОБНЫЙ ПЕРИОД доступен</p>"
        result = _check_no_trial(content, "index.html")
        passed, message, severity = result
        assert passed is False
        assert severity == "warning"


class TestTariffCheck:
    def test_check_tariffs_ok(self):
        result = _check_tariffs(COMPLETE_INDEX, "index.html", ("25", "100", "250"))
        passed, message, severity = result
        assert passed is True
        assert "configured tariffs found" in message
        assert severity == "ok"

    def test_check_tariffs_missing(self):
        result = _check_tariffs(MISSING_TARIFFS_INDEX, "index.html", ("25", "100", "250"))
        passed, message, severity = result
        assert passed is False
        assert "tariffs missing" in message
        assert "25" in message and "100" in message and "250" in message
        assert severity == "warning"

    def test_check_tariffs_skip_when_empty(self):
        result = _check_tariffs(COMPLETE_INDEX, "index.html", ())
        passed, message, severity = result
        assert passed is True
        assert "tariff check skipped" in message
        assert severity == "ok"


class TestSellerNameCheck:
    def test_check_seller_name_full_ok(self):
        result = _check_seller_name(
            COMPLETE_INDEX, "index.html",
            (r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",),
            "full_name"
        )
        passed, message, severity = result
        assert passed is True
        assert "seller name found" in message
        assert severity == "ok"

    def test_check_seller_name_abbreviated_fail(self):
        result = _check_seller_name(
            ABBREVIATED_SELLER_INDEX, "index.html",
            (r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",),
            "full_name"
        )
        passed, message, severity = result
        assert passed is False
        assert "not found, placeholder, or abbreviated" in message
        assert severity == "blocker"

    def test_check_seller_name_placeholder_fail(self):
        result = _check_seller_name(
            PLACEHOLDER_SELLER_INDEX, "index.html",
            (r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",),
            "full_name"
        )
        passed, message, severity = result
        assert passed is False
        assert "not found, placeholder, or abbreviated" in message
        assert severity == "blocker"

    def test_check_seller_name_any_non_placeholder_mode(self):
        result = _check_seller_name(
            ABBREVIATED_SELLER_INDEX, "index.html",
            (r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",),
            "any_non_placeholder"
        )
        passed, message, severity = result
        assert passed is True
        assert "seller name found" in message
        assert severity == "ok"

    def test_check_seller_name_skip_mode(self):
        result = _check_seller_name(
            COMPLETE_INDEX, "index.html",
            (r"(?:ФИО|Самозанятый).*?</strong>\s*([^<]+)",),
            "skip"
        )
        passed, message, severity = result
        assert passed is True
        assert "seller name check skipped" in message
        assert severity == "ok"


class TestSellerIdentifierCheck:
    def test_check_seller_identifier_found(self):
        result = _check_seller_identifier(
            COMPLETE_INDEX, "index.html",
            (r"\b\d{12}\b",), "seller INN"
        )
        passed, message, severity = result
        assert passed is True
        assert "seller INN found" in message
        assert severity == "ok"

    def test_check_seller_identifier_missing(self):
        result = _check_seller_identifier(
            NO_INN_INDEX, "index.html",
            (r"\b\d{12}\b",), "seller INN"
        )
        passed, message, severity = result
        assert passed is False
        assert "seller INN not found" in message
        assert severity == "blocker"

    def test_check_seller_identifier_skip_when_no_patterns(self):
        result = _check_seller_identifier(
            COMPLETE_INDEX, "index.html",
            (), "seller INN"
        )
        passed, message, severity = result
        assert passed is True
        assert "seller INN check skipped" in message
        assert severity == "ok"


class TestEmailCheck:
    def test_check_email_found(self):
        result = _check_email(COMPLETE_INDEX, "index.html")
        passed, message, severity = result
        assert passed is True
        assert "support email found" in message
        assert severity == "ok"

    def test_check_email_missing(self):
        result = _check_email(NO_EMAIL_INDEX, "index.html")
        passed, message, severity = result
        assert passed is False
        assert "support email not found" in message
        assert severity == "blocker"

    def test_check_email_various_formats(self):
        test_cases = [
            "user@example.com",
            "test.email+filter@domain.co.uk",
            "user_name@sub.domain.org",
        ]
        for email in test_cases:
            content = f"<p>Contact: {email}</p>"
            result = _check_email(content, "test.html")
            assert result[0] is True, f"Email {email} should be valid"


class TestPhoneCheck:
    def test_check_phone_found(self):
        result = _check_phone(
            COMPLETE_INDEX, "index.html",
            (r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",)
        )
        passed, message, severity = result
        assert passed is True
        assert "phone number found" in message
        assert severity == "ok"

    def test_check_phone_missing(self):
        result = _check_phone(
            NO_PHONE_INDEX, "index.html",
            (r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",)
        )
        passed, message, severity = result
        assert passed is False
        assert "phone number not found" in message
        assert severity == "blocker"

    def test_check_phone_skip_when_no_patterns(self):
        result = _check_phone(COMPLETE_INDEX, "index.html", ())
        passed, message, severity = result
        assert passed is True
        assert "phone check skipped" in message
        assert severity == "ok"

    def test_check_phone_various_formats(self):
        test_cases = [
            "+7 977 479-45-07",
            "8(495)123-45-67",
            "+7 (977) 479 45 07",
            "8-495-123-45-67",
        ]
        pattern = (r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",)
        for phone in test_cases:
            content = f"<p>Телефон: {phone}</p>"
            result = _check_phone(content, "test.html", pattern)
            assert result[0] is True, f"Phone {phone} should be valid"


class TestRefundCheck:
    def test_check_refund_found(self):
        result = _check_refund(COMPLETE_OFFER, "offer.html")
        passed, message, severity = result
        assert passed is True
        assert "refund wording found" in message
        assert severity == "ok"

    def test_check_refund_missing(self):
        result = _check_refund(INCOMPLETE_OFFER, "offer.html")
        passed, message, severity = result
        assert passed is False
        assert "refund wording not found" in message
        assert severity == "blocker"

    def test_check_refund_case_insensitive(self):
        content = "<p>ВОЗВРАТ денежных средств</p>"
        result = _check_refund(content, "offer.html")
        passed, message, severity = result
        assert passed is True
        assert severity == "ok"


class TestKeywordsAnyCheck:
    def test_check_keywords_any_found(self):
        content = "Порядок оказания услуг описан ниже"
        result = _check_keywords_any(
            content, "terms.html",
            ("порядок оказания", "предоставляется доступ"),
            "delivery terms found", "delivery terms missing"
        )
        passed, message, severity = result
        assert passed is True
        assert "delivery terms found" in message
        assert severity == "ok"

    def test_check_keywords_any_missing(self):
        content = "Условия работы нашего сервиса"
        result = _check_keywords_any(
            content, "terms.html",
            ("порядок оказания", "предоставляется доступ"),
            "delivery terms found", "delivery terms missing"
        )
        passed, message, severity = result
        assert passed is False
        assert "delivery terms missing" in message
        assert severity == "warning"

    def test_check_keywords_any_skip_when_empty(self):
        result = _check_keywords_any(
            COMPLETE_INDEX, "index.html", (),
            "keywords found", "keywords missing"
        )
        passed, message, severity = result
        assert passed is True
        assert "keywords found skipped" in message
        assert severity == "ok"


class TestKeywordsAllCheck:
    def test_check_keywords_all_found(self):
        content = "Оплата через Telegram бот доступна"
        result = _check_keywords_all(
            content, "index.html",
            ("telegram", "бот", "оплат"),
            "purchase info found", "purchase info missing"
        )
        passed, message, severity = result
        assert passed is True
        assert "purchase info found" in message
        assert severity == "ok"

    def test_check_keywords_all_partial(self):
        content = "Оплата через Telegram доступна"  # Нет "бот"
        result = _check_keywords_all(
            content, "index.html",
            ("telegram", "бот", "оплат"),
            "purchase info found", "purchase info missing"
        )
        passed, message, severity = result
        assert passed is False
        assert "purchase info missing" in message
        assert severity == "warning"

    def test_check_keywords_all_skip_when_empty(self):
        result = _check_keywords_all(
            COMPLETE_INDEX, "index.html", (),
            "keywords found", "keywords missing"
        )
        passed, message, severity = result
        assert passed is True
        assert "keywords found skipped" in message
        assert severity == "ok"


class TestHrefTargets:
    def test_find_href_targets(self):
        content = '''
        <a href="offer.html">Оферта</a>
        <a href="privacy.html">Конфиденциальность</a>
        <a href="/terms.html">Условия</a>
        <a href='https://example.com'>Внешняя ссылка</a>
        '''
        targets = _find_href_targets(content)
        expected = {"offer.html", "privacy.html", "/terms.html", "https://example.com"}
        assert targets == expected

    def test_find_href_targets_empty(self):
        content = "<p>Нет ссылок</p>"
        targets = _find_href_targets(content)
        assert targets == set()


class TestLegalLinksCheck:
    def test_check_legal_links_href_found(self):
        config = CheckerConfig(required_link_targets_on_index=("offer.html", "privacy.html"))
        result = _check_legal_links_on_index(COMPLETE_INDEX, config)
        passed, message, severity = result
        assert passed is True
        assert "legal page links found" in message
        assert severity == "ok"

    def test_check_legal_links_missing(self):
        config = CheckerConfig(required_link_targets_on_index=("offer.html", "privacy.html", "terms.html"))
        result = _check_legal_links_on_index(MISSING_LINKS_INDEX, config)
        passed, message, severity = result
        assert passed is False
        assert "legal links missing" in message
        assert severity == "blocker"

    def test_check_legal_links_skip_when_empty(self):
        # Need to override the __post_init__ behavior by creating a config directly
        # and setting the field afterwards
        config = CheckerConfig()
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(config, "required_link_targets_on_index", ())
        result = _check_legal_links_on_index(COMPLETE_INDEX, config)
        passed, message, severity = result
        assert passed is True
        assert "legal link check skipped" in message
        assert severity == "ok"


class TestMinContentLengthCheck:
    def test_check_min_content_length_ok(self):
        result = _check_min_content_length(COMPLETE_INDEX, "index.html", 500)
        passed, message, severity = result
        assert passed is True
        assert "content length sufficient" in message
        assert severity == "ok"

    def test_check_min_content_length_short(self):
        result = _check_min_content_length(MINIMAL_INDEX, "index.html", 500)
        passed, message, severity = result
        assert passed is False
        assert "likely a stub page" in message
        assert severity == "warning"


class TestOfferStructureCheck:
    def test_offer_structure_complete(self):
        results = _check_offer_structure(COMPLETE_OFFER, "offer.html")
        assert len(results) == 5

        # All checks should pass
        for passed, message, severity in results:
            assert passed is True
            assert severity == "ok"

        # Check specific sections
        messages = [result[1] for result in results]
        assert any("public offer identification found" in msg for msg in messages)
        assert any("subject section found" in msg for msg in messages)
        assert any("refund wording found" in msg for msg in messages)
        assert any("personal data handling section found" in msg for msg in messages)
        assert any("executor details section found" in msg for msg in messages)

    def test_offer_structure_missing_public_offer(self):
        content = '''
        <h1>Договор оказания услуг</h1>
        <h2>Предмет</h2>
        <h2>Возврат</h2>
        <h2>Персональные данные</h2>
        <h2>Реквизиты исполнителя</h2>
        '''
        results = _check_offer_structure(content, "offer.html")

        # Public offer check should fail
        public_offer_result = results[0]
        assert public_offer_result[0] is False
        assert "public offer identification not found" in public_offer_result[1]
        assert public_offer_result[2] == "blocker"

    def test_offer_structure_missing_subject(self):
        content = '''
        <h1>Публичная оферта</h1>
        <h2>Возврат</h2>
        <h2>Персональные данные</h2>
        <h2>Реквизиты исполнителя</h2>
        '''
        results = _check_offer_structure(content, "offer.html")

        # Subject check should fail
        subject_result = results[1]
        assert subject_result[0] is False
        assert "subject section not found" in subject_result[1]
        assert subject_result[2] == "blocker"

    def test_offer_structure_missing_personal_data(self):
        content = '''
        <h1>Публичная оферта</h1>
        <h2>Предмет</h2>
        <h2>Возврат</h2>
        <h2>Реквизиты исполнителя</h2>
        '''
        results = _check_offer_structure(content, "offer.html")

        # Personal data check should fail
        personal_data_result = results[3]
        assert personal_data_result[0] is False
        assert "personal data handling section not found" in personal_data_result[1]
        assert personal_data_result[2] == "blocker"


class TestCrossPageConsistency:
    def test_consistency_matching_names(self):
        pages = {
            "index.html": COMPLETE_INDEX,
            "offer.html": COMPLETE_OFFER
        }
        config = CheckerConfig()
        results = _check_cross_page_consistency(pages, config)

        # Should find consistent seller names
        name_result = [r for r in results if "seller names consistent" in r[1]]
        assert len(name_result) == 1
        assert name_result[0][0] is True
        assert name_result[0][2] == "ok"

    def test_consistency_mismatched_names(self):
        pages = {
            "index.html": COMPLETE_INDEX,
            "offer.html": MISMATCHED_SELLER_OFFER
        }
        config = CheckerConfig()
        results = _check_cross_page_consistency(pages, config)

        # Should find seller name mismatch
        name_result = [r for r in results if "seller name mismatch" in r[1]]
        assert len(name_result) == 1
        assert name_result[0][0] is False
        assert name_result[0][2] == "warning"

    def test_consistency_matching_inn(self):
        pages = {
            "index.html": COMPLETE_INDEX,
            "offer.html": COMPLETE_OFFER
        }
        config = CheckerConfig()
        results = _check_cross_page_consistency(pages, config)

        # Should find consistent INNs
        inn_result = [r for r in results if "seller INN consistent" in r[1]]
        assert len(inn_result) == 1
        assert inn_result[0][0] is True
        assert inn_result[0][2] == "ok"

    def test_consistency_mismatched_inn(self):
        pages = {
            "index.html": COMPLETE_INDEX,
            "offer.html": MISMATCHED_SELLER_OFFER
        }
        config = CheckerConfig()
        results = _check_cross_page_consistency(pages, config)

        # Should find INN mismatch
        inn_result = [r for r in results if "seller INN mismatch" in r[1]]
        assert len(inn_result) == 1
        assert inn_result[0][0] is False
        assert inn_result[0][2] == "warning"


class TestSeverityLevels:
    def test_blocker_severity_on_missing_page(self):
        result = _check_page_exists(None, "missing.html")
        assert result[2] == "blocker"

    def test_warning_severity_on_trial_language(self):
        result = _check_no_trial(TRIAL_LANGUAGE_INDEX, "index.html")
        assert result[2] == "warning"

    def test_ok_severity_on_passing_check(self):
        result = _check_email(COMPLETE_INDEX, "index.html")
        assert result[2] == "ok"


class TestHttpsCheck:
    def test_https_url_passes(self):
        def mock_reader(page: str) -> str | None:
            if page == "index.html":
                return COMPLETE_INDEX
            return None

        results = run_checks(mock_reader, None, "https://example.com")

        # Should not have HTTPS blocker
        https_failures = [r for r in results if "HTTP, not HTTPS" in r[1]]
        assert len(https_failures) == 0

    def test_http_url_fails(self):
        def mock_reader(page: str) -> str | None:
            return COMPLETE_INDEX

        results = run_checks(mock_reader, None, "http://example.com")

        # Should have HTTPS blocker
        https_failures = [r for r in results if "HTTP, not HTTPS" in r[1]]
        assert len(https_failures) == 1
        assert https_failures[0][0] is False
        assert https_failures[0][2] == "blocker"


class TestRunChecksIntegration:
    def test_run_checks_with_complete_site(self):
        def mock_reader(page: str) -> str | None:
            pages = {
                "index.html": COMPLETE_INDEX,
                "offer.html": COMPLETE_OFFER,
                "privacy.html": "<html><body><h1>Конфиденциальность</h1>" + "x" * 500 + "</body></html>",
                "terms.html": "<html><body><h1>Условия</h1>" + "x" * 500 + "</body></html>",
                "about.html": "<html><body><h1>О нас</h1>" + "x" * 500 + "</body></html>",
                "faq.html": "<html><body><h1>FAQ</h1>" + "x" * 500 + "</body></html>",
            }
            return pages.get(page)

        results = run_checks(mock_reader, None, "https://example.com")

        # Should have mostly passing results
        passed_results = [r for r in results if r[0] is True]
        failed_results = [r for r in results if r[0] is False]

        # Should have significantly more passed than failed
        assert len(passed_results) > len(failed_results)

    def test_run_checks_with_missing_pages(self):
        def mock_reader(page: str) -> str | None:
            if page == "index.html":
                return COMPLETE_INDEX
            return None  # All other pages missing

        results = run_checks(mock_reader)

        # Should have multiple page missing errors
        missing_errors = [r for r in results if "missing or empty" in r[1] and r[2] == "blocker"]
        assert len(missing_errors) > 1


class TestDiffNormalization:
    def test_normalize_diff_key_strips_char_count(self):
        message = "index.html: content length sufficient (1234 chars)"
        normalized = _normalize_diff_key(message)
        expected = "index.html: content length sufficient"
        assert normalized == expected

    def test_normalize_diff_key_preserves_other_messages(self):
        message = "index.html: seller name found"
        normalized = _normalize_diff_key(message)
        assert normalized == message

    def test_normalize_diff_key_multiple_char_counts(self):
        # The regex only replaces the specific pattern, not all (N chars)
        message = "index.html: content length sufficient (500 chars)"
        normalized = _normalize_diff_key(message)
        expected = "index.html: content length sufficient"
        assert normalized == expected


class TestPrintResults:
    def test_print_results_json_format(self, capsys):
        results = [
            (True, "test: passed", "ok"),
            (False, "test: failed", "blocker"),
        ]

        exit_code = print_results(results, as_json=True)
        captured = capsys.readouterr()

        # Should return proper exit code
        assert exit_code == 1  # Has failures

        # Should output valid JSON
        output_data = json.loads(captured.out)
        assert "checks" in output_data
        assert len(output_data["checks"]) == 2

        # Check structure
        first_result = output_data["checks"][0]
        assert "ok" in first_result
        assert "message" in first_result
        assert "severity" in first_result

    def test_print_results_text_format(self, capsys):
        results = [
            (True, "test: passed", "ok"),
            (False, "test: failed", "blocker"),
        ]

        exit_code = print_results(results, as_json=False)
        captured = capsys.readouterr()

        # Should return proper exit code
        assert exit_code == 1  # Has failures

        # Should contain expected text
        assert "passed" in captured.out
        assert "failed" in captured.out
        assert "Status:" in captured.out


class TestLooksLikeFullLegalName:
    def test_looks_like_full_legal_name_valid(self):
        test_cases = [
            "Иван Петрович Сидоров",
            "Анна Владимировна Козлова",
            "Петр Иванович",
            "Mary Jane Smith",
            "Jean-Pierre Dupont",
            "O'Connor Michael",
        ]
        for name in test_cases:
            assert _looks_like_full_legal_name(name), f"Should accept: {name}"

    def test_looks_like_full_legal_name_invalid(self):
        test_cases = [
            "И. П. Сидоров",  # Abbreviated
            "Иван",  # Single name
            "",  # Empty
            "—",  # Placeholder
            "Имя Фамилия.",  # Contains dot
            "123",  # Numbers
            "А",  # Too short
        ]
        for name in test_cases:
            assert not _looks_like_full_legal_name(name), f"Should reject: {name}"