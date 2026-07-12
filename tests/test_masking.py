"""Тесты маскирования значений идентификаторов.

По кейсу на каждую стратегию: plain, sha256, md5, mac_anonymize, custom_phone_mask.
+ неизвестная стратегия → fallback на plain.
"""

from __future__ import annotations

import hashlib

from src.dynamic.masking import mask_value


class TestPlain:
    def test_plain_returns_same_value(self):
        assert mask_value("hello", "plain") == "hello"

    def test_none_strategy_is_plain(self):
        assert mask_value("hello", None) == "hello"

    def test_empty_value(self):
        assert mask_value("", "plain") == ""


class TestSha256:
    def test_sha256_matches_manual(self):
        expected = hashlib.sha256(b"test_value").hexdigest()
        assert mask_value("test_value", "sha256") == expected

    def test_sha256_deterministic(self):
        a = mask_value("abc", "sha256")
        b = mask_value("abc", "sha256")
        assert a == b
        assert len(a) == 64  # hex SHA-256 = 64 chars


class TestMd5:
    def test_md5_matches_manual(self):
        expected = hashlib.md5(b"test_value").hexdigest()
        assert mask_value("test_value", "md5") == expected

    def test_md5_deterministic(self):
        a = mask_value("abc", "md5")
        b = mask_value("abc", "md5")
        assert a == b
        assert len(a) == 32  # hex MD5 = 32 chars


class TestMacAnonymize:
    def test_standard_mac(self):
        result = mask_value("AA:BB:CC:DD:EE:FF", "mac_anonymize")
        assert result == "AA:BB:00:00:EE:FF"

    def test_lowercase_mac(self):
        result = mask_value("aa:bb:cc:dd:ee:ff", "mac_anonymize")
        assert result == "aa:bb:00:00:ee:ff"

    def test_non_mac_falls_back_to_sha256(self):
        result = mask_value("not_a_mac", "mac_anonymize")
        expected = hashlib.sha256(b"not_a_mac").hexdigest()
        assert result == expected


class TestCustomPhoneMask:
    def test_russian_phone(self):
        result = mask_value("+79998887766", "custom_phone_mask")
        # 11 цифр: 4 + (11-6)=5 звёздочек + 2
        assert result == "+7999*****66"

    def test_phone_with_spaces(self):
        result = mask_value("+7 999 888 77 66", "custom_phone_mask")
        # 11 цифр: 4 + 5 + 2, формат с пробелами сохраняется
        assert result == "+7 999 *****  66"

    def test_short_number_falls_back_to_sha256(self):
        result = mask_value("123", "custom_phone_mask")
        expected = hashlib.sha256(b"123").hexdigest()
        assert result == expected


class TestUnknownStrategy:
    def test_unknown_falls_back_to_plain(self):
        assert mask_value("hello", "some_unknown_strategy") == "hello"
