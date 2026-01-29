## Question 1. Understanding Docker images

$ docker run -it --entrypoint=bash python:3.13
$ pip -V
pip 25.3 from /usr/local/lib/python3.13/site-packages/pip (python 3.13)

## Question 2. Understanding Docker networking and docker-compose
Docker uses the service or container name as hostname and container port, so both of these could work:
db:5432
postgres:5432

## Question 3. Counting short trips
select count(1) from taxi_trips where lpep_pickup_datetime >='20251101' and lpep_pickup_datetime < '20251201' and trip_distance<=1;
+-------+
| count |
|-------|
| 8007  |
+-------+

## Question 4. Longest trip for each day

select lpep_pickup_datetime::date date, max(trip_distance) from taxi_trips where trip_distance<100 group by lpep_pickup_datetime::date order by 2 desc limit 1;
+------------+-------+
| date       | max   |
|------------+-------|
| 2025-11-14 | 88.03 |
+------------+-------+

## Question 5. Biggest pickup zone
select sum(total_amount) total, b."Zone" FROM taxi_trips a inner join taxi_zone b on a."PULocationID"=b."LocationID" where 
"lpep_pickup_datetime">= '20251118'and "lpep_pickup_datetime" <'20251119' group by b."Zone" order by 1 desc limit 1;
+--------------------+---------------------+
| total              | Zone                |
|--------------------+---------------------|
| 257684.7000000002  | East Harlem North   |
+--------------------+---------------------+

## Question 6. Largest tip
select max(tip_amount) total, dropoff."Zone" FROM taxi_trips a inner join taxi_zone dropoff on a."DOLocationID"=dropoff.LocationID" inner join taxi_zone pickup on pickup."LocationID" = a."PULocationID" where "lpep_pickup_datetime">= '20251101' and "lpep_pickup_datetime" <'20251201' and pickup."Zone"='East Harlem North' group by dropoff."Zone" order by 1 desc limit 1;
+-------+----------------+
| total | Zone           |
|-------+----------------|
| 81.89 | Yorkville West |
+-------+----------------+
