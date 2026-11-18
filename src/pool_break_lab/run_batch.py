"""Corre un experimento de quiebres en paralelo y lo guarda en Parquet.

Cada experimento se escribe en `data/raw/experiment=<nombre>/` en bloques
(`part-00000.parquet`, ...). Si un bloque ya existe se salta, así que un
experimento interrumpido se puede retomar con el mismo comando.
"""

import argparse
import json
import random
from datetime import UTC, datetime
from importlib.metadata import version
from multiprocessing import Pool
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pool_break_lab.simulate import BreakParams, simulate_break

# Rangos del barrido de parámetros
V0_RANGE = (3.0, 10.0)
CUT_RANGE = (-6.0, 6.0)
SPIN_RANGE = (-0.5, 0.5)


def sample_params(n: int, base_seed: int) -> list[BreakParams]:
    rng = random.Random(base_seed)
    return [
        BreakParams(
            v0=rng.uniform(*V0_RANGE),
            cut=rng.uniform(*CUT_RANGE),
            a=rng.uniform(*SPIN_RANGE),
            b=rng.uniform(*SPIN_RANGE),
            seed=base_seed + i,
        )
        for i in range(n)
    ]


def run(experiment: str, n: int, base_seed: int, chunk_size: int, workers: int, out: Path) -> None:
    exp_dir = out / f"experiment={experiment}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    params = sample_params(n, base_seed)
    chunks = [params[i : i + chunk_size] for i in range(0, n, chunk_size)]

    manifest = {
        "experiment": experiment,
        "n": n,
        "base_seed": base_seed,
        "chunk_size": chunk_size,
        "ranges": {"v0": V0_RANGE, "cut": CUT_RANGE, "spin": SPIN_RANGE},
        "pooltool_version": version("pooltool-billiards"),
        "created_at": datetime.now(UTC).isoformat(),
    }
    (exp_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    with Pool(workers) as pool:
        for idx, chunk in enumerate(chunks):
            path = exp_dir / f"part-{idx:05d}.parquet"
            if path.exists():
                print(f"{path.name}: ya existe, se salta")
                continue
            rows = pool.map(simulate_break, chunk)
            # Escritura atómica: un bloque a medio escribir nunca queda con el nombre final
            tmp = path.with_suffix(".tmp")
            pq.write_table(pa.Table.from_pylist(rows), tmp)
            tmp.rename(path)
            print(f"{path.name}: {len(rows)} quiebres")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    run(args.experiment, args.n, args.seed, args.chunk_size, args.workers, args.out)


if __name__ == "__main__":
    main()
