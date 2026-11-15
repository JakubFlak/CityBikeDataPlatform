# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.12"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "e2c7f187-48e5-40c7-bbe8-24659adbdd9e",
# META       "default_lakehouse_name": "lh_citybike",
# META       "default_lakehouse_workspace_id": "dff13992-dc91-47d2-a496-9e564a94a078",
# META       "known_lakehouses": [
# META         {
# META           "id": "e2c7f187-48e5-40c7-bbe8-24659adbdd9e"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

%pip install "builtin/city_bike_data_platform-0.1.0-py3-none-any.whl"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

from bike_data.gbfs import GBFSFeed
from bike_data.storage import RawSnapshotStore

print("Package import successful")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

from pathlib import Path
from datetime import UTC, datetime
import json

import pyarrow as pa
import pyarrow.parquet as pq

TEST_ROOT = Path("/lakehouse/default/Files/bronze/gbfs/_raw_store_test")

TEST_RESULTS = {}
PACKAGE_READY = False

try:
    from bike_data.gbfs import GBFSFeed
    from bike_data.storage import RawSnapshotStore

    PACKAGE_READY = True
    print("PASS | Imported RawSnapshotStore and GBFSFeed from the installed bike_data package")
except Exception as error:
    print(f"FAIL | Package import | {type(error).__name__}: {error}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

OBSERVED_AT_1 = datetime(2026, 11, 14, 18, 0, tzinfo=UTC)
OBSERVED_AT_2 = datetime(2026, 11, 14, 18, 1, tzinfo=UTC)

SOURCE_URL = "https://example.test/gbfs/station_status.json"

FEED_DATA = {
    "stations": [
        {
            "station_id": "fabric-compat-station-001",
            "num_bikes_available": 4,
            "num_docks_available": 8,
            "is_installed": True,
            "is_renting": True,
            "is_returning": True,
            "last_reported": 1794680000,
        }
    ]
}

FEED_PAYLOAD = {
    "last_updated": 1794680000,
    "ttl": 60,
    "version": "2.3",
    "data": FEED_DATA,
    "test_marker": "synthetic-fabric-raw-store-test",
}

feed = None

if PACKAGE_READY:
    try:
        feed = GBFSFeed(
            last_updated=FEED_PAYLOAD["last_updated"],
            ttl=FEED_PAYLOAD["ttl"],
            version=FEED_PAYLOAD["version"],
            data=FEED_DATA,
            payload=FEED_PAYLOAD,
        )
        TEST_RESULTS["GBFSFeed construction"] = "PASS"
        print("PASS | Constructed the real GBFSFeed dataclass with synthetic GBFS data")
    except Exception as error:
        TEST_RESULTS["GBFSFeed construction"] = "FAIL"
        print(f"FAIL | GBFSFeed construction | {type(error).__name__}: {error}")
else:
    TEST_RESULTS["GBFSFeed construction"] = "NOT VERIFIED"
    print("NOT VERIFIED | GBFSFeed construction | package import failed")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

store = None
snapshot_path_1 = None

if PACKAGE_READY and feed is not None:
    try:
        store = RawSnapshotStore(TEST_ROOT)
        TEST_RESULTS["RawSnapshotStore construction"] = "PASS"
        print(f"PASS | Constructed RawSnapshotStore with root {TEST_ROOT}")
    except Exception as error:
        TEST_RESULTS["RawSnapshotStore construction"] = "FAIL"
        print(f"FAIL | RawSnapshotStore construction | {type(error).__name__}: {error}")
else:
    TEST_RESULTS["RawSnapshotStore construction"] = "NOT VERIFIED"
    print("NOT VERIFIED | RawSnapshotStore construction | prerequisite unavailable")

if store is not None and feed is not None:
    try:
        snapshot_path_1 = store.write(
            feed_name="station_status",
            source_url=SOURCE_URL,
            feed=feed,
            observed_at=OBSERVED_AT_1,
        )
        TEST_RESULTS["First RawSnapshotStore.write"] = "PASS"
        print(f"PASS | First snapshot written to {snapshot_path_1}")
    except Exception as error:
        TEST_RESULTS["First RawSnapshotStore.write"] = "FAIL"
        print(f"FAIL | First RawSnapshotStore.write | {type(error).__name__}: {error}")
else:
    TEST_RESULTS["First RawSnapshotStore.write"] = "NOT VERIFIED"
    print("NOT VERIFIED | First RawSnapshotStore.write | prerequisite unavailable")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

if snapshot_path_1 is not None:
    try:
        if not snapshot_path_1.is_file():
            raise AssertionError(f"Expected Parquet file does not exist: {snapshot_path_1}")

        TEST_RESULTS["First snapshot exists"] = "PASS"
        print(f"PASS | Snapshot file exists: {snapshot_path_1}")
    except Exception as error:
        TEST_RESULTS["First snapshot exists"] = "FAIL"
        print(f"FAIL | First snapshot exists | {type(error).__name__}: {error}")
else:
    TEST_RESULTS["First snapshot exists"] = "NOT VERIFIED"
    print("NOT VERIFIED | First snapshot exists | no output path from write")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

EXPECTED_SCHEMA = pa.schema(
    [
        ("feed_name", pa.string()),
        ("source_url", pa.string()),
        ("observed_at", pa.string()),
        ("last_updated", pa.int64()),
        ("ttl", pa.int64()),
        ("version", pa.string()),
        ("data_json", pa.string()),
        ("source_payload_json", pa.string()),
    ]
)

if snapshot_path_1 is not None and snapshot_path_1.is_file():
    try:
        table = pq.ParquetFile(snapshot_path_1).read()

        if table.schema != EXPECTED_SCHEMA:
            raise AssertionError(
                f"Schema mismatch. Expected {EXPECTED_SCHEMA}, got {table.schema}"
            )

        if table.num_rows != 1:
            raise AssertionError(f"Expected one row, got {table.num_rows}")

        row = table.to_pylist()[0]

        expected_values = {
            "feed_name": "station_status",
            "source_url": SOURCE_URL,
            "observed_at": OBSERVED_AT_1.isoformat(),
            "last_updated": FEED_PAYLOAD["last_updated"],
            "ttl": FEED_PAYLOAD["ttl"],
            "version": FEED_PAYLOAD["version"],
            "data_json": json.dumps(
                FEED_DATA, ensure_ascii=True, separators=(",", ":")
            ),
            "source_payload_json": json.dumps(
                FEED_PAYLOAD, ensure_ascii=True, separators=(",", ":")
            ),
        }

        if row != expected_values:
            raise AssertionError(
                f"Value mismatch. Expected {expected_values!r}, got {row!r}"
            )

        TEST_RESULTS["First snapshot Parquet schema and values"] = "PASS"
        print("PASS | Parquet schema, one-row grain, metadata, and JSON payload match")
        print(f"      Columns: {table.column_names}")
    except Exception as error:
        TEST_RESULTS["First snapshot Parquet schema and values"] = "FAIL"
        print(
            "FAIL | First snapshot Parquet schema and values | "
            f"{type(error).__name__}: {error}"
        )
else:
    TEST_RESULTS["First snapshot Parquet schema and values"] = "NOT VERIFIED"
    print("NOT VERIFIED | First snapshot Parquet schema and values | file unavailable")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

snapshot_path_2 = None

if store is not None and feed is not None:
    try:
        snapshot_path_2 = store.write(
            feed_name="station_status",
            source_url=SOURCE_URL,
            feed=feed,
            observed_at=OBSERVED_AT_2,
        )

        if snapshot_path_2 == snapshot_path_1:
            raise AssertionError("Different observations unexpectedly resolved to one path")

        TEST_RESULTS["Second RawSnapshotStore.write"] = "PASS"
        print(f"PASS | Second snapshot written to {snapshot_path_2}")
    except Exception as error:
        TEST_RESULTS["Second RawSnapshotStore.write"] = "FAIL"
        print(f"FAIL | Second RawSnapshotStore.write | {type(error).__name__}: {error}")
else:
    TEST_RESULTS["Second RawSnapshotStore.write"] = "NOT VERIFIED"
    print("NOT VERIFIED | Second RawSnapshotStore.write | prerequisite unavailable")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

if snapshot_path_1 is not None and snapshot_path_2 is not None:
    try:
        if not snapshot_path_1.is_file():
            raise AssertionError(f"First snapshot is missing: {snapshot_path_1}")
        if not snapshot_path_2.is_file():
            raise AssertionError(f"Second snapshot is missing: {snapshot_path_2}")

        first_row = pq.ParquetFile(snapshot_path_1).read().to_pylist()[0]
        second_row = pq.ParquetFile(snapshot_path_2).read().to_pylist()[0]

        if first_row["observed_at"] != OBSERVED_AT_1.isoformat():
            raise AssertionError("First snapshot has an unexpected observed_at")
        if second_row["observed_at"] != OBSERVED_AT_2.isoformat():
            raise AssertionError("Second snapshot has an unexpected observed_at")

        snapshots = sorted(TEST_ROOT.rglob("snapshot.parquet"))
        if snapshot_path_1 not in snapshots or snapshot_path_2 not in snapshots:
            raise AssertionError(
                f"Expected both files in nested discovery; discovered {snapshots!r}"
            )

        TEST_RESULTS["Both observations remain available"] = "PASS"
        print("PASS | Both distinct observation timestamps are readable and discoverable")
        print(f"      {snapshot_path_1}")
        print(f"      {snapshot_path_2}")
    except Exception as error:
        TEST_RESULTS["Both observations remain available"] = "FAIL"
        print(
            "FAIL | Both observations remain available | "
            f"{type(error).__name__}: {error}"
        )
else:
    TEST_RESULTS["Both observations remain available"] = "NOT VERIFIED"
    print("NOT VERIFIED | Both observations remain available | prerequisite unavailable")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

print("RawSnapshotStore Fabric integration test results:")
for name, status in TEST_RESULTS.items():
    print(f"{status} | {name}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 1 — Imports and paths

# CELL ********************

from pathlib import Path
import json

import pyarrow.parquet as pq

RAW_ROOT = Path(
    "/lakehouse/default/Files/bronze/gbfs/_raw_store_test"
)
SILVER_ROOT = Path(
    "/lakehouse/default/Files/silver/_raw_to_silver_test"
)
STATE_PATH = SILVER_ROOT / "_incremental_state.json"

from bike_data.incremental import incremental_raw_to_silver
from bike_data.silver import SILVER_TABLES, TABLE_SCHEMAS

print("PASS | Imported the existing incremental Raw-to-Silver function and schemas")
print(f"Raw input: {RAW_ROOT}")
print(f"Isolated Silver output: {SILVER_ROOT}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 2 — Inspect and preflight the two Raw snapshots
# This verifies the test input is exactly the two intended station_status snapshots. It tests both ParquetFile.read() and the exact pq.read_table(file_path) operation used by the existing function.

# CELL ********************


raw_files = sorted(RAW_ROOT.rglob("snapshot.parquet"))

if len(raw_files) != 2:
    raise RuntimeError(
        f"Expected exactly two test snapshots under {RAW_ROOT}; found {len(raw_files)}: "
        f"{raw_files}"
    )

raw_rows = []

for path in raw_files:
    try:
        # Read a single Parquet file without Hive partition discovery.
        parquet_file_row = pq.ParquetFile(path).read().to_pylist()[0]

        if parquet_file_row["feed_name"] != "station_status":
            raise AssertionError(
                f"Unexpected feed in {path}: {parquet_file_row['feed_name']!r}"
            )

        if parquet_file_row["observed_at"] is None:
            raise AssertionError(f"Missing observed_at in {path}")

        raw_rows.append(parquet_file_row)

        print(f"PASS | ParquetFile.read() works for {path}")

    except Exception as error:
        print(
            f"FAIL | Raw Parquet preflight for {path} | "
            f"{type(error).__name__}: {error}"
        )
        raise

identities = {
    f"{row['feed_name']}|{row['observed_at']}"
    for row in raw_rows
}

if len(identities) != 2:
    raise AssertionError(f"Expected two distinct Raw identities; found {identities}")

print(f"PASS | Found two distinct station_status snapshots: {sorted(identities)}")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 3 — Run the existing incremental transformation
# This does not implement transformation logic in the notebook; it calls the installed project function. On the first run, both snapshots should be pending. On a rerun with the same input and output directory, they should already be in the state manifest and should not be processed again.

# CELL ********************

processed_this_call = []

def record_processed_snapshot(path):
    processed_this_call.append(str(path))

silver_paths = incremental_raw_to_silver(
    raw_root=RAW_ROOT,
    silver_root=SILVER_ROOT,
    on_snapshot=record_processed_snapshot,
)

if set(silver_paths) != set(SILVER_TABLES):
    raise AssertionError(
        f"Returned Silver tables differ from expected: {set(silver_paths)}"
    )

print(f"PASS | incremental_raw_to_silver returned {len(silver_paths)} Silver paths")
print(f"Snapshots processed during this call: {len(processed_this_call)}")
for name in SILVER_TABLES:
    print(f"  {name}: {silver_paths[name]}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Intermediate testing

# CELL ********************

from pathlib import Path
import pyarrow.parquet as pq

SILVER_ROOT = Path("/lakehouse/default/Files/silver/_raw_to_silver_test")

expected_tables = [
    "vehicle_types",
    "station_information",
    "station_status",
    "station_status_vehicle_types",
    "free_bike_status",
    "system_pricing_plans",
    "system_pricing_plan_tiers",
    "system_regions",
]

for table_name in expected_tables:
    path = SILVER_ROOT / f"{table_name}.parquet"

    if not path.exists():
        raise FileNotFoundError(f"Missing Silver table: {path}")

    table = pq.ParquetFile(path).read()

    print(f"\n--- {table_name} ---")
    print(f"Rows: {table.num_rows}")
    print(f"Columns: {table.num_columns}")
    print(f"Schema:\n{table.schema}")

print("\nPASS | All 8 Silver tables exist and are readable.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 4 — Validate Silver Parquet outputs
# The synthetic input from the preceding Raw store test has two station-status observations for fabric-compat-station-001, with four available bikes and eight available docks. It did not include vehicle_types_available, so the child availability table should be empty.

# CELL ********************

silver_rows = {}

for table_name in SILVER_TABLES:
    path = silver_paths[table_name]

    if not path.is_file():
        raise AssertionError(f"Silver output is missing: {path}")

    table = pq.ParquetFile(path).read()

    if table.schema != TABLE_SCHEMAS[table_name]:
        raise AssertionError(
            f"Schema mismatch for {table_name}.\n"
            f"Expected: {TABLE_SCHEMAS[table_name]}\n"
            f"Actual:   {table.schema}"
        )

    silver_rows[table_name] = table.to_pylist()
    print(
        f"PASS | {table_name}: exists, schema matches, "
        f"{table.num_rows} row(s)"
    )

status_rows = silver_rows["station_status"]

if len(status_rows) != 2:
    raise AssertionError(f"Expected 2 station_status rows; found {len(status_rows)}")

expected_observed_at = {
    row["observed_at"] for row in raw_rows
}
actual_observed_at = {
    row["observed_at"].replace(tzinfo=__import__("datetime").UTC).isoformat()
    for row in status_rows
}
if actual_observed_at != expected_observed_at:
    raise AssertionError(
        f"Silver observed_at values differ from Raw.\n"
        f"Expected: {expected_observed_at}\n"
        f"Actual:   {actual_observed_at}"
    )

for row in status_rows:
    if row["station_id"] != "fabric-compat-station-001":
        raise AssertionError(f"Unexpected station_id: {row['station_id']!r}")
    if row["num_bikes_available"] != 4:
        raise AssertionError(f"Unexpected bike count: {row['num_bikes_available']!r}")
    if row["num_docks_available"] != 8:
        raise AssertionError(f"Unexpected dock count: {row['num_docks_available']!r}")
    if row["is_installed"] is not True:
        raise AssertionError(f"Unexpected is_installed value: {row['is_installed']!r}")
    if row["is_renting"] is not True:
        raise AssertionError(f"Unexpected is_renting value: {row['is_renting']!r}")
    if row["is_returning"] is not True:
        raise AssertionError(f"Unexpected is_returning value: {row['is_returning']!r}")

if silver_rows["station_status_vehicle_types"]:
    raise AssertionError(
        "Expected no vehicle-type child rows for the synthetic input, but found some"
    )

print("PASS | Two station-status rows contain the expected synthetic values and timestamps")
print("PASS | station_status_vehicle_types is empty as expected for this input")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 5 — Validate the incremental state manifest

# CELL ********************

if not STATE_PATH.is_file():
    raise AssertionError(f"Incremental state manifest is missing: {STATE_PATH}")

state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
manifest = state.get("raw_snapshots")

if not isinstance(manifest, dict):
    raise AssertionError("Manifest is missing the raw_snapshots object")

if set(manifest) != identities:
    raise AssertionError(
        f"Manifest identities differ from the two input snapshots.\n"
        f"Expected: {sorted(identities)}\n"
        f"Actual:   {sorted(manifest)}"
    )

for identity, metadata in manifest.items():
    if metadata.get("status") != "silver_complete":
        raise AssertionError(
            f"Unexpected status for {identity}: {metadata.get('status')!r}"
        )
    if len(metadata.get("payload_hash", "")) != 64:
        raise AssertionError(f"Missing or invalid SHA-256 hash for {identity}")
    if not metadata.get("source_url"):
        raise AssertionError(f"Missing source_url for {identity}")

print(f"PASS | Manifest contains both snapshot identities: {sorted(manifest)}")
print("PASS | Each entry has a SHA-256 payload hash, source URL, and silver_complete status")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 6 — Rerun and verify idempotency
# 
# This calls the same existing function again, without clearing the isolated output. No snapshots should be sent to the callback, and Silver rows and manifest should remain unchanged.

# CELL ********************

rows_before_rerun = {
    name: pq.ParquetFile(silver_paths[name]).read().to_pylist()
    for name in SILVER_TABLES
}
state_before_rerun = STATE_PATH.read_bytes()

processed_on_rerun = []

def record_rerun_processed_snapshot(path):
    processed_on_rerun.append(str(path))

rerun_paths = incremental_raw_to_silver(
    raw_root=RAW_ROOT,
    silver_root=SILVER_ROOT,
    on_snapshot=record_rerun_processed_snapshot,
)

if processed_on_rerun:
    raise AssertionError(
        f"Expected no pending snapshots on rerun; callback received {processed_on_rerun}"
    )

if STATE_PATH.read_bytes() != state_before_rerun:
    raise AssertionError("Manifest changed during a no-op rerun")

for name in SILVER_TABLES:
    rows_after_rerun = pq.ParquetFile(rerun_paths[name]).read().to_pylist()
    if rows_after_rerun != rows_before_rerun[name]:
        raise AssertionError(f"Silver table changed during rerun: {name}")

print("PASS | Rerun processed no snapshots")
print("PASS | Manifest and all Silver table rows remained unchanged")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 7 — Configure historical Silver input

# CELL ********************

from pathlib import Path
import pyarrow.parquet as pq

SILVER_GOLD_TEST_ROOT = Path(
    "/lakehouse/default/Files/silver/_gold_test_input"
)

GOLD_TEST_ROOT = Path(
    "/lakehouse/default/Files/_gold_test/gold_output"
)

expected_tables = [
    "vehicle_types",
    "station_information",
    "station_status",
    "station_status_vehicle_types",
    "free_bike_status",
    "system_pricing_plans",
    "system_pricing_plan_tiers",
    "system_regions",
]

print(f"Silver input: {SILVER_GOLD_TEST_ROOT}")
print(f"Gold output:  {GOLD_TEST_ROOT}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 8 — Validate historical Silver files

# CELL ********************

historical_silver_tables = {}

for table_name in expected_tables:
    path = SILVER_GOLD_TEST_ROOT / f"{table_name}.parquet"

    if not path.is_file():
        raise FileNotFoundError(f"Missing Silver input: {path}")

    table = pq.ParquetFile(path).read()

    expected_schema = TABLE_SCHEMAS[table_name]

    if table.schema != expected_schema:
        raise AssertionError(
            f"Schema mismatch for {table_name}.\n"
            f"Expected: {expected_schema}\n"
            f"Actual:   {table.schema}"
        )

    historical_silver_tables[table_name] = table

    print(
        f"PASS | {table_name}: "
        f"{table.num_rows:,} rows, "
        f"{table.num_columns} columns"
    )

print("\nPASS | All 8 historical Silver tables match expected schemas.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 9

# CELL ********************

import pyarrow.compute as pc

key_columns = {
    "vehicle_types": ["vehicle_type_id"],
    "station_information": ["station_id"],
    "station_status": ["station_id"],
    "station_status_vehicle_types": ["station_id", "vehicle_type_id"],
    "free_bike_status": ["bike_id", "vehicle_type_id", "station_id", "pricing_plan_id"],
    "system_pricing_plans": ["plan_id"],
    "system_pricing_plan_tiers": ["plan_id", "tier_index"],
    "system_regions": ["region_id"],
}

for table_name, table in historical_silver_tables.items():
    print(f"\n--- {table_name} ---")
    print(f"Rows: {table.num_rows:,}")

    if "observed_at" in table.column_names and table.num_rows > 0:
        time_stats = pc.min_max(table["observed_at"]).as_py()
        distinct_times = pc.count_distinct(table["observed_at"]).as_py()

        print(f"observed_at range: {time_stats['min']} -> {time_stats['max']}")
        print(f"Distinct timestamps: {distinct_times:,}")

    for column_name in key_columns[table_name]:
        column = table[column_name]
        print(
            f"{column_name}: "
            f"nulls={column.null_count:,}"
        )

print("\nPASS | Silver data diagnostics completed.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Cell 10

# CELL ********************

from bike_data.incremental import incremental_silver_to_gold


# Ensure the parent directory exists.
GOLD_TEST_ROOT.parent.mkdir(parents=True, exist_ok=True)

# Protect against accidental overwriting of previous test results.
if GOLD_TEST_ROOT.exists():
    raise FileExistsError(
        f"Gold test output already exists: {GOLD_TEST_ROOT}. "
        "Inspect or clean this isolated test directory before rerunning."
    )

print("Starting historical Silver -> Gold transformation...")

gold_paths = incremental_silver_to_gold(
    silver_root=SILVER_GOLD_TEST_ROOT,
    gold_root=GOLD_TEST_ROOT,
)

print("\nGold transformation completed.")
print(f"Generated tables: {len(gold_paths)}")

for table_name, path in gold_paths.items():
    print(f"  {table_name}: {path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import pyarrow.parquet as pq

expected_gold_tables = [
    "dim_date",
    "dim_station",
    "dim_vehicle_type",
    "dim_region",
    "dim_pricing_plan",
    "dim_pricing_plan_tier",
    "fact_station_availability",
    "fact_station_vehicle_type_availability",
    "fact_free_bike_snapshot",
    "gold_system_availability",
]

if set(gold_paths.keys()) != set(expected_gold_tables):
    raise AssertionError(
        f"Unexpected Gold tables: {sorted(gold_paths.keys())}"
    )

gold_tables = {}

total_rows = 0
total_size_bytes = 0

for table_name in expected_gold_tables:
    path = gold_paths[table_name]

    if not path.is_file():
        raise FileNotFoundError(f"Missing Gold output: {path}")

    table = pq.ParquetFile(path).read()

    file_size = path.stat().st_size

    gold_tables[table_name] = table
    total_rows += table.num_rows
    total_size_bytes += file_size

    print(f"\n--- {table_name} ---")
    print(f"Rows: {table.num_rows:,}")
    print(f"Columns: {table.num_columns}")
    print(f"File size: {file_size / (1024**2):.2f} MB")

    if "observed_at" in table.column_names and table.num_rows > 0:
        time_stats = pc.min_max(table["observed_at"]).as_py()
        print(
            f"observed_at: {time_stats['min']} -> "
            f"{time_stats['max']}"
        )

print("\n" + "=" * 50)
print("GOLD INVENTORY SUMMARY")
print(f"Tables: {len(gold_tables)}")
print(f"Total rows: {total_rows:,}")
print(f"Total Parquet size: {total_size_bytes / (1024**2):.2f} MB")
print("\nPASS | All 10 Gold outputs exist and are readable.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

gold_grains = {
    "dim_date": ["date_key"],
    "dim_station": ["station_id", "observed_at"],
    "dim_vehicle_type": ["vehicle_type_id", "observed_at"],
    "dim_region": ["region_id", "observed_at"],
    "dim_pricing_plan": ["plan_id", "observed_at"],
    "dim_pricing_plan_tier": [
        "plan_id", "tier_index", "observed_at"
    ],
    "fact_station_availability": [
        "station_id", "observed_at"
    ],
    "fact_station_vehicle_type_availability": [
        "station_id", "vehicle_type_id", "observed_at"
    ],
    "fact_free_bike_snapshot": [
        "bike_id", "observed_at"
    ],
    "gold_system_availability": ["observed_at"],
}

for table_name, grain_columns in gold_grains.items():
    table = gold_tables[table_name]

    grouped = table.group_by(grain_columns).aggregate(
        [(grain_columns[0], "count")]
    )

    duplicate_rows = table.num_rows - grouped.num_rows

    status = "PASS" if duplicate_rows == 0 else "FAIL"

    print(
        f"{status} | {table_name}: "
        f"{grouped.num_rows:,} unique keys, "
        f"{duplicate_rows:,} duplicate rows"
    )

    if duplicate_rows > 0:
        raise AssertionError(
            f"Duplicate grain detected in {table_name}"
        )

print("\nPASS | All Gold tables have unique declared grains.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import pyarrow as pa
import pyarrow.compute as pc

def distinct_values(table, column):
    return set(
        pc.unique(table[column].combine_chunks()).to_pylist()
    )

def check_reference(
    fact_name,
    fact_column,
    dimension_name,
    dimension_column,
):
    fact_values = distinct_values(
        gold_tables[fact_name], fact_column
    )
    dimension_values = distinct_values(
        gold_tables[dimension_name], dimension_column
    )

    # Null values are not valid dimension references.
    null_count = gold_tables[fact_name][fact_column].null_count

    missing = fact_values - dimension_values - {None}

    status = "PASS" if not missing and null_count == 0 else "FAIL"

    print(
        f"{status} | {fact_name}.{fact_column} -> "
        f"{dimension_name}.{dimension_column} | "
        f"missing={len(missing):,}, nulls={null_count:,}"
    )

    if missing or null_count:
        print(f"  Sample missing keys: {list(missing)[:10]}")
        raise AssertionError(
            f"Referential integrity failure: {fact_name}.{fact_column}"
        )

checks = [
    (
        "fact_station_availability", "station_id",
        "dim_station", "station_id"
    ),
    (
        "fact_station_availability", "region_id",
        "dim_region", "region_id"
    ),
    (
        "fact_station_vehicle_type_availability", "station_id",
        "dim_station", "station_id"
    ),
    (
        "fact_station_vehicle_type_availability", "vehicle_type_id",
        "dim_vehicle_type", "vehicle_type_id"
    ),
    (
        "fact_free_bike_snapshot", "vehicle_type_id",
        "dim_vehicle_type", "vehicle_type_id"
    ),
    (
        "fact_free_bike_snapshot", "pricing_plan_id",
        "dim_pricing_plan", "plan_id"
    ),
]

for check in checks:
    check_reference(*check)

date_checks = [
    ("fact_station_availability", "date_key"),
    ("fact_station_vehicle_type_availability", "date_key"),
    ("fact_free_bike_snapshot", "date_key"),
    ("gold_system_availability", "date_key"),
]

date_keys = distinct_values(gold_tables["dim_date"], "date_key")

for table_name, column_name in date_checks:
    values = distinct_values(gold_tables[table_name], column_name)
    missing = values - date_keys - {None}
    null_count = gold_tables[table_name][column_name].null_count

    status = "PASS" if not missing and null_count == 0 else "FAIL"

    print(
        f"{status} | {table_name}.{column_name} -> "
        f"dim_date.date_key | missing={len(missing):,}, "
        f"nulls={null_count:,}"
    )

    if missing or null_count:
        raise AssertionError(
            f"Date reference failure: {table_name}"
        )

print("\nPASS | All tested Gold references are valid.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

row_count_mapping = {
    "station_information": "dim_station",
    "vehicle_types": "dim_vehicle_type",
    "system_regions": "dim_region",
    "system_pricing_plans": "dim_pricing_plan",
    "system_pricing_plan_tiers": "dim_pricing_plan_tier",
    "station_status": "fact_station_availability",
    "station_status_vehicle_types": "fact_station_vehicle_type_availability",
    "free_bike_status": "fact_free_bike_snapshot",
}

for silver_name, gold_name in row_count_mapping.items():
    silver_rows = historical_silver_tables[silver_name].num_rows
    gold_rows = gold_tables[gold_name].num_rows

    status = "PASS" if silver_rows == gold_rows else "FAIL"

    print(
        f"{status} | {silver_name} -> {gold_name} | "
        f"Silver: {silver_rows:,}, Gold: {gold_rows:,}"
    )

    if silver_rows != gold_rows:
        raise AssertionError(
            f"Row count mismatch: {silver_name} -> {gold_name}"
        )

# System availability should have one record per observation timestamp.
system_rows = gold_tables["gold_system_availability"].num_rows
station_status_times = pc.count_distinct(
    historical_silver_tables["station_status"]["observed_at"]
).as_py()

assert system_rows == station_status_times

print(
    f"PASS | gold_system_availability: "
    f"{system_rows:,} rows for {station_status_times:,} timestamps"
)

print("\nPASS | Silver-to-Gold row preservation checks completed.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

station_times = set(
    pc.unique(
        historical_silver_tables["station_status"]["observed_at"]
    ).to_pylist()
)

vehicle_times = set(
    pc.unique(
        historical_silver_tables["station_status_vehicle_types"]["observed_at"]
    ).to_pylist()
)

only_station = station_times - vehicle_times
only_vehicle = vehicle_times - station_times

print(f"Station status timestamps: {len(station_times):,}")
print(f"Vehicle type timestamps:  {len(vehicle_times):,}")

print(f"Only in station_status: {len(only_station):,}")
print(f"Only in station_status_vehicle_types: {len(only_vehicle):,}")

if only_station:
    print("Sample only_station:", sorted(only_station)[:5])

if only_vehicle:
    print("Sample only_vehicle:", sorted(only_vehicle)[:5])

print(
    "\n"
    + (
        "PASS | All timestamps match exactly."
        if not only_station and not only_vehicle
        else "WARNING | Timestamp mismatches detected."
    )
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
