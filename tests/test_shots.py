import cv2
import numpy as np
import pooltool as pt
import pytest

from pool_match_lab.shots import MAX_GAP, MIN_SHOT, MOTION_LAG, MotionDetector, analyze, segment
from pool_match_lab.synthetic import CLOTH_BGR, RAIL_PX, simulate_game, table_corners_px
from pool_match_lab.vision import BALL_RADIUS, PX_PER_M


def test_segment_splits_on_long_rest():
    n = MIN_SHOT + 2
    moving = [False] * 3 + [True] * n + [False] * (MAX_GAP + 5) + [True] * n + [False] * 3
    second = 3 + n + MAX_GAP + 5
    assert segment(moving) == [(3, 3 + n), (second, second + n)]


def test_segment_keeps_short_pauses_inside_one_shot():
    moving = [True] * 10 + [False] * (MAX_GAP - 2) + [True] * 10
    assert len(segment(moving)) == 1


def test_segment_drops_blips():
    assert segment([False] * 5 + [True] * (MIN_SHOT - 1) + [False] * 30) == []


def _ball_at(x: int) -> np.ndarray:
    mask = np.zeros((200, 400), np.uint8)
    cv2.circle(mask, (x, 100), int(BALL_RADIUS * PX_PER_M), 255, -1)
    return mask


def test_slow_rolling_ball_counts_as_motion():
    # Una bola que rueda a 1 px por cuadro cambia muy pocos píxeles entre cuadros seguidos.
    # Antes eso se leía como reposo y partía el tiro en dos.
    motion = MotionDetector()
    flags = [motion.update(_ball_at(100 + i)) for i in range(30)]
    assert all(flags[MOTION_LAG:])


def test_still_ball_is_not_motion():
    motion = MotionDetector()
    assert not any(motion.update(_ball_at(100)) for _ in range(30))


def test_flickering_ball_edges_are_not_motion():
    # Con la mesa quieta, el borde de las bolas titila píxel a píxel por ruido y compresión
    rng = np.random.default_rng(0)
    motion = MotionDetector()
    flags = []
    for _ in range(30):
        mask = _ball_at(100)
        ys, xs = rng.integers(0, 200, 120), rng.integers(0, 400, 120)
        mask[ys, xs] = 255 - mask[ys, xs]
        flags.append(motion.update(mask))
    assert not any(flags)


def test_ball_appearing_is_not_a_shot():
    # Tras una falta la blanca reaparece de golpe: no debe contarse como tiro
    motion = MotionDetector()
    masks = [np.zeros((200, 400), np.uint8)] * 20 + [_ball_at(100)] * 20
    assert segment([motion.update(m) for m in masks]) == []


def test_motion_without_cue_movement_is_not_a_shot(tmp_path):
    # Si en un tramo de movimiento la blanca no se desplaza (p. ej., al ponerla en la mesa
    # tras una falta), no es un tiro
    video = tmp_path / "solo_aparece.mp4"
    corners = table_corners_px(pt.Table.default())
    frame = cv2.imread(str(_still_frame(tmp_path)))
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 30, frame.shape[1::-1])
    empty = frame.copy()
    cue = tuple(int(v) for v in corners[0] + 200)
    for i in range(90):
        f = empty.copy()
        if i >= 30:
            cv2.circle(f, cue, 11, (235, 235, 235), -1)
            # Parpadeo de la blanca, como artefactos de compresión, para forzar un tramo largo
            if i < 50 and i % 2:
                cv2.circle(f, cue, 11, CLOTH_BGR, -1)
        writer.write(f)
    writer.release()
    assert analyze(video, corners) == []


def _still_frame(tmp_path):
    path = tmp_path / "mesa.png"
    table = pt.Table.default()
    w, h = (int(c) + RAIL_PX for c in table_corners_px(table)[2])
    frame = np.full((h, w, 3), (30, 50, 90), np.uint8)
    cv2.rectangle(frame, (RAIL_PX, RAIL_PX), (w - RAIL_PX, h - RAIL_PX), CLOTH_BGR, -1)
    cv2.imwrite(str(path), frame)
    return path


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
