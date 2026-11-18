import pytest

from pool_match_lab.shots import MAX_GAP, MIN_SHOT, analyze, segment
from pool_match_lab.synthetic import simulate_game, table_corners_px


def test_segment_splits_on_long_rest():
    moving = [False] * 3 + [True] * 10 + [False] * (MAX_GAP + 5) + [True] * 8 + [False] * 3
    assert segment(moving) == [(3, 13), (13 + MAX_GAP + 5, 13 + MAX_GAP + 13)]


def test_segment_keeps_short_pauses_inside_one_shot():
    moving = [True] * 10 + [False] * (MAX_GAP - 2) + [True] * 10
    assert len(segment(moving)) == 1


def test_segment_drops_blips():
    assert segment([False] * 5 + [True] * (MIN_SHOT - 1) + [False] * 30) == []


@pytest.fixture(scope="module")
def synthetic_game(tmp_path_factory):
    video = tmp_path_factory.mktemp("video") / "partida.mp4"
    truths, table = simulate_game(n_shots=4, seed=1, video_path=str(video))
    return truths, analyze(video, table_corners_px(table))


def test_detects_every_shot(synthetic_game):
    truths, rows = synthetic_game
    assert len(rows) == len(truths)
    assert rows[0]["is_break"]


def test_matches_simulated_outcome(synthetic_game):
    truths, rows = synthetic_game
    assert [r["n_pocketed"] for r in rows] == [t.n_pocketed for t in truths]
    assert [r["scratch"] for r in rows] == [t.scratch for t in truths]
