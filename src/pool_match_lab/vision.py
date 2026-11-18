"""Visión por computador: de un cuadro del video a la posición de las bolas en la mesa."""

from dataclasses import dataclass

import cv2
import numpy as np

# Medidas de una mesa de 9 pies, en metros
TABLE_LENGTH = 1.9812
TABLE_WIDTH = 0.9906
BALL_RADIUS = 0.028575
POCKET_RADIUS = 0.062

PX_PER_M = 300  # resolución de la vista cenital normalizada
COLOR_THRESHOLD = 14  # distancia de color (Lab) al paño para considerar que un píxel es bola
RACK_MIN_BALLS = 6  # una mancha con el área de al menos estas bolas es un rack armado


@dataclass
class FrameDetection:
    n_balls: int  # incluye la blanca
    cue_xy: tuple[float, float] | None  # metros desde la esquina superior izquierda
    rack: bool  # hay un grupo compacto de bolas del tamaño de un rack armado


def calibrate(corners_px: np.ndarray) -> np.ndarray:
    """Homografía del video a una vista cenital de la mesa.

    `corners_px`: esquinas del paño en el video, en orden superior izquierda,
    superior derecha, inferior derecha, inferior izquierda, con el largo de la
    mesa en horizontal. Corrige la perspectiva si la cámara no está justo encima.
    """
    w, h = TABLE_LENGTH * PX_PER_M, TABLE_WIDTH * PX_PER_M
    target = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    return cv2.getPerspectiveTransform(np.float32(corners_px), target)


def _pocket_mask() -> np.ndarray:
    """Zonas de las troneras: ahí no se buscan bolas (una tronera oscura parece una bola)."""
    w, h = int(TABLE_LENGTH * PX_PER_M), int(TABLE_WIDTH * PX_PER_M)
    mask = np.zeros((h, w), np.uint8)
    radius = int((POCKET_RADIUS + BALL_RADIUS * 0.5) * PX_PER_M)
    for x in (0, w // 2, w):
        for y in (0, h):
            cv2.circle(mask, (x, y), radius, 255, -1)
    return mask


POCKETS = _pocket_mask()
BALL_AREA = np.pi * (BALL_RADIUS * PX_PER_M) ** 2


def _count_balls(mask: np.ndarray) -> int:
    """Cuenta bolas aunque se toquen (como en el rack), buscando el centro de cada una.

    El centro de una bola es el punto más lejano al borde de su mancha, así que
    se buscan máximos locales de la transformada de distancia.
    """
    radius_px = BALL_RADIUS * PX_PER_M
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    window = np.ones((int(radius_px), int(radius_px)), np.uint8)
    peaks = (dist >= cv2.dilate(dist, window)) & (dist > 0.6 * radius_px)
    n_peaks, _ = cv2.connectedComponents(peaks.astype(np.uint8))
    return n_peaks - 1


def detect(frame: np.ndarray, homography: np.ndarray) -> tuple[FrameDetection, np.ndarray]:
    """Detecta las bolas de un cuadro.

    Devuelve también la máscara de bolas en la vista cenital, que sirve para
    detectar movimiento entre cuadros pero no conviene guardar por cada uno.
    """
    w, h = int(TABLE_LENGTH * PX_PER_M), int(TABLE_WIDTH * PX_PER_M)
    top = cv2.warpPerspective(frame, homography, (w, h))
    lab = cv2.cvtColor(top, cv2.COLOR_BGR2LAB).astype(np.float32)

    # El paño es el color dominante, así que la mediana lo representa aunque cambie la luz
    cloth = np.median(lab.reshape(-1, 3), axis=0)
    distance = np.linalg.norm(lab - cloth, axis=2)
    mask = ((distance > COLOR_THRESHOLD) & (POCKETS == 0)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    n_balls = _count_balls(mask)
    n_blobs, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    largest = stats[1:n_blobs, cv2.CC_STAT_AREA].max(initial=0)
    rack = largest > RACK_MIN_BALLS * BALL_AREA

    # Blanca: un blob claro y poco saturado del tamaño de una bola completa
    hsv = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)
    white = ((hsv[..., 1] < 60) & (hsv[..., 2] > 180) & (mask > 0)).astype(np.uint8)
    n_white, _, wstats, centroids = cv2.connectedComponentsWithStats(white)
    cue_xy = None
    candidates = [i for i in range(1, n_white) if wstats[i, cv2.CC_STAT_AREA] > 0.6 * BALL_AREA]
    if candidates:
        best = max(candidates, key=lambda i: wstats[i, cv2.CC_STAT_AREA])
        cue_xy = (centroids[best][0] / PX_PER_M, centroids[best][1] / PX_PER_M)

    return FrameDetection(n_balls=n_balls, cue_xy=cue_xy, rack=rack), mask
