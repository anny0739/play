from dataclasses import dataclass

CHAR_THRESHOLD = 900
WORD_THRESHOLD = 200


@dataclass(frozen=True)
class CountResult:
    char_count: int
    word_count: int
    char_goal_met: bool
    word_goal_met: bool
    goal_met: bool
    chars_remaining: int
    words_remaining: int


def count(text: str) -> CountResult:
    char_count = len(text)
    word_count = len(text.split()) if text.strip() else 0
    char_met = char_count >= CHAR_THRESHOLD
    word_met = word_count >= WORD_THRESHOLD
    return CountResult(
        char_count=char_count,
        word_count=word_count,
        char_goal_met=char_met,
        word_goal_met=word_met,
        goal_met=char_met or word_met,
        chars_remaining=max(0, CHAR_THRESHOLD - char_count),
        words_remaining=max(0, WORD_THRESHOLD - word_count),
    )
