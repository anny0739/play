import pytest
from diary.counter import count, CHAR_THRESHOLD, WORD_THRESHOLD


def test_empty_string():
    r = count("")
    assert r.char_count == 0
    assert r.word_count == 0
    assert r.goal_met is False


def test_whitespace_only():
    r = count("   \n\t  ")
    assert r.word_count == 0
    assert r.goal_met is False


def test_char_goal_exactly_met():
    text = "가" * CHAR_THRESHOLD
    r = count(text)
    assert r.char_goal_met is True
    assert r.goal_met is True
    assert r.chars_remaining == 0


def test_char_goal_one_short():
    text = "가" * (CHAR_THRESHOLD - 1)
    r = count(text)
    assert r.char_goal_met is False
    assert r.chars_remaining == 1


def test_word_goal_exactly_met():
    text = " ".join(["단어"] * WORD_THRESHOLD)
    r = count(text)
    assert r.word_goal_met is True
    assert r.goal_met is True
    assert r.words_remaining == 0


def test_word_goal_one_short():
    text = " ".join(["단어"] * (WORD_THRESHOLD - 1))
    r = count(text)
    assert r.word_goal_met is False
    assert r.words_remaining == 1


def test_or_condition_word_only():
    """글자 수 미달이지만 단어 수 달성 → goal_met True"""
    text = " ".join(["단어"] * WORD_THRESHOLD)  # 200단어, ~599자
    r = count(text)
    assert r.char_goal_met is False
    assert r.word_goal_met is True
    assert r.goal_met is True


def test_or_condition_char_only():
    """단어 수 미달이지만 글자 수 달성 → goal_met True"""
    text = "가" * CHAR_THRESHOLD  # 900자, 1단어
    r = count(text)
    assert r.char_goal_met is True
    assert r.word_goal_met is False
    assert r.goal_met is True


def test_newline_as_word_separator():
    text = "안녕\n세상\n반가워"
    r = count(text)
    assert r.word_count == 3


def test_mixed_korean_english():
    text = "Hello 세상 world 안녕"
    r = count(text)
    assert r.word_count == 4
    assert r.char_count == len(text)
