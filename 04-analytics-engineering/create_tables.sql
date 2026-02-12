
-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.yellow_taxi_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/yellow*.parquet']
);


-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.green_taxi_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/green*.parquet']
);


CREATE OR REPLACE TABLE `kestra-sandbox-486113.zoomcamp.yellow_taxi_part`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS (
  SELECT * FROM zoomcamp.yellow_taxi_ext
);

#############


################# tablas separadas por años por inconsistencia de datos en sus columnas
-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.yellow_taxi19_ext`
OPTIONS (
  format = 'parquet',
  autodetect = TRUE,
  uris = ['gs://de-zoomcamp26-bucket/yellow_tripdata_2019*.parquet']
);

-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.yellow_taxi20_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/yellow_tripdata_2020*.parquet']
);


-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.green_taxi19_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/green_tripdata_2019*.parquet']
);

-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `de-zoomcamp26.zoomcamp.green_taxi20_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://de-zoomcamp26-bucket/green_tripdata_2020*.parquet']
);

################ cosas 
CREATE OR REPLACE TABLE `de-zoomcamp26.zoomcamp.yellow_tripdata` (
  VendorID INT64,
  tpep_pickup_datetime TIMESTAMP,
  tpep_dropoff_datetime TIMESTAMP,
  passenger_count INT64,
  trip_distance FLOAT64,
  RatecodeID INT64,
  store_and_fwd_flag STRING,
  PULocationID INT64,
  DOLocationID INT64,
  payment_type INT64,
  fare_amount FLOAT64,
  extra FLOAT64,
  mta_tax FLOAT64,
  tip_amount FLOAT64,
  tolls_amount FLOAT64,
  improvement_surcharge FLOAT64,
  total_amount FLOAT64,
  congestion_surcharge FLOAT64,
  airport_fee FLOAT64
)
CLUSTER BY VendorID;

LOAD DATA INTO `de-zoomcamp26.zoomcamp.yellow_tripdata`
FROM FILES (
  format = 'PARQUET',
  uris = ['gs://de-zoomcamp26-bucket/yellow_tripdata_2020-*.parquet']
);

CREATE OR REPLACE TABLE `zoomcamp.yellow_tripdata`
CLUSTER BY VendorID AS (
  SELECT * EXCEPT(airport_fee),
  SAFE_CAST(airport_fee AS FLOAT64) AS airport_fee
  FROM `de-zoomcamp26.zoomcamp.yellow_taxi19_ext`
);

insert into `zoomcamp.yellow_tripdata`
SELECT * EXCEPT(airport_fee),
SAFE_CAST(airport_fee AS FLOAT64) AS airport_fee
from `de-zoomcamp26.zoomcamp.yellow_taxi20_ext`;


CREATE OR REPLACE TABLE `zoomcamp.green_tripdata`
CLUSTER BY VendorID AS (
  SELECT * FROM `de-zoomcamp26.zoomcamp.green_taxi_ext`
);



