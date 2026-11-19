from itertools import pairwise

import dagster as dg

from pool_match_lab.defs import EXPERIMENTS, defs, new_videos, video_partitions


def test_definitions_load():
    dg.Definitions.validate_loadable(defs)


def test_each_experiment_is_a_partition():
    raw = defs.resolve_assets_def(dg.AssetKey(["raw", "breaks"]))
    assert set(raw.partitions_def.get_partition_keys()) == set(EXPERIMENTS)


def test_experiment_seeds_do_not_overlap():
    ranges = sorted((cfg["seed"], cfg["seed"] + cfg["n"]) for cfg in EXPERIMENTS.values())
    for (_, end), (start, _) in pairwise(ranges):
        assert end <= start


def test_sensor_only_picks_new_calibrated_videos(tmp_path, monkeypatch):
    monkeypatch.setenv("POOL_VIDEOS_DIR", str(tmp_path))
    for name in ("lunes", "martes", "sin_calibrar"):
        (tmp_path / f"{name}.mp4").touch()
    for name in ("lunes", "martes"):
        (tmp_path / f"{name}.json").write_text('{"corners": "0,0;1,0;1,1;0,1"}')

    with dg.instance_for_test() as instance:
        instance.add_dynamic_partitions(video_partitions.name, ["lunes"])
        result = new_videos(dg.build_sensor_context(instance=instance))

    assert [r.partition_key for r in result.run_requests] == ["martes"]
    assert result.dynamic_partitions_requests[0].partition_keys == ["martes"]
