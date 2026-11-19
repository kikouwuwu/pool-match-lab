"""Orquestación con Dagster.

Tiros (el foco del proyecto):
- Un sensor detecta videos nuevos en `data/videos/` y crea una partición por video.
- `raw/shots`: el análisis de cada video, un Parquet por partición.
- Modelos dbt de tiros: se recalculan solos cuando se analiza un video.

Laboratorio de quiebres:
- `raw/breaks`: simulaciones, una partición por experimento de `experiments.yml`.
- Modelos dbt de quiebres: se recalculan solos cuando llega un experimento.

En ambos casos los tests de dbt quedan como asset checks.
"""

import os
import sys
from pathlib import Path

import dagster as dg
import pyarrow.parquet as pq
import yaml
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

from pool_match_lab.run_batch import run
from pool_match_lab.shots import analyze_to_parquet

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
EXPERIMENTS = yaml.safe_load((ROOT / "experiments.yml").read_text())

# dbt corre como subproceso dentro de transform/, así que las rutas van absolutas
os.environ.setdefault("POOL_RAW_DIR", str(DATA_DIR / "raw"))
os.environ.setdefault("POOL_SHOTS_DIR", str(DATA_DIR / "shots"))
os.environ.setdefault("POOL_VIDEOS_DIR", str(DATA_DIR / "videos"))
os.environ.setdefault("POOL_WAREHOUSE", str(DATA_DIR / "warehouse.duckdb"))

video_partitions = dg.DynamicPartitionsDefinition(name="videos")
experiment_partitions = dg.StaticPartitionsDefinition(list(EXPERIMENTS))


@dg.asset(
    key=["shots", "raw_shots"],
    partitions_def=video_partitions,
    group_name="video",
    description="Tiros detectados en cada video, un Parquet por video.",
)
def raw_shots(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    video = Path(os.environ["POOL_VIDEOS_DIR"]) / f"{context.partition_key}.mp4"
    shots = pq.read_table(analyze_to_parquet(video, Path(os.environ["POOL_SHOTS_DIR"])))
    return dg.MaterializeResult(
        metadata={
            "n_shots": shots.num_rows,
            "balls_pocketed": sum(shots.column("n_pocketed").to_pylist()),
            "scratches": sum(shots.column("scratch").to_pylist()),
        }
    )


def ready_videos(videos_dir: Path) -> list[str]:
    """Videos listos para analizar: los que ya tienen su calibración (`<video>.json`)."""
    return sorted(v.stem for v in videos_dir.glob("*.mp4") if v.with_suffix(".json").exists())


@dg.sensor(target=[raw_shots], default_status=dg.DefaultSensorStatus.RUNNING)
def new_videos(context: dg.SensorEvaluationContext) -> dg.SensorResult:
    """Crea una partición y lanza el análisis por cada video nuevo."""
    known = set(context.instance.get_dynamic_partitions(video_partitions.name))
    new = [v for v in ready_videos(Path(os.environ["POOL_VIDEOS_DIR"])) if v not in known]
    return dg.SensorResult(
        run_requests=[dg.RunRequest(partition_key=v) for v in new],
        dynamic_partitions_requests=[video_partitions.build_add_request(new)] if new else [],
    )


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
        # Recalcular los modelos apenas llegan datos nuevos
        return dg.AutomationCondition.eager()

    def get_group_name(self, dbt_resource_props):
        return "modelado_" + dbt_resource_props["fqn"][1]


dbt_project = DbtProject(project_dir=ROOT / "transform", profiles_dir=ROOT / "transform")
dbt_project.prepare_if_dev()


@dbt_assets(
    manifest=dbt_project.manifest_path, select="tag:tiros", dagster_dbt_translator=Translator()
)
def dbt_shot_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


@dbt_assets(
    manifest=dbt_project.manifest_path, select="tag:quiebres", dagster_dbt_translator=Translator()
)
def dbt_break_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


defs = dg.Definitions(
    assets=[raw_shots, raw_breaks, dbt_shot_models, dbt_break_models],
    sensors=[new_videos],
    # El dbt del mismo entorno de Python, aunque el entorno no esté activado en la terminal
    resources={
        "dbt": DbtCliResource(
            project_dir=dbt_project, dbt_executable=str(Path(sys.executable).parent / "dbt")
        )
    },
)
