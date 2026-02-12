import os
import sys
import time
import urllib.request
import gc  # Garbage Collector
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

TAXI = "green"  # O "yellow"
YEARS = [2019, 2020]
MONTHS = [f"{i:02d}" for i in range(1, 13)]
DOWNLOAD_DIR = "./data"

# REDUCIDO A 2 PARA EVITAR OUT OF MEMORY EN 2019
MAX_WORKERS = 2 
CHUNK_SIZE = 8 * 1024 * 1024
MAX_RETRIES = 3

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


# =========================
# CANONICAL SCHEMAS
# =========================
YELLOW_SCHEMA = pa.schema([
    ("VendorID", pa.int64()),
    ("tpep_pickup_datetime", pa.timestamp("us")),
    ("tpep_dropoff_datetime", pa.timestamp("us")),
    ("passenger_count", pa.int64()),
    ("trip_distance", pa.float64()),
    ("RatecodeID", pa.int64()),
    ("store_and_fwd_flag", pa.string()),
    ("PULocationID", pa.int64()),
    ("DOLocationID", pa.int64()),
    ("payment_type", pa.int64()),
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
    ("VendorID", pa.int64()),
    ("lpep_pickup_datetime", pa.timestamp("us")),
    ("lpep_dropoff_datetime", pa.timestamp("us")),
    ("store_and_fwd_flag", pa.string()),
    ("RatecodeID", pa.int64()),
    ("PULocationID", pa.int64()),
    ("DOLocationID", pa.int64()),
    ("passenger_count", pa.int64()),
    ("trip_distance", pa.float64()),
    ("fare_amount", pa.float64()),
    ("extra", pa.float64()),
    ("mta_tax", pa.float64()),
    ("tip_amount", pa.float64()),
    ("tolls_amount", pa.float64()),
    ("ehail_fee", pa.float64()),
    ("improvement_surcharge", pa.float64()),
    ("total_amount", pa.float64()),
    ("payment_type", pa.int64()),
    ("trip_type", pa.int64()),
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
        print(f"Bucket '{bucket_name}' encontrado.")
        return bucket
    except NotFound:
        bucket = client.create_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' creado.")
        return bucket
    except Exception as e:
        print(f"Error con el bucket: {e}")
        sys.exit(1)


def _safe_cast_array(arr, target_type: pa.DataType) -> pa.Array:
    """Intenta castear de varias formas para manejar incompatibilidades."""
    try:
        # Intento 1: Directo
        return pc.cast(arr, target_type, safe=False)
    except Exception:
        try:
            # Intento 2: Si es un numero 'float' que queremos como 'int' pero tiene nulos
            # Pyarrow a veces falla convirtiendo nulos float -> nulos int.
            # Convertimos a string primero suele limpiar formatos raros.
            s_arr = pc.cast(arr, pa.string())
            return pc.cast(s_arr, target_type, safe=False)
        except Exception:
            # Intento 3: Devuelve nulos si todo falla
            return pa.array([None] * len(arr), type=target_type)


def normalize_parquet_inplace(file_path: str, schema: pa.Schema) -> None:
    """
    Lee el archivo por batches (lotes) para ahorrar memoria RAM.
    Normaliza cada lote y lo escribe en un archivo temporal.
    """
    temp_file = file_path + ".tmp"
    
    try:
        # Leemos el archivo Parquet original
        parquet_file = pq.ParquetFile(file_path)
        
        # Preparamos el escritor con el esquema CORRECTO
        with pq.ParquetWriter(temp_file, schema, compression="snappy") as writer:
            
            # Iteramos por lotes (batches) de 100,000 filas
            for batch in parquet_file.iter_batches(batch_size=100000):
                batch_arrays = []
                
                for field in schema:
                    # Si la columna existe en el batch original
                    if field.name in batch.schema.names:
                        col_data = batch[field.name]
                        # Casteamos
                        batch_arrays.append(_safe_cast_array(col_data, field.type))
                    else:
                        # Si falta la columna, creamos nulos
                        batch_arrays.append(pa.array([None] * len(batch), type=field.type))
                
                # Creamos el batch normalizado
                normalized_batch = pa.RecordBatch.from_arrays(batch_arrays, schema=schema)
                writer.write_batch(normalized_batch)
        
        # Reemplazamos el archivo original con el normalizado
        os.replace(temp_file, file_path)
        
        # Limpieza de memoria explícita
        gc.collect()

    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise e


def download_file(taxi: str, year: int, month: str, canon_schema: pa.Schema) -> str | None:
    url = f"{BASE_URL}/{taxi}_tripdata_{year}-{month}.parquet"
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{taxi}_tripdata_{year}-{month}.parquet")

    # Si ya existe y pesa más de 1MB, lo saltamos (opcional, para reanudar)
    if os.path.exists(file_path) and os.path.getsize(file_path) > 1000000:
         print(f"[SKIP] {year}-{month} ya existe.")
         return file_path

    try:
        print(f"[DL] Descargando {year}-{month}...")
        urllib.request.urlretrieve(url, file_path)

        # Verificar descarga básica
        if os.path.getsize(file_path) < 1000:
            print(f"[ERROR] Archivo {year}-{month} inválido (muy pequeño).")
            os.remove(file_path)
            return None

        # Normalizar
        normalize_parquet_inplace(file_path, canon_schema)
        print(f"[OK] Normalizado {year}-{month}")
        return file_path

    except HTTPError as e:
        print(f"[FAIL HTTP] {year}-{month}: {e}")
        return None
    except Exception as e:
        print(f"[FAIL ERROR] {year}-{month}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return None


def verify_gcs_upload(bucket: storage.Bucket, blob_name: str) -> bool:
    return storage.Blob(bucket=bucket, name=blob_name).exists(client)


def upload_to_gcs(bucket: storage.Bucket, taxi: str, file_path: str, max_retries: int = MAX_RETRIES):
    filename = os.path.basename(file_path)
    # Extracción robusta del año
    try:
        year = filename.split("_tripdata_")[1].split("-")[0]
    except IndexError:
        print(f"[SKIP] Nombre de archivo incorrecto: {filename}")
        return

    blob_name = f"{taxi}/year={year}/{filename}"
    blob = bucket.blob(blob_name)
    blob.chunk_size = CHUNK_SIZE

    # Verificar si ya existe en GCS para no resubir
    if verify_gcs_upload(bucket, blob_name):
        print(f"[SKIP GCS] {blob_name} ya existe en bucket.")
        return

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[UP] Subiendo {filename} -> {blob_name} (Intento {attempt})")
            blob.upload_from_filename(file_path, timeout=300) # Timeout aumentado
            print(f"[OK] Subido: {blob_name}")
            return
        except Exception as e:
            print(f"[RETRY] Error subiendo {blob_name}: {e}")
            time.sleep(5)

    print(f"[FAIL] No se pudo subir {blob_name}")


def main():
    taxi = TAXI.strip().lower()
    if taxi not in ("green", "yellow"):
        raise ValueError("TAXI debe ser 'green' o 'yellow'")

    canon_schema = YELLOW_SCHEMA if taxi == "yellow" else GREEN_SCHEMA
    print(f"==> RUN taxi={taxi}, years={YEARS}")
    
    # 1. Preparar Bucket
    bucket = create_bucket_if_needed(BUCKET_NAME)

    tasks = [(y, m) for y in YEARS for m in MONTHS]
    downloaded_files: list[str] = []

    # 2. Descargar y Normalizar
    print(f"==> Iniciando descargas con {MAX_WORKERS} workers...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(download_file, taxi, y, m, canon_schema) for y, m in tasks]
        for fut in as_completed(futures):
            path = fut.result()
            if path:
                downloaded_files.append(path)

    print(f"==> Descargas finalizadas. Archivos listos: {len(downloaded_files)}")

    # 3. Subir a GCS
    print("==> Iniciando subida a GCS...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(upload_to_gcs, bucket, taxi, fp) for fp in downloaded_files]
        for fut in as_completed(futures):
            fut.result()

    print("DONE.")

    # Opcional: Limpiar archivos locales al final
    # for f in downloaded_files:
    #     os.remove(f)


if __name__ == "__main__":
    main()