"""Sample Airflow 2 DAG for testing migration."""

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from airflow.utils.dates import days_ago
from airflow.utils.decorators import apply_defaults
from airflow.models import Variable
from airflow.decorators import dag, task

default_args = {
    "owner": "airflow",
    "start_date": days_ago(1),
}

with DAG(
    dag_id="sample_v2_dag",
    schedule_interval="@daily",
    default_args=default_args,
    catchup=False,
    concurrency=16,
    provide_context=True,
) as dag:

    start = DummyOperator(task_id="start")

    def my_python_callable(**context):
        execution_date = context['execution_date']
        next_ds = context.get('next_ds')
        print(f"Running for {execution_date}")

    run_task = PythonOperator(
        task_id="run_task",
        python_callable=my_python_callable,
        provide_context=True,
    )

    bash_task = BashOperator(
        task_id="bash_task",
        bash_command="echo hello",
    )

    end = DummyOperator(
        task_id="end",
        trigger_rule="dummy",
    )

    wait = ExternalTaskSensor(
        task_id="wait",
        external_dag_id="other_dag",
        use_task_execution_day=True,
    )

    start >> run_task >> bash_task >> wait >> end
