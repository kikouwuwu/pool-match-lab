import pyarrow.parquet as pq

from pool_break_lab.run_batch import run, sample_params
from pool_break_lab.simulate import BreakParams, simulate_break


def test_same_seed_gives_same_break():
    params = BreakParams(v0=7.0, cut=0.0, seed=1)
    assert simulate_break(params) == simulate_break(params)


def test_break_result_is_consistent():
    row = simulate_break(BreakParams(v0=8.0, cut=-2.0, seed=3))
    assert row["n_pocketed"] == len(row["pocketed"])
    assert "cue" not in row["pocketed"]
    assert row["nine_on_break"] == ("9" in row["pocketed"])


def test_sample_params_is_deterministic():
    assert sample_params(5, base_seed=10) == sample_params(5, base_seed=10)


def test_run_is_resumable(tmp_path):
    run("test", n=4, base_seed=0, chunk_size=2, workers=2, out=tmp_path)
    exp_dir = tmp_path / "experiment=test"
    first = pq.read_table(exp_dir / "part-00000.parquet")

    # Se borra un bloque y se vuelve a correr: solo se regenera ese bloque, idéntico
    (exp_dir / "part-00001.parquet").unlink()
    run("test", n=4, base_seed=0, chunk_size=2, workers=2, out=tmp_path)

    assert pq.read_table(exp_dir / "part-00000.parquet").equals(first)
    assert pq.read_table(exp_dir / "part-00001.parquet").num_rows == 2
