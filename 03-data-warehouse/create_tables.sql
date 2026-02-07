
-- Creating external table referring to gcs path
CREATE OR REPLACE EXTERNAL TABLE `kestra-sandbox-486113.zoomcamp.yellow_taxi_ext`
OPTIONS (
  format = 'parquet',
  uris = ['gs://kestra-sandbox-486113-kestra-sandbox/*.parquet']
);

-- Create a non partitioned table from external table
CREATE OR REPLACE TABLE `kestra-sandbox-486113.zoomcamp.yellow_taxi` AS
SELECT * FROM `kestra-sandbox-486113.zoomcamp.yellow_taxi_ext`;


-- For question 5
CREATE OR REPLACE TABLE `kestra-sandbox-486113.zoomcamp.yellow_taxi_part`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS (
  SELECT * FROM zoomcamp.yellow_taxi_ext
);