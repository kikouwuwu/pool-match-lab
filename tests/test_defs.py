from itertools import pairwise

import dagster as dg

from pool_match_lab.defs import EXPERIMENTS, defs


def test_definitions_load():
    dg.Definitions.validate_loadable(defs)


def test_each_experiment_is_a_partition():
    raw = defs.resolve_assets_def(dg.AssetKey(["raw", "breaks"]))
    assert set(raw.partitions_def.get_partition_keys()) == set(EXPERIMENTS)


def test_experiment_seeds_do_not_overlap():
    ranges = sorted((cfg["seed"], cfg["seed"] + cfg["n"]) for cfg in EXPERIMENTS.values())
    for (_, end), (start, _) in pairwise(ranges):
        assert end <= start
