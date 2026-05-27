"""Tests for internationalization."""

import pytest
import os

from src.utils.i18n import I18n


class TestI18n:
    """Test cases for I18n class."""
    
    def test_default_language(self):
        """Test default language selection."""
        i18n = I18n("auto")
        assert i18n.language in ["en_US", "es_ES"]
    
    def test_manual_language_en(self):
        """Test setting English language manually."""
        i18n = I18n("en_US")
        assert i18n.language == "en_US"
    
    def test_manual_language_es(self):
        """Test setting Spanish language manually."""
        i18n = I18n("es_ES")
        assert i18n.language == "es_ES"
    
    def test_invalid_language(self):
        """Test handling of invalid language code."""
        i18n = I18n("invalid")
        assert i18n.language == "en_US"  # Should default to English
    
    def test_translation_english(self):
        """Test English translation."""
        i18n = I18n("en_US")
        text = i18n.t("setup_welcome")
        assert "Welcome" in text
    
    def test_translation_spanish(self):
        """Test Spanish translation."""
        i18n = I18n("es_ES")
        text = i18n.t("setup_welcome")
        assert "Bienvenido" in text
    
    def test_translation_with_args(self):
        """Test translation with formatting arguments."""
        i18n = I18n("en_US")
        text = i18n.t("setup_error", "test error")
        assert "test error" in text
    
    def test_missing_key(self):
        """Test handling of missing translation key."""
        i18n = I18n("en_US")
        text = i18n.t("nonexistent.key")
        assert text == "nonexistent.key"
    
    def test_set_language(self):
        """Test changing language dynamically."""
        i18n = I18n("en_US")
        assert i18n.language == "en_US"
        
        i18n.set_language("es_ES")
        assert i18n.language == "es_ES"
    
    def test_lang_detection(self, monkeypatch):
        """Test language detection from LANG environment variable."""
        monkeypatch.setenv("LANG", "es_ES.UTF-8")
        i18n = I18n("auto")
        assert i18n.language == "es_ES"
