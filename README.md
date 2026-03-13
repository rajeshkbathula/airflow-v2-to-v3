# airflow-v2-to-v3

CLI tool to **validate** and **migrate** Apache Airflow 2.x DAGs to Airflow 3.x, built for [Astronomer](https://www.astronomer.io/) (Astro) Airflow.

Ruff's AIR rules flag Airflow 3 compatibility issues but don't auto-fix them — this tool does the actual code transformation.

## Features

- **200+ migration rules** covering import moves, parameter renames, class renames, context variable changes, and more
- **Validate** — scan DAGs for Airflow 3 compatibility issues without modifying files
- **Migrate** — transform Airflow 2 code to Airflow 3 in-place or to a separate output directory
- **Diff** — side-by-side diff output (like a GitHub PR) showing exactly what changed
- **Reserved keyword detection** — flags directories that shadow core Airflow modules (`utils`, `models`, etc.)

## Installation

```bash
pip install airflow-v2-to-v3
```

## Usage

### Validate

Check your DAGs for Airflow 3 compatibility issues:

```bash
airflow-v2-to-v3 validate /path/to/dags/

# Output as JSON
airflow-v2-to-v3 validate /path/to/dags/ --format json

# Output as table
airflow-v2-to-v3 validate /path/to/dags/ --format table
```

### Migrate

Transform your DAGs from Airflow 2 to Airflow 3:

```bash
# In-place migration
airflow-v2-to-v3 migrate /path/to/dags/

# Migrate to a separate directory
airflow-v2-to-v3 migrate /path/to/dags/ -o /path/to/output/

# Dry run (show what would change without modifying files)
airflow-v2-to-v3 migrate /path/to/dags/ --dry-run

# Save diff report to file
airflow-v2-to-v3 migrate /path/to/dags/ --diff-report /path/to/report.txt
```

### Diff

Preview changes without modifying files:

```bash
# Show side-by-side diff in terminal
airflow-v2-to-v3 diff /path/to/dags/

# Save diff report to file
airflow-v2-to-v3 diff /path/to/dags/ -o /path/to/report.txt
```

## What Gets Migrated

| Category | Example |
|----------|---------|
| **Import moves** | `from airflow.operators.dummy import DummyOperator` → `from airflow.providers.standard.operators.empty import EmptyOperator` |
| **SDK moves** | `from airflow.decorators import dag, task` → `from airflow.sdk import dag, task` |
| **Parameter renames** | `schedule_interval="@daily"` → `schedule="@daily"` |
| **Removed parameters** | `provide_context=True` → removed (always provided in Airflow 3) |
| **Context variables** | `context['execution_date']` → `context['logical_date']` |
| **Class renames** | `DummyOperator` → `EmptyOperator` |
| **Dataset → Asset** | `from airflow.datasets import Dataset` → `from airflow.sdk import Asset` |
| **Trigger rules** | `TriggerRule.DUMMY` → `TriggerRule.ALWAYS` |
| **Removed functions** | `days_ago(1)` → `datetime(...)` |

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/rajeshkbathula/airflow-v2-to-v3.git
cd airflow-v2-to-v3
make dev

# Run tests
make test

# Build
make build

# Publish to PyPI
PYPI_TOKEN=your-token make publish
```

## License

Apache 2.0
