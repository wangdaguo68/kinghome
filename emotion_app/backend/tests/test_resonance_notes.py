import os

from app.db import (
    add_resonance_reaction,
    create_resonance_note,
    random_resonance_note,
)


def test_resonance_note_returns_other_users_note(tmp_path) -> None:
    os.environ["APP_DB_PATH"] = str(tmp_path / "app.db")

    create_resonance_note(
        user_id="writer",
        mood_label="很累",
        content="今天真的有点撑不住，但还是想把话放在这里。",
    )

    own_note = random_resonance_note(user_id="writer", mood_label="很累")
    other_note = random_resonance_note(user_id="reader", mood_label="很累")

    assert own_note is None
    assert other_note is not None
    assert other_note["mood_label"] == "很累"


def test_resonance_reaction_counts_and_updates(tmp_path) -> None:
    os.environ["APP_DB_PATH"] = str(tmp_path / "app.db")

    note = create_resonance_note(
        user_id="writer",
        mood_label="有点难过",
        content="只是想知道是不是也有人有过这样的夜晚。",
    )

    first = add_resonance_reaction(
        note_id=str(note["id"]),
        user_id="reader",
        reaction="抱抱你",
    )
    second = add_resonance_reaction(
        note_id=str(note["id"]),
        user_id="reader",
        reaction="我也有过",
    )

    assert first == {"抱抱你": 1}
    assert second == {"我也有过": 1}
