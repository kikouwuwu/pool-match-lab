import cv2
import numpy as np

from pool_match_lab.vision import (
    BALL_RADIUS,
    POCKETS,
    PX_PER_M,
    TABLE_LENGTH,
    TABLE_WIDTH,
    _count_balls,
)

R = int(BALL_RADIUS * PX_PER_M)
SHAPE = (int(TABLE_WIDTH * PX_PER_M), int(TABLE_LENGTH * PX_PER_M))


def _balls(*centers_m: tuple[float, float]) -> np.ndarray:
    mask = np.zeros(SHAPE, np.uint8)
    for x, y in centers_m:
        cv2.circle(mask, (round(x * PX_PER_M), round(y * PX_PER_M)), R, 255, -1)
    return mask


def test_ball_next_to_pocket_is_not_hidden():
    # Bola detenida a 5 cm de la esquina del paño: sigue en la mesa y debe verse
    x = y = 0.05
    assert POCKETS[round(y * PX_PER_M), round(x * PX_PER_M)] == 0


def test_touching_balls_count_separately():
    assert _count_balls(_balls((1.0, 0.5), (1.0 + 2 * BALL_RADIUS, 0.5))) == 2


def test_rack_of_nine_plus_cue():
    rack = []
    for row in range(5):
        n = min(row + 1, 5 - row)  # rombo de bola 9: 1, 2, 3, 2, 1
        for i in range(n):
            x = 1.4 + row * BALL_RADIUS * 1.75
            y = 0.5 + (i - (n - 1) / 2) * 2 * BALL_RADIUS
            rack.append((x, y))
    assert _count_balls(_balls(*rack, (0.5, 0.5))) == 10
