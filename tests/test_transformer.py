"""Tests for the transformer module."""

from pathlib import Path

from airflow_v2_to_v3.transformer import transform_source


FIXTURES = Path(__file__).parent / "fixtures"


def test_import_rewrites():
    source = "from airflow.operators.bash_operator import BashOperator\n"
    result = transform_source(source)
    assert "airflow.providers.standard.operators.bash" in result.transformed
    assert result.changed


def test_schedule_interval_rename():
    source = '    schedule_interval="@daily",\n'
    result = transform_source(source)
    assert 'schedule="@daily"' in result.transformed


def test_provide_context_removed():
    source = '    provide_context=True,\n'
    result = transform_source(source)
    assert "provide_context" not in result.transformed


def test_dummy_to_empty():
    source = "start = DummyOperator(task_id='start')\n"
    result = transform_source(source)
    assert "EmptyOperator" in result.transformed
    assert "DummyOperator" not in result.transformed


def test_days_ago_replaced():
    source = "    start_date=days_ago(1),\n"
    result = transform_source(source)
    assert "pendulum.today('UTC').add(days=-1)" in result.transformed


def test_apply_defaults_removed():
    source = "    @apply_defaults\n    def __init__(self):\n        pass\n"
    result = transform_source(source)
    assert "@apply_defaults" not in result.transformed


def test_context_var_execution_date():
    source = "    ed = context['execution_date']\n"
    result = transform_source(source)
    assert "logical_date" in result.transformed


def test_context_var_next_ds_flagged():
    source = "    nd = context['next_ds']\n"
    result = transform_source(source)
    assert "TODO(airflow3)" in result.transformed


def test_trigger_rule_dummy_renamed():
    source = '    trigger_rule="dummy",\n'
    result = transform_source(source)
    assert '"always"' in result.transformed


def test_concurrency_renamed():
    source = "    concurrency=16,\n"
    result = transform_source(source)
    assert "max_active_tasks=16" in result.transformed


def test_use_task_execution_day():
    source = "    use_task_execution_day=True,\n"
    result = transform_source(source)
    assert "use_task_logical_date=True" in result.transformed


def test_sdk_moves():
    source = "from airflow.models import Variable\n"
    result = transform_source(source)
    assert "airflow.sdk" in result.transformed


def test_decorator_moves():
    source = "from airflow.decorators import dag, task\n"
    result = transform_source(source)
    assert "airflow.sdk" in result.transformed


def test_full_sample_dag():
    source = (FIXTURES / "sample_dag_v2.py").read_text()
    result = transform_source(source, "sample_dag_v2.py")
    assert result.changed
    assert len(result.changes) > 0
    # Should have no leftover v2 patterns
    assert "bash_operator" not in result.transformed
    assert "python_operator" not in result.transformed
    assert "dummy_operator" not in result.transformed
    assert "schedule_interval" not in result.transformed
    assert "DummyOperator" not in result.transformed


def test_unchanged_file():
    source = "x = 1\n"
    result = transform_source(source)
    assert not result.changed
    assert len(result.changes) == 0


def test_dataset_to_asset():
    source = "from airflow.datasets import Dataset\n"
    result = transform_source(source)
    assert "airflow.sdk" in result.transformed
    assert "Asset" in result.transformed
