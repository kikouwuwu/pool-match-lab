"""Partidas sintéticas: se simulan con pooltool y se dibujan como video cenital.

Sirven para probar el analizador con una respuesta conocida: además del video,
se devuelve lo que realmente pasó en cada tiro.
"""

import random
from dataclasses import dataclass

import cv2
import numpy as np
import pooltool as pt

FPS = 30
PX_PER_M = 400  # resolución del video: píxeles por metro de mesa
RAIL_PX = 40  # ancho de la banda alrededor del paño
REST_SECONDS = 1.0  # pausa entre tiros, como cuando el jugador camina a la blanca

CLOTH_BGR = (60, 120, 20)
RAIL_BGR = (30, 50, 90)
BALL_BGR = {
    "cue": (235, 235, 235),
    "1": (0, 210, 240),
    "2": (180, 60, 10),
    "3": (30, 30, 200),
    "4": (120, 30, 90),
    "5": (0, 120, 240),
    "6": (40, 80, 10),
    "7": (20, 20, 110),
    "8": (15, 15, 15),
    "9": (0, 210, 240),  # amarilla con franja blanca
}


@dataclass
class ShotTruth:
    """Lo que realmente pasó en un tiro, según la simulación."""

    v0: float
    n_pocketed: int
    scratch: bool


def table_corners_px(table: pt.Table) -> np.ndarray:
    """Esquinas del paño en el video, en el orden que espera `vision.calibrate`."""
    w, h = table.l * PX_PER_M, table.w * PX_PER_M
    return np.float32(
        [[RAIL_PX, RAIL_PX], [RAIL_PX + w, RAIL_PX], [RAIL_PX + w, RAIL_PX + h], [RAIL_PX, RAIL_PX + h]]
    )


def _to_px(x: float, y: float) -> tuple[int, int]:
    # El largo de la mesa (eje y de pooltool) queda horizontal en el video
    return int(RAIL_PX + y * PX_PER_M), int(RAIL_PX + x * PX_PER_M)


def _draw(table: pt.Table, positions: dict[str, np.ndarray], rng: np.random.Generator) -> np.ndarray:
    w = int(table.l * PX_PER_M) + 2 * RAIL_PX
    h = int(table.w * PX_PER_M) + 2 * RAIL_PX
    frame = np.full((h, w, 3), RAIL_BGR, np.uint8)
    cv2.rectangle(frame, (RAIL_PX, RAIL_PX), (w - RAIL_PX, h - RAIL_PX), CLOTH_BGR, -1)
    for pocket in table.pockets.values():
        cv2.circle(frame, _to_px(*pocket.center[:2]), int(pocket.radius * PX_PER_M), (0, 0, 0), -1)

    radius = int(pt.BallParams.default().R * PX_PER_M)
    for ball_id, pos in positions.items():
        center = _to_px(*pos[:2])
        cv2.circle(frame, center, radius, BALL_BGR[ball_id], -1, cv2.LINE_AA)
        if ball_id == "9":
            band = np.zeros(frame.shape[:2], np.uint8)
            cv2.rectangle(band, (center[0] - radius, center[1] - radius // 3),
                          (center[0] + radius, center[1] + radius // 3), 255, -1)
            disk = np.zeros_like(band)
            cv2.circle(disk, center, radius, 255, -1)
            frame[(band > 0) & (disk > 0)] = BALL_BGR["cue"]

    # Ruido de sensor y algo de desenfoque, para no probar con imágenes perfectas
    noise = rng.normal(0, 4, frame.shape)
    frame = np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(frame, (3, 3), 0)


def _on_table(system: pt.System) -> dict[str, np.ndarray]:
    return {
        ball_id: ball.state.rvw[0]
        for ball_id, ball in system.balls.items()
        if ball.state.s != pt.constants.pocketed
    }


def simulate_game(n_shots: int, seed: int, video_path: str) -> tuple[list[ShotTruth], pt.Table]:
    """Simula un quiebre y `n_shots - 1` tiros a la bola más baja, y escribe el video.

    Los cuadros se escriben a medida que se dibujan: una partida completa en
    memoria pesa varios GB.
    """
    random.seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)

    table = pt.Table.default()
    system = pt.System(
        table=table,
        balls=pt.get_rack(pt.GameType.NINEBALL, table),
        cue=pt.Cue(cue_ball_id="cue"),
    )
    head_spot = system.balls["cue"].state.rvw[0].copy()
    corners = table_corners_px(table)
    size = (int(corners[2][0]) + RAIL_PX, int(corners[2][1]) + RAIL_PX)
    writer = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*"mp4v"), FPS, size)

    def rest() -> None:
        for _ in range(int(REST_SECONDS * FPS)):
            writer.write(_draw(table, _on_table(system), rng))

    truths = []
    for shot in range(n_shots):
        targets = sorted((b for b in _on_table(system) if b != "cue"), key=int)
        if not targets:
            break
        rest()

        before = set(_on_table(system))
        v0 = rng.uniform(5, 8) if shot == 0 else rng.uniform(1.5, 4)
        cut = rng.uniform(-3, 3) if shot == 0 else rng.uniform(-25, 25)
        system.reset_history()
        system.cue.set_state(V0=v0, phi=pt.aim.at_ball(system, targets[0], cut=cut))
        pt.simulate(system, inplace=True, continuous=True, dt=1 / FPS)

        for i in range(len(system.balls["cue"].history_cts.states)):
            positions = {}
            for ball_id, ball in system.balls.items():
                states = ball.history_cts.states
                state = states[min(i, len(states) - 1)]
                if state.s != pt.constants.pocketed:
                    positions[ball_id] = state.rvw[0]
            writer.write(_draw(table, positions, rng))

        pocketed = before - set(_on_table(system))
        truths.append(ShotTruth(v0=v0, n_pocketed=len(pocketed - {"cue"}), scratch="cue" in pocketed))

        if "cue" in pocketed:
            # Bola en mano: la mesa queda un momento sin blanca y luego vuelve al punto de salida
            rest()
            system.balls["cue"].state = pt.objects.BallState(
                rvw=np.array([head_spot, np.zeros(3), np.zeros(3)]), s=pt.constants.stationary, t=0
            )

    rest()
    writer.release()
    return truths, table


def main() -> None:
    import argparse
    import json
    from dataclasses import asdict
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Genera el video de una partida simulada")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--shots", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("data/videos"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    video = args.out / f"sintetica_{args.seed}.mp4"
    truths, table = simulate_game(args.shots, args.seed, str(video))
    corners = ";".join(f"{x:.0f},{y:.0f}" for x, y in table_corners_px(table))
    sidecar = {"corners": corners, "truth": [asdict(t) for t in truths]}
    video.with_suffix(".json").write_text(json.dumps(sidecar, indent=2))
    print(f"{video}: {len(truths)} tiros")


if __name__ == "__main__":
    main()
