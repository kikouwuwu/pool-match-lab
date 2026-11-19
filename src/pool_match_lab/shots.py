"""Analiza el video de una partida y genera una fila por tiro.

Un tiro es un tramo en que las bolas se mueven, entre dos momentos de reposo.
Comparando la mesa antes y después de cada tiro se sabe cuántas bolas entraron
y si hubo falta.
"""

import argparse
import json
from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pool_match_lab.vision import BALL_AREA, calibrate, detect

MOTION_PX = 0.3 * BALL_AREA  # píxeles de bola que deben cambiar entre cuadros para contar como movimiento
MAX_GAP = 10  # cuadros quietos que se toleran dentro de un mismo tiro (bolas casi detenidas)
MIN_SHOT = 5  # tramos más cortos se descartan (p. ej., la blanca reapareciendo tras una falta)
REST_WINDOW = 5  # cuadros de reposo que se usan para leer la mesa antes y después
RACK_BALLS = 9  # bola 9: un quiebre siempre parte con 9 bolas de color


def segment(moving: list[bool]) -> list[tuple[int, int]]:
    """Agrupa los cuadros en movimiento en tiros `(inicio, fin)`, con fin exclusivo."""
    shots, start, still = [], None, 0
    for i, is_moving in enumerate(moving):
        if is_moving:
            if start is None:
                start = i
            still = 0
        elif start is not None:
            still += 1
            if still > MAX_GAP:
                shots.append((start, i - still + 1))
                start, still = None, 0
    if start is not None:
        shots.append((start, len(moving) - still))
    return [(s, e) for s, e in shots if e - s >= MIN_SHOT]


def _rest_reading(detections, frames: range) -> tuple[int, bool, bool]:
    """Bolas en la mesa, si está la blanca y si hay un rack armado.

    Usa la mayoría de varios cuadros para filtrar ruido.
    """
    window = [detections[i] for i in frames if 0 <= i < len(detections)]
    counts = [d.n_balls for d in window]
    n_balls = max(set(counts), key=counts.count)
    cue_present = sum(d.cue_xy is not None for d in window) > len(window) / 2
    rack = sum(d.rack for d in window) > len(window) / 2
    return n_balls, cue_present, rack


def analyze(video: Path, corners_px: np.ndarray) -> list[dict]:
    homography = calibrate(corners_px)
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)

    detections, moving, previous = [], [], None
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        detection, mask = detect(frame, homography)
        changed = 0 if previous is None else np.count_nonzero(mask != previous)
        moving.append(changed > MOTION_PX)
        detections.append(detection)
        previous = mask
    capture.release()

    rows = []
    for number, (start, end) in enumerate(segment(moving), start=1):
        balls_before, cue_before, is_break = _rest_reading(detections, range(start - REST_WINDOW, start))
        balls_after, cue_after, _ = _rest_reading(detections, range(end, end + REST_WINDOW))
        scratch = cue_before and not cue_after
        # En el rack las bolas se tocan y el conteo falla; ahí manda la regla del juego
        object_before = RACK_BALLS if is_break else balls_before - cue_before
        object_after = balls_after - cue_after

        # Velocidad inicial de la blanca: su mayor desplazamiento en los primeros cuadros
        path = [d.cue_xy for d in detections[start - 1 : end] if d.cue_xy is not None]
        steps = [np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(path)]
        cue_speed = max(steps[:4], default=0.0) * fps

        rows.append({
            "video": video.stem,
            "shot": number,
            "is_break": is_break,
            "start_s": start / fps,
            "duration_s": (end - start) / fps,
            "n_pocketed": max(object_before - object_after, 0),
            "scratch": scratch,
            "cue_speed_ms": cue_speed,
            "cue_travel_m": float(sum(steps)),
            "cue_start_x": path[0][0] if path else None,
            "cue_start_y": path[0][1] if path else None,
            "cue_end_x": None if scratch or not path else path[-1][0],
            "cue_end_y": None if scratch or not path else path[-1][1],
            "balls_left": object_after,
        })
    return rows


def load_corners(video: Path) -> np.ndarray:
    """Lee las esquinas del paño desde el `<video>.json` que acompaña al video.

    La calibración se mide una vez por posición de cámara y se guarda junto al video.
    """
    return parse_corners(json.loads(video.with_suffix(".json").read_text())["corners"])


def parse_corners(text: str) -> np.ndarray:
    return np.float32([[float(v) for v in pair.split(",")] for pair in text.split(";")])


def analyze_to_parquet(video: Path, out_dir: Path, corners: np.ndarray | None = None) -> Path:
    """Analiza un video y guarda sus tiros en `<out_dir>/<video>.parquet`."""
    rows = analyze(video, load_corners(video) if corners is None else corners)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{video.stem}.parquet"
    # Escritura atómica: dbt nunca lee un archivo a medio escribir
    tmp = path.with_suffix(".tmp")
    pq.write_table(pa.Table.from_pylist(rows), tmp)
    tmp.rename(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument(
        "--corners",
        help="Esquinas del paño en píxeles: 'x,y;x,y;x,y;x,y' (sup. izq., sup. der., inf. der., "
        "inf. izq.). Si se omite, se leen de un <video>.json al lado del video.",
    )
    parser.add_argument("--out", type=Path, default=Path("data/shots"))
    args = parser.parse_args()

    corners = parse_corners(args.corners) if args.corners else None
    path = analyze_to_parquet(args.video, args.out, corners)
    print(f"{path}: {pq.read_metadata(path).num_rows} tiros")


if __name__ == "__main__":
    main()
