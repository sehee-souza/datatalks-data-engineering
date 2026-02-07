
# Question 1. What is count of records for the 2024 Yellow Taxi Data?
select count(1) from zoomcamp.yellow_taxi;

# Question 2. What is the estimated amount of data that will be read when this query is executed on the External Table and the Table?
select count(distinct PULocationID) from zoomcamp.yellow_taxi;
select count(distinct PULocationID) from zoomcamp.yellow_taxi_ext;

# Question 3. Why are the estimated number of Bytes different?
select PULocationID from zoomcamp.yellow_taxi;
select PULocationID, DOLocationID  from zoomcamp.yellow_taxi;

# Question 4. How many records have a fare_amount of 0?
select count(1) from zoomcamp.yellow_taxi where fare_amount=0;

# Question 5. What is the best strategy to make an optimized table in Big Query if your query will always filter based on tpep_dropoff_datetime and order the results by VendorID (Create a new table with this strategy)
CREATE OR REPLACE TABLE `kestra-sandbox-486113.zoomcamp.yellow_taxi_part`
PARTITION BY DATE(tpep_dropoff_datetime)
CLUSTER BY VendorID AS (
  SELECT * FROM zoomcamp.yellow_taxi_ext
);

# Question 6. Write a query to retrieve the distinct VendorIDs between tpep_dropoff_datetime 2024-03-01 and 2024-03-15 (inclusive). Use the materialized table you created earlier in your from clause and note the estimated bytes. Now change the table in the from clause to the partitioned table you created for question 5 and note the estimated bytes processed. What are these values? 
select distinct VendorID from zoomcamp.yellow_taxi where date(tpep_dropoff_datetime) between '2024-03-01' and '2024-03-15';

select distinct VendorID from zoomcamp.yellow_taxi_part where date(tpep_dropoff_datetime) between '2024-03-01' and '2024-03-15';

# Question 9. Write a `SELECT count(*)` query FROM the materialized table you created. How many bytes does it estimate will be read? Why?
select count(*) from zoomcamp.yellow_taxi_part;

