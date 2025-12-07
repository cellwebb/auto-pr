"""Test module for language code resolution functionality."""

from auto_pr.constants import Languages


class TestLanguageCodeResolution:
    """Test suite for language code resolution."""

    def test_resolve_english_code(self):
        """Test English language code resolution."""
        assert Languages.resolve_code("en") == "English"
        assert Languages.resolve_code("EN") == "English"
        assert Languages.resolve_code("En") == "English"

    def test_resolve_chinese_codes(self):
        """Test Chinese language code resolution."""
        assert Languages.resolve_code("zh") == "Simplified Chinese"
        assert Languages.resolve_code("zh-CN") == "Simplified Chinese"
        assert Languages.resolve_code("zh-cn") == "Simplified Chinese"
        assert Languages.resolve_code("zh-Hans") == "Simplified Chinese"
        assert Languages.resolve_code("zh-hans") == "Simplified Chinese"
        assert Languages.resolve_code("zh-TW") == "Traditional Chinese"
        assert Languages.resolve_code("zh-tw") == "Traditional Chinese"
        assert Languages.resolve_code("zh-Hant") == "Traditional Chinese"
        assert Languages.resolve_code("zh-hant") == "Traditional Chinese"

    def test_resolve_cjk_codes(self):
        """Test CJK language codes."""
        assert Languages.resolve_code("ja") == "Japanese"
        assert Languages.resolve_code("JA") == "Japanese"
        assert Languages.resolve_code("ko") == "Korean"
        assert Languages.resolve_code("KO") == "Korean"

    def test_resolve_european_codes(self):
        """Test European language codes."""
        assert Languages.resolve_code("es") == "Spanish"
        assert Languages.resolve_code("pt") == "Portuguese"
        assert Languages.resolve_code("fr") == "French"
        assert Languages.resolve_code("de") == "German"
        assert Languages.resolve_code("ru") == "Russian"
        assert Languages.resolve_code("it") == "Italian"
        assert Languages.resolve_code("pl") == "Polish"
        assert Languages.resolve_code("nl") == "Dutch"
        assert Languages.resolve_code("sv") == "Swedish"
        assert Languages.resolve_code("el") == "Greek"
        assert Languages.resolve_code("da") == "Danish"
        assert Languages.resolve_code("no") == "Norwegian"
        assert Languages.resolve_code("nb") == "Norwegian"
        assert Languages.resolve_code("nn") == "Norwegian"
        assert Languages.resolve_code("fi") == "Finnish"

    def test_resolve_other_codes(self):
        """Test other language codes."""
        assert Languages.resolve_code("hi") == "Hindi"
        assert Languages.resolve_code("tr") == "Turkish"
        assert Languages.resolve_code("vi") == "Vietnamese"
        assert Languages.resolve_code("th") == "Thai"
        assert Languages.resolve_code("id") == "Indonesian"
        assert Languages.resolve_code("ar") == "Arabic"
        assert Languages.resolve_code("he") == "Hebrew"

    def test_resolve_full_names_passthrough(self):
        """Test that full language names are passed through unchanged."""
        assert Languages.resolve_code("Spanish") == "Spanish"
        assert Languages.resolve_code("Simplified Chinese") == "Simplified Chinese"
        assert Languages.resolve_code("Traditional Chinese") == "Traditional Chinese"
        assert Languages.resolve_code("Japanese") == "Japanese"
        assert Languages.resolve_code("Korean") == "Korean"
        assert Languages.resolve_code("English") == "English"

    def test_resolve_custom_languages(self):
        """Test that unknown codes/names are passed through for custom languages."""
        assert Languages.resolve_code("Klingon") == "Klingon"
        assert Languages.resolve_code("Elvish") == "Elvish"
        assert Languages.resolve_code("xyz") == "xyz"
        assert Languages.resolve_code("Unknown") == "Unknown"

    def test_resolve_case_insensitivity(self):
        """Test that language codes are case-insensitive."""
        assert Languages.resolve_code("ES") == "Spanish"
        assert Languages.resolve_code("Es") == "Spanish"
        assert Languages.resolve_code("eS") == "Spanish"
        assert Languages.resolve_code("ZH-CN") == "Simplified Chinese"
        assert Languages.resolve_code("Zh-Cn") == "Simplified Chinese"

    def test_resolve_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        assert Languages.resolve_code(" es ") == "Spanish"
        assert Languages.resolve_code("  ja  ") == "Japanese"
        assert Languages.resolve_code("\tzh-CN\t") == "Simplified Chinese"
