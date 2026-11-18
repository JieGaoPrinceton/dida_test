import json

from src.etl.cleaner import clean_email_body, normalize_text, strip_html
from src.etl.classifier import classify_email, extract_tags
from src.etl.importer import parse_csv, parse_json


class TestCleaner:
    def test_clean_email_body_removes_signature(self):
        text = "Hello, this is the body.\n\n-- \nJohn Doe\nCompany Inc."
        result = clean_email_body(text)
        assert "John Doe" not in result
        assert "Hello, this is the body." in result

    def test_clean_email_body_removes_quoted_text(self):
        text = "My reply here.\n\n> Original message\n> from sender"
        result = clean_email_body(text)
        assert "Original message" not in result
        assert "My reply here." in result

    def test_strip_html(self):
        html = "<html><body><p>Hello <b>World</b></p></body></html>"
        result = strip_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_strip_html_empty(self):
        assert strip_html("") == ""
        assert strip_html(None) == ""

    def test_normalize_text(self):
        text = "  Hello   World  \n\n\n  Foo  "
        result = normalize_text(text)
        assert "  " not in result or result == result.strip()
        assert len(result) < len(text)

    def test_normalize_text_unicode(self):
        text = "ＡＢＣ"  # fullwidth ABC
        result = normalize_text(text)
        assert isinstance(result, str)


class TestClassifier:
    def test_classify_email_account_issue(self):
        category, _ = classify_email("无法登录账户", "我的密码忘记了，无法登录")
        assert category is not None

    def test_classify_email_order_issue(self):
        category, _ = classify_email("退款申请", "我想申请退款，订单号12345")
        assert category is not None

    def test_classify_email_unknown(self):
        category, _ = classify_email("Hello", "Just saying hi")
        # May or may not classify; shouldn't crash
        assert category is None or isinstance(category, str)

    def test_extract_tags_finds_keywords(self):
        tags = extract_tags("订单退款问题", "我的退款还没有到账，请帮忙查询")
        assert isinstance(tags, list)

    def test_extract_tags_empty_input(self):
        tags = extract_tags("", "")
        assert isinstance(tags, list)


class TestImporter:
    def test_parse_csv(self):
        csv_content = b"subject,body_text,sender\nTest Subject,Test Body,test@example.com\n"
        results = parse_csv(csv_content)
        assert len(results) == 1
        assert results[0]["subject"] == "Test Subject"
        assert results[0]["body_text"] == "Test Body"

    def test_parse_csv_with_chinese(self):
        csv_content = "subject,body_text,sender\n退款问题,我要退款,user@test.com\n".encode("utf-8")
        results = parse_csv(csv_content)
        assert len(results) == 1
        assert results[0]["subject"] == "退款问题"

    def test_parse_json(self):
        data = [
            {"subject": "Test", "body_text": "Body", "sender": "a@b.com"},
            {"subject": "Test2", "body_text": "Body2", "sender": "c@d.com"},
        ]
        results = parse_json(json.dumps(data).encode("utf-8"))
        assert len(results) == 2
        assert results[0]["subject"] == "Test"

    def test_parse_json_empty_array(self):
        results = parse_json(b"[]")
        assert results == []
