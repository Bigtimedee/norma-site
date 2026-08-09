"""
Unit tests for the tweet-text sanitizer in content_generator.
No network or credentials required.
"""

from __future__ import annotations

import pytest

from content_generator import sanitize_tweet, _truncate_at_word


# ── sanitize_tweet ───────────────────────────────────────────────────────────

def test_clean_input_passes_through():
    text = "Big games today. Track every alert with NORMA 🏆 #NFL"
    assert sanitize_tweet(text) == text


def test_strips_heres_a_tweet_preamble():
    text = "Here's a tweet for you:\nBig games today. Track every alert with NORMA 🏆 #NFL"
    result = sanitize_tweet(text)
    assert result == "Big games today. Track every alert with NORMA 🏆 #NFL"


def test_strips_separator_and_char_count():
    text = (
        "Big games today. Track every alert with NORMA 🏆 #NFL\n"
        "---\n"
        "**Character count: 52**"
    )
    result = sanitize_tweet(text)
    assert result == "Big games today. Track every alert with NORMA 🏆 #NFL"
    assert "---" not in result
    assert "Character count" not in result


def test_strips_full_meta_commentary_block():
    text = (
        "Here's a tweet for you:\n"
        "Big games tonight — Chiefs vs. Eagles on prime time. "
        "Get every alert the second it drops. 🏈 #NFL #Chiefs\n"
        "---\n"
        "**Character count: 121**"
    )
    result = sanitize_tweet(text)
    assert result.startswith("Big games tonight")
    assert "Here's" not in result
    assert "Character count" not in result
    assert "---" not in result


def test_strips_here_is_a_tweet_variant():
    text = "Here is a tweet:\nSome tweet content here."
    result = sanitize_tweet(text)
    assert result == "Some tweet content here."


def test_strips_tweet_colon_preamble():
    text = "Tweet:\nSome tweet content here."
    result = sanitize_tweet(text)
    assert result == "Some tweet content here."


def test_char_count_inline_without_separator():
    text = "Some tweet content.\n**Character count: 19**"
    result = sanitize_tweet(text)
    assert result == "Some tweet content."


# ── _truncate_at_word ────────────────────────────────────────────────────────

def test_truncate_under_limit_unchanged():
    text = "Short tweet."
    assert _truncate_at_word(text, 280) == text


def test_truncate_at_word_boundary():
    # 290-char string; should cut before last word that crosses 280
    text = "word " * 56  # 5 chars * 56 = 280 exactly, then add one more word
    text = text.rstrip() + " extra"  # now 286 chars
    result = _truncate_at_word(text, 280)
    assert len(result) <= 280
    assert not result.endswith(" ")
    # must not cut mid-word
    assert "extra" not in result


def test_truncate_exact_limit_unchanged():
    text = "a" * 280
    assert _truncate_at_word(text, 280) == text


def test_truncate_one_over():
    text = "a" * 281
    result = _truncate_at_word(text, 280)
    # no spaces, so falls back to hard cut
    assert len(result) == 280


def test_over_280_pipeline():
    """Sanitize + truncate together mirrors the _call_claude fallback path."""
    long_preamble = (
        "Here's a tweet for you:\n"
        + ("This is a very long tweet that goes well over the limit. " * 6)
    )
    cleaned = sanitize_tweet(long_preamble)
    assert "Here's" not in cleaned
    if len(cleaned) > 280:
        final = _truncate_at_word(cleaned, 280)
        assert len(final) <= 280
