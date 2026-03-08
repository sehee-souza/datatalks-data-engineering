
-- Green
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.yellow_taxi_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/yellow/year=2019/yellow*.parquet'
    , 'gs://de-zoomcamp26-bucket/yellow/year=2020/yellow*.parquet']
);


CREATE OR REPLACE TABLE `de-zoomcamp26.zoomcamp.green_tripdata`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS (
  SELECT * FROM zoomcamp.green_taxi_ext
);

-- Yellow (2019/2020 have inconsistent data types)
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.yellow_taxi_ext`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://de-zoomcamp26-bucket/yellow/*']
);

CREATE OR REPLACE TABLE `de-zoomcamp26.zoomcamp.yellow_tripdata`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS -- Ahora funcionará porque lo convertiremos abajo
SELECT 
    CAST(VendorID AS INT64) AS VendorID, -- Convertimos de Float a Int aquí
    tpep_pickup_datetime,
    tpep_dropoff_datetime,
    CAST(passenger_count AS INT64) AS passenger_count,
    trip_distance,
    CAST(RatecodeID AS INT64) AS RatecodeID,
    store_and_fwd_flag,
    CAST(PULocationID AS INT64) AS PULocationID,
    CAST(DOLocationID AS INT64) AS DOLocationID,
    CAST(payment_type AS INT64) AS payment_type,
    fare_amount,
    extra,
    mta_tax,
    tip_amount,
    tolls_amount,
    improvement_surcharge,
    total_amount,
    congestion_surcharge,
    airport_fee
FROM `de-zoomcamp26.zoomcamp.yellow_taxi_ext`;