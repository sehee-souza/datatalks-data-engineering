import os
import sys
import time
import urllib.request
import gc
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

from google.cloud import storage
from google.api_core.exceptions import NotFound, Forbidden

# =========================
# CONFIG
# =========================
BUCKET_NAME = "de-zoomcamp26-bucket"
CREDENTIALS_FILE = "./../secrets/de-zoomcamp26-key.json"

TAXI = "yellow"  # Cambiado a yellow según tu petición
YEARS = [2019, 2020]
MONTHS = [f"{i:02d}" for i in range(1, 13)]
DOWNLOAD_DIR = "./data"

MAX_WORKERS = 2 
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 3

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

# =========================
# CANONICAL SCHEMAS (Homogeneizados a FLOAT64)
# =========================
# Forzamos FLOAT64 en IDs y conteos para evitar errores de mismatch en BigQuery
YELLOW_SCHEMA = pa.schema([
    ("VendorID", pa.float64()),
    ("tpep_pickup_datetime", pa.timestamp("us")),
    ("tpep_dropoff_datetime", pa.timestamp("us")),
    ("passenger_count", pa.float64()),
    ("trip_distance", pa.float64()),
    ("RatecodeID", pa.float64()),
    ("store_and_fwd_flag", pa.string()),
    ("PULocationID", pa.float64()),
    ("DOLocationID", pa.float64()),
    ("payment_type", pa.float64()),
    ("fare_amount", pa.float64()),
    ("extra", pa.float64()),
    ("mta_tax", pa.float64()),
    ("tip_amount", pa.float64()),
    ("tolls_amount", pa.float64()),
    ("improvement_surcharge", pa.float64()),
    ("total_amount", pa.float64()),
    ("congestion_surcharge", pa.float64()),
    ("airport_fee", pa.float64()),
])

GREEN_SCHEMA = pa.schema([
    ("VendorID", pa.float64()),
    ("lpep_pickup_datetime", pa.timestamp("us")),
    ("lpep_dropoff_datetime", pa.timestamp("us")),
    ("store_and_fwd_flag", pa.string()),
    ("RatecodeID", pa.float64()),
    ("PULocationID", pa.float64()),
    ("DOLocationID", pa.float64()),
    ("passenger_count", pa.float64()),
    ("trip_distance", pa.float64()),
    ("fare_amount", pa.float64()),
    ("extra", pa.float64()),
    ("mta_tax", pa.float64()),
    ("tip_amount", pa.float64()),
    ("tolls_amount", pa.float64()),
    ("ehail_fee", pa.float64()),
    ("improvement_surcharge", pa.float64()),
    ("total_amount", pa.float64()),
    ("payment_type", pa.float64()),
    ("trip_type", pa.float64()),
    ("congestion_surcharge", pa.float64()),
])

# =========================
# GCS CLIENT
# =========================
try:
    client = storage.Client.from_service_account_json(CREDENTIALS_FILE)
except Exception as e:
    print(f"Error cargando credenciales: {e}")
    sys.exit(1)

def create_bucket_if_needed(bucket_name: str) -> storage.Bucket:
    try:
        bucket = client.get_bucket(bucket_name)
        return bucket
    except NotFound:
        return client.create_bucket(bucket_name)

def _safe_cast_array(arr, target_type: pa.DataType) -> pa.Array:
    try:
        return pc.cast(arr, target_type, safe=False)
    except Exception:
        try:
            # Forzar vía string para limpiar nulos problemáticos
            return pc.cast(pc.cast(arr, pa.string()), target_type, safe=False)
        except Exception:
            return pa.array([None] * len(arr), type=target_type)

def normalize_parquet_inplace(file_path: str, schema: pa.Schema) -> None:
    temp_file = file_path + ".tmp"
    try:
        parquet_file = pq.ParquetFile(file_path)
        with pq.ParquetWriter(temp_file, schema, compression="snappy") as writer:
            for batch in parquet_file.iter_batches(batch_size=100000):
                batch_arrays = []
                for field in schema:
                    if field.name in batch.schema.names:
                        batch_arrays.append(_safe_cast_array(batch[field.name], field.type))
                    else:
                        batch_arrays.append(pa.array([None] * len(batch), type=field.type))
                
                normalized_batch = pa.RecordBatch.from_arrays(batch_arrays, schema=schema)
                writer.write_batch(normalized_batch)
        os.replace(temp_file, file_path)
        gc.collect()
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        raise e

def download_file(taxi: str, year: int, month: str, canon_schema: pa.Schema) -> str | None:
    url = f"{BASE_URL}/{taxi}_tripdata_{year}-{month}.parquet"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{taxi}_tripdata_{year}-{month}.parquet")

    try:
        print(f"[DL] Descargando {year}-{month}...")
        urllib.request.urlretrieve(url, file_path)
        if os.path.getsize(file_path) < 1000:
            os.remove(file_path)
            return None
        normalize_parquet_inplace(file_path, canon_schema)
        return file_path
    except Exception as e:
        print(f"[FAIL] {year}-{month}: {e}")
        if os.path.exists(file_path): os.remove(file_path)
        return None

def upload_to_gcs(bucket: storage.Bucket, taxi: str, file_path: str):
    filename = os.path.basename(file_path)
    year = filename.split("_tripdata_")[1].split("-")[0]
    blob_name = f"{taxi}/year={year}/{filename}"
    blob = bucket.blob(blob_name)
    blob.chunk_size = CHUNK_SIZE

    # NO saltamos la subida para asegurar que los archivos corregidos reemplacen a los viejos
    try:
        print(f"[UP] Subiendo {filename} corregido...")
        blob.upload_from_filename(file_path, timeout=300)
        return True
    except Exception as e:
        print(f"[ERR UP] {filename}: {e}")
        return False

def main():
    taxi = TAXI.strip().lower()
    canon_schema = YELLOW_SCHEMA if taxi == "yellow" else GREEN_SCHEMA
    bucket = create_bucket_if_needed(BUCKET_NAME)

    tasks = [(y, m) for y in YEARS for m in MONTHS]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(download_file, taxi, y, m, canon_schema) for y, m in tasks]
        for fut in as_completed(futures):
            path = fut.result()
            if path: downloaded_files.append(path)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        [ex.submit(upload_to_gcs, bucket, taxi, fp) for fp in downloaded_files]

    print("DONE. Archivos homogeneizados y subidos.")

if __name__ == "__main__":
    main()