"""Migration rules for Airflow 2 → 3.

Contains all import mappings, parameter renames, removed APIs, reserved keywords,
and context variable changes needed to migrate DAGs.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Import‑path mappings  (old_module → new_module)
# ---------------------------------------------------------------------------
IMPORT_MOVES: dict[str, str] = {
    # --- standard provider moves (AIR302 / AIR312) -------------------------
    "airflow.operators.bash_operator": "airflow.providers.standard.operators.bash",
    "airflow.operators.bash": "airflow.providers.standard.operators.bash",
    "airflow.operators.python_operator": "airflow.providers.standard.operators.python",
    "airflow.operators.python": "airflow.providers.standard.operators.python",
    "airflow.operators.dummy_operator": "airflow.providers.standard.operators.empty",
    "airflow.operators.dummy": "airflow.providers.standard.operators.empty",
    "airflow.operators.empty": "airflow.providers.standard.operators.empty",
    "airflow.operators.datetime": "airflow.providers.standard.operators.datetime",
    "airflow.operators.trigger_dagrun": "airflow.providers.standard.operators.trigger_dagrun",
    "airflow.operators.dagrun_operator": "airflow.providers.standard.operators.trigger_dagrun",
    "airflow.operators.latest_only_operator": "airflow.providers.standard.operators.latest_only",
    "airflow.operators.latest_only": "airflow.providers.standard.operators.latest_only",
    "airflow.operators.weekday": "airflow.providers.standard.operators.weekday",
    "airflow.sensors.external_task_sensor": "airflow.providers.standard.sensors.external_task",
    "airflow.sensors.external_task": "airflow.providers.standard.sensors.external_task",
    "airflow.sensors.time_delta": "airflow.providers.standard.sensors.time_delta",
    "airflow.sensors.date_time": "airflow.providers.standard.sensors.date_time",
    "airflow.sensors.filesystem": "airflow.providers.standard.sensors.filesystem",
    "airflow.sensors.python": "airflow.providers.standard.sensors.python",
    "airflow.sensors.time_sensor": "airflow.providers.standard.sensors.time",
    "airflow.sensors.weekday": "airflow.providers.standard.sensors.weekday",
    "airflow.sensors.bash": "airflow.providers.standard.sensors.bash",
    "airflow.hooks.filesystem": "airflow.providers.standard.hooks.filesystem",
    "airflow.hooks.package_index": "airflow.providers.standard.hooks.package_index",
    "airflow.hooks.subprocess": "airflow.providers.standard.hooks.subprocess",
    "airflow.triggers.external_task": "airflow.providers.standard.triggers.external_task",
    "airflow.triggers.file": "airflow.providers.standard.triggers.file",
    "airflow.triggers.temporal": "airflow.providers.standard.triggers.temporal",
    # --- SDK moves (AIR311) ------------------------------------------------
    "airflow.models.DAG": "airflow.sdk",
    "airflow.models.dag.DAG": "airflow.sdk",
    "airflow.models.Variable": "airflow.sdk",
    "airflow.models.Connection": "airflow.sdk",
    "airflow.models.baseoperator.BaseOperator": "airflow.sdk",
    "airflow.models.baseoperator.BaseOperatorLink": "airflow.sdk",
    "airflow.models.TaskGroup": "airflow.sdk",
    "airflow.utils.task_group.TaskGroup": "airflow.sdk",
    "airflow.sensors.base.BaseSensorOperator": "airflow.sdk.bases.sensor",
    "airflow.sensors.base_sensor_operator.BaseSensorOperator": "airflow.sdk.bases.sensor",
    "airflow.sensors.base.PokeReturnValue": "airflow.sdk.bases.sensor",
    "airflow.sensors.base.poke_mode_only": "airflow.sdk.bases.sensor",
    "airflow.notifications.basenotifier.BaseNotifier": "airflow.sdk.bases.notifier",
    "airflow.models.Param": "airflow.sdk.definitions.param",
    "airflow.models.param": "airflow.sdk.definitions.param",
    # --- decorator / function moves to SDK ---------------------------------
    "airflow.decorators.dag": "airflow.sdk",
    "airflow.decorators.task": "airflow.sdk",
    "airflow.decorators.task_group": "airflow.sdk",
    "airflow.decorators.setup": "airflow.sdk",
    "airflow.decorators.teardown": "airflow.sdk",
    "airflow.operators.python.get_current_context": "airflow.sdk",
    "airflow.utils.helpers.chain": "airflow.sdk",
    "airflow.utils.helpers.cross_downstream": "airflow.sdk",
    "airflow.models.baseoperator.chain": "airflow.sdk",
    "airflow.models.baseoperator.chain_linear": "airflow.sdk",
    "airflow.models.baseoperator.cross_downstream": "airflow.sdk",
    "airflow.utils.get_parsing_context": "airflow.sdk",
    "airflow.io.ObjectStoragePath": "airflow.sdk",
    "airflow.io.attach": "airflow.sdk.io",
    # --- Dataset → Asset renames -------------------------------------------
    "airflow.datasets.Dataset": "airflow.sdk",
    "airflow.Dataset": "airflow.sdk",
    "airflow.datasets.DatasetAlias": "airflow.sdk",
    "airflow.datasets.DatasetAll": "airflow.sdk",
    "airflow.datasets.DatasetAny": "airflow.sdk",
    "airflow.datasets.metadata.Metadata": "airflow.sdk",
    "airflow.datasets.manager.DatasetManager": "airflow.assets.manager",
    "airflow.datasets.manager.dataset_manager": "airflow.assets.manager",
    "airflow.timetables.simple.DatasetTriggeredTimetable": "airflow.timetables.simple",
    "airflow.timetables.datasets.DatasetOrTimeSchedule": "airflow.timetables.assets",
    # --- legacy provider moves (AIR302) ------------------------------------
    "airflow.hooks.S3_hook": "airflow.providers.amazon.aws.hooks.s3",
    "airflow.hooks.postgres_hook": "airflow.providers.postgres.hooks.postgres",
    "airflow.hooks.mysql_hook": "airflow.providers.mysql.hooks.mysql",
    "airflow.hooks.hive_hooks": "airflow.providers.apache.hive.hooks.hive",
    "airflow.hooks.druid_hook": "airflow.providers.apache.druid.hooks.druid",
    "airflow.hooks.http_hook": "airflow.providers.http.hooks.http",
    "airflow.hooks.docker_hook": "airflow.providers.docker.hooks.docker",
    "airflow.hooks.oracle_hook": "airflow.providers.oracle.hooks.oracle",
    "airflow.hooks.presto_hook": "airflow.providers.presto.hooks.presto",
    "airflow.hooks.jdbc_hook": "airflow.providers.jdbc.hooks.jdbc",
    "airflow.hooks.mssql_hook": "airflow.providers.microsoft.mssql.hooks.mssql",
    "airflow.hooks.samba_hook": "airflow.providers.samba.hooks.samba",
    "airflow.hooks.slack_hook": "airflow.providers.slack.hooks.slack",
    "airflow.hooks.sqlite_hook": "airflow.providers.sqlite.hooks.sqlite",
    "airflow.hooks.zendesk_hook": "airflow.providers.zendesk.hooks.zendesk",
    "airflow.hooks.pig_hook": "airflow.providers.apache.pig.hooks.pig",
    "airflow.hooks.dbapi": "airflow.providers.common.sql.hooks.sql",
    "airflow.hooks.dbapi_hook": "airflow.providers.common.sql.hooks.sql",
    "airflow.hooks.webhdfs_hook": "airflow.providers.apache.hdfs.hooks.webhdfs",
    "airflow.hooks.base_hook": "airflow.hooks.base",
    "airflow.operators.email_operator": "airflow.providers.smtp.operators.smtp",
    "airflow.operators.email": "airflow.providers.smtp.operators.smtp",
    "airflow.operators.http_operator": "airflow.providers.http.operators.http",
    "airflow.operators.docker_operator": "airflow.providers.docker.operators.docker",
    "airflow.operators.hive_operator": "airflow.providers.apache.hive.operators.hive",
    "airflow.operators.hive_stats_operator": "airflow.providers.apache.hive.operators.hive_stats",
    "airflow.operators.pig_operator": "airflow.providers.apache.pig.operators.pig",
    "airflow.operators.slack_operator": "airflow.providers.slack.operators.slack",
    "airflow.operators.papermill_operator": "airflow.providers.papermill.operators.papermill",
    "airflow.operators.check_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.sql": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.postgres_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.mysql_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.sqlite_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.oracle_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.mssql_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.jdbc_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.presto_check_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.druid_check_operator": "airflow.providers.common.sql.operators.sql",
    "airflow.operators.gcs_to_s3": "airflow.providers.amazon.aws.transfers.gcs_to_s3",
    "airflow.operators.s3_file_transform_operator": "airflow.providers.amazon.aws.operators.s3",
    "airflow.operators.s3_to_redshift_operator": "airflow.providers.amazon.aws.transfers.s3_to_redshift",
    "airflow.operators.redshift_to_s3_operator": "airflow.providers.amazon.aws.transfers.redshift_to_s3",
    "airflow.operators.google_api_to_s3_transfer": "airflow.providers.amazon.aws.transfers.google_api_to_s3",
    "airflow.operators.hive_to_druid": "airflow.providers.apache.druid.transfers.hive_to_druid",
    "airflow.operators.hive_to_mysql": "airflow.providers.apache.hive.transfers.hive_to_mysql",
    "airflow.operators.hive_to_samba_operator": "airflow.providers.apache.hive.transfers.hive_to_samba",
    "airflow.operators.mssql_to_hive": "airflow.providers.apache.hive.transfers.mssql_to_hive",
    "airflow.operators.mysql_to_hive": "airflow.providers.apache.hive.transfers.mysql_to_hive",
    "airflow.operators.s3_to_hive_operator": "airflow.providers.apache.hive.transfers.s3_to_hive",
    "airflow.operators.presto_to_mysql": "airflow.providers.mysql.transfers.presto_to_mysql",
    "airflow.sensors.s3_key_sensor": "airflow.providers.amazon.aws.sensors.s3",
    "airflow.sensors.http_sensor": "airflow.providers.http.sensors.http",
    "airflow.sensors.hive_partition_sensor": "airflow.providers.apache.hive.sensors.hive_partition",
    "airflow.sensors.metastore_partition_sensor": "airflow.providers.apache.hive.sensors.metastore_partition",
    "airflow.sensors.named_hive_partition_sensor": "airflow.providers.apache.hive.sensors.named_hive_partition",
    "airflow.sensors.web_hdfs_sensor": "airflow.providers.apache.hdfs.sensors.web_hdfs",
    "airflow.sensors.sql": "airflow.providers.common.sql.sensors.sql",
    "airflow.sensors.sql_sensor": "airflow.providers.common.sql.sensors.sql",
    "airflow.macros.hive": "airflow.providers.apache.hive.macros.hive",
    "airflow.config_templates.default_celery": "airflow.providers.celery.executors.default_celery",
    "airflow.executors.celery_executor": "airflow.providers.celery.executors.celery_executor",
    "airflow.executors.celery_kubernetes_executor": "airflow.providers.celery.executors.celery_kubernetes_executor",
    "airflow.executors.dask_executor": "airflow.providers.daskexecutor.executors.dask_executor",
    "airflow.executors.kubernetes_executor_types": "airflow.providers.cncf.kubernetes.executors.kubernetes_executor_types",
    "airflow.kubernetes.k8s_model": "airflow.providers.cncf.kubernetes.k8s_model",
    "airflow.kubernetes.kube_client": "airflow.providers.cncf.kubernetes.kube_client",
    "airflow.kubernetes.kubernetes_helper_functions": "airflow.providers.cncf.kubernetes.kubernetes_helper_functions",
    "airflow.kubernetes.pod_generator": "airflow.providers.cncf.kubernetes.pod_generator",
    "airflow.kubernetes.pod_generator_deprecated": "airflow.providers.cncf.kubernetes.pod_generator",
    "airflow.kubernetes.pod_launcher": "airflow.providers.cncf.kubernetes.utils.pod_manager",
    "airflow.kubernetes.pod_launcher_deprecated": "airflow.providers.cncf.kubernetes.utils.pod_manager",
    "airflow.kubernetes.secret": "airflow.providers.cncf.kubernetes.secret",
    "airflow.api.auth.backend.basic_auth": "airflow.providers.fab.auth_manager.api.auth.backend.basic_auth",
    "airflow.api.auth.backend.kerberos_auth": "airflow.providers.fab.auth_manager.api.auth.backend.kerberos_auth",
    "airflow.auth.managers.fab.fab_auth_manager": "airflow.providers.fab.auth_manager.fab_auth_manager",
    "airflow.auth.managers.fab.security_manager.override": "airflow.providers.fab.auth_manager.security_manager.override",
    "airflow.www.security": "airflow.providers.fab.auth_manager.security_manager.override",
    # --- utility / misc moves ---------------------------------------------
    "airflow.utils.dates": "pendulum",
    "airflow.utils.decorators": "",  # apply_defaults removed entirely
    "airflow.utils.file.TemporaryDirectory": "tempfile",
    "airflow.utils.log.secrets_masker": "airflow.sdk.execution_time.secrets_masker",
}

# ---------------------------------------------------------------------------
# Class renames  (old_class → new_class)
# ---------------------------------------------------------------------------
CLASS_RENAMES: dict[str, str] = {
    "DummyOperator": "EmptyOperator",
    "ExternalTaskSensorLink": "ExternalDagLink",
    "PodLauncher": "PodManager",
    "PodStatus": "PodPhase",
    "Dataset": "Asset",
    "DatasetAlias": "AssetAlias",
    "DatasetAll": "AssetAll",
    "DatasetAny": "AssetAny",
    "DatasetManager": "AssetManager",
    "DatasetTriggeredTimetable": "AssetTriggeredTimetable",
    "DatasetOrTimeSchedule": "AssetOrTimeSchedule",
    "DatasetLineageInfo": "AssetLineageInfo",
    "DatasetInfo": "AssetInfo",
    "AllowListValidator": "PatternAllowListValidator",
    "BlockListValidator": "PatternBlockListValidator",
    "SubDagOperator": "TaskGroup",
}

# ---------------------------------------------------------------------------
# DAG / operator parameter renames  (old_kwarg → new_kwarg)
# ---------------------------------------------------------------------------
PARAM_RENAMES: dict[str, str | None] = {
    "schedule_interval": "schedule",
    "timetable": "schedule",
    "fail_stop": "fail_fast",
    "concurrency": "max_active_tasks",
    "task_concurrency": "max_active_tis_per_dag",
    "use_task_execution_day": "use_task_logical_date",
    "use_task_execution_date": "use_task_logical_date",
}

# Parameters to remove entirely (value is a comment explaining why)
PARAMS_REMOVED: dict[str, str] = {
    "provide_context": "Context is always provided automatically since Airflow 2.0",
    "sla_miss_callback": "SLA feature removed in Airflow 3",
    "default_view": "Removed in Airflow 3",
    "orientation": "Removed in Airflow 3",
}

# ---------------------------------------------------------------------------
# Removed context variables
# ---------------------------------------------------------------------------
REMOVED_CONTEXT_VARS: dict[str, str | None] = {
    "execution_date": "logical_date",
    "next_ds": None,
    "next_ds_nodash": None,
    "next_execution_date": None,
    "prev_ds": None,
    "prev_ds_nodash": None,
    "prev_execution_date": None,
    "prev_execution_date_success": None,
    "tomorrow_ds": None,
    "tomorrow_ds_nodash": None,
    "yesterday_ds": None,
    "yesterday_ds_nodash": None,
}

# ---------------------------------------------------------------------------
# Functions / utilities removed
# ---------------------------------------------------------------------------
REMOVED_FUNCTIONS: dict[str, str | None] = {
    "days_ago": "pendulum.today('UTC').add(days=-N)",
    "apply_defaults": None,  # remove decorator entirely
    "date_range": None,
    "parse_execution_date": None,
    "round_time": None,
    "scale_time_units": None,
    "infer_time_unit": None,
    "load_connections": "load_connections_dict",
}

# ---------------------------------------------------------------------------
# Reserved keywords that shadow airflow core modules at bundle root
# ---------------------------------------------------------------------------
RESERVED_KEYWORDS: dict[str, str] = {
    "utils": "airflow.utils is a core module — a custom package named 'utils' at the DAG bundle root will shadow it and cause import failures",
    "models": "airflow.models is a core module — avoid naming custom packages 'models'",
    "operators": "airflow.operators is a core module — avoid naming custom packages 'operators'",
    "sensors": "airflow.sensors is a core module — avoid naming custom packages 'sensors'",
    "hooks": "airflow.hooks is a core module — avoid naming custom packages 'hooks'",
}

# ---------------------------------------------------------------------------
# Method / attribute renames  (Dataset → Asset)
# ---------------------------------------------------------------------------
METHOD_RENAMES: dict[str, str] = {
    "register_dataset_change": "register_asset_change",
    "create_datasets": "create_assets",
    "notify_dataset_created": "notify_asset_created",
    "notify_dataset_changed": "notify_asset_changed",
    "notify_dataset_alias_created": "notify_asset_alias_created",
    "create_dataset": "create_asset",
    "add_input_dataset": "add_input_asset",
    "add_output_dataset": "add_output_asset",
    "collected_datasets": "collected_assets",
    "is_authorized_dataset": "is_authorized_asset",
    "initialize_providers_dataset_uri_resources": "initialize_providers_asset_uri_resources",
    "dataset_factories": "asset_factories",
    "dataset_uri_handlers": "asset_uri_handlers",
    "dataset_to_openlineage_converters": "asset_to_openlineage_converters",
    "iter_datasets": "iter_assets",
    "iter_dataset_aliases": "iter_asset_aliases",
    "translate_airflow_dataset": "translate_airflow_asset",
}

# Trigger rule renames
TRIGGER_RULE_RENAMES: dict[str, str] = {
    "dummy": "always",
    "none_failed_or_skipped": "none_failed_min_one_success",
}
