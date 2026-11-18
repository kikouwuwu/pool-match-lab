"""Simulación de un quiebre de bola 9 con pooltool."""

import random
from dataclasses import asdict, dataclass

import numpy as np
import pooltool as pt


@dataclass(frozen=True)
class BreakParams:
    v0: float  # velocidad inicial de la blanca (m/s)
    cut: float  # desvío respecto del centro de la bola 1 (grados)
    a: float = 0.0  # efecto lateral, de -1 a 1
    b: float = 0.0  # efecto vertical, de -1 a 1
    seed: int = 0


def simulate_break(params: BreakParams) -> dict:
    """Simula un quiebre y devuelve una fila con el resultado.

    pooltool no expone una semilla propia: el armado del rack usa `random`
    y `numpy`, así que se fijan ambas para que cada quiebre sea reproducible.
    """
    random.seed(params.seed)
    np.random.seed(params.seed)

    table = pt.Table.default()
    system = pt.System(
        table=table,
        balls=pt.get_rack(pt.GameType.NINEBALL, table),
        cue=pt.Cue(cue_ball_id="cue"),
    )
    system.cue.set_state(
        V0=params.v0,
        phi=pt.aim.at_ball(system, "1", cut=params.cut),
        a=params.a,
        b=params.b,
    )
    pt.simulate(system, inplace=True)

    pocketed = sorted(
        ball_id
        for ball_id, ball in system.balls.items()
        if ball.state.s == pt.constants.pocketed
    )
    object_balls = [ball_id for ball_id in pocketed if ball_id != "cue"]

    return {
        **asdict(params),
        "pocketed": object_balls,
        "n_pocketed": len(object_balls),
        "scratch": "cue" in pocketed,
        "nine_on_break": "9" in object_balls,
        "n_events": len(system.events),
        "sim_time_s": float(system.t),
    }
