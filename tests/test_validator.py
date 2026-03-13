"""Tests for the validator module."""

from airflow_v2_to_v3.validator import Severity, validate_source


def test_detects_old_import():
    source = "from airflow.operators.bash_operator import BashOperator\n"
    result = validate_source(source)
    assert not result.passed
    assert any(i.code == "AIR302" for i in result.issues)


def test_detects_schedule_interval():
    source = '    schedule_interval="@daily",\n'
    result = validate_source(source)
    assert any(i.code == "AIR311" for i in result.issues)


def test_detects_provide_context():
    source = "    provide_context=True,\n"
    result = validate_source(source)
    assert any(i.code == "AIR301" for i in result.issues)


def test_detects_execution_date():
    source = "    ed = context['execution_date']\n"
    result = validate_source(source)
    assert any("execution_date" in i.message for i in result.issues)


def test_detects_days_ago():
    source = "    start_date = days_ago(1)\n"
    result = validate_source(source)
    assert any("days_ago" in i.message for i in result.issues)


def test_detects_dummy_operator():
    source = "start = DummyOperator(task_id='start')\n"
    result = validate_source(source)
    assert any(i.severity == Severity.WARNING for i in result.issues)


def test_clean_file_passes():
    source = "x = 1\n"
    result = validate_source(source)
    assert result.passed
    assert result.error_count == 0


def test_detects_trigger_rule():
    source = '    trigger_rule="dummy",\n'
    result = validate_source(source)
    assert any("trigger_rule" in i.message.lower() or "dummy" in i.message.lower() for i in result.issues)
