"""Orquestación con Dagster.

- `raw/breaks`: simulaciones, una partición por experimento de `experiments.yml`.
- Modelos dbt: se actualizan solos cuando llega un experimento nuevo, y sus
  tests quedan como asset checks.
"""

import os
from pathlib import Path

import dagster as dg
import yaml
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

from pool_break_lab.run_batch import run

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
EXPERIMENTS = yaml.safe_load((ROOT / "experiments.yml").read_text())

# dbt corre como subproceso dentro de transform/, así que las rutas van absolutas
os.environ.setdefault("POOL_RAW_DIR", str(DATA_DIR / "raw"))
os.environ.setdefault("POOL_WAREHOUSE", str(DATA_DIR / "warehouse.duckdb"))

experiment_partitions = dg.StaticPartitionsDefinition(list(EXPERIMENTS))


@dg.asset(
    key=["raw", "breaks"],
    partitions_def=experiment_partitions,
    group_name="simulacion",
    description="Quiebres simulados con pooltool, en Parquet por bloques.",
)
def raw_breaks(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    name = context.partition_key
    config = EXPERIMENTS[name]
    run(
        experiment=name,
        n=config["n"],
        base_seed=config["seed"],
        chunk_size=config.get("chunk_size", 500),
        workers=int(os.environ.get("POOL_WORKERS", os.cpu_count())),
        out=Path(os.environ["POOL_RAW_DIR"]),
    )
    parts = sorted((Path(os.environ["POOL_RAW_DIR"]) / f"experiment={name}").glob("part-*.parquet"))
    return dg.MaterializeResult(
        metadata={"n_breaks": config["n"], "seed": config["seed"], "parts": len(parts)}
    )


class Translator(DagsterDbtTranslator):
    def get_automation_condition(self, dbt_resource_props):
        # Recalcular los modelos apenas se materializa un experimento nuevo
        return dg.AutomationCondition.eager()

    def get_group_name(self, dbt_resource_props):
        return "modelado"


dbt_project = DbtProject(project_dir=ROOT / "transform", profiles_dir=ROOT / "transform")
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path, dagster_dbt_translator=Translator())
def dbt_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


defs = dg.Definitions(
    assets=[raw_breaks, dbt_models],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
