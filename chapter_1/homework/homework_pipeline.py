#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import pyarrow
from sqlalchemy import create_engine



def run():


    # Read a sample of the data
    prefix = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/'
    df = pd.read_csv(prefix + 'taxi_zone_lookup.csv', nrows=100)


    # In[4]:



    taxi_data_url = "https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-11.parquet"


    # In[6]:


    taxi = pd.read_parquet(taxi_data_url)



    engine = create_engine("postgresql+psycopg://root:root@pgdatabase:5432/ny_taxi")


    df_iter = pd.read_csv(prefix + "taxi_zone_lookup.csv", chunksize=100000)

    first = True
    for df_chunk in df_iter:
        if first:
            df_chunk.head(0).to_sql(
                name="taxi_zone",
                con=engine,
                if_exists="replace",
                index=False
            )
            first = False
            print("Table taxi_zone created")

        df_chunk.to_sql(
            name="taxi_zone",
            con=engine,
            if_exists="append",
            index=False
        )
        print("Inserted zones:", len(df_chunk))


    # In[18]:


    taxi.head(0).to_sql("taxi_trips", engine, if_exists="replace", index=False)
    print("Table taxi_trips created")
    taxi.to_sql("taxi_trips", engine, if_exists="append", index=False, chunksize=100000)
    print("Inserted taxi_trips:", len(taxi))


   

if __name__=="__main__":
    run()

"""
To build and run container (in the same network as Postgres database w/ docker compose):
Terminal 1:
docker run -it   -e POSTGRES_USER="root"   -e POSTGRES_PASSWORD="root"   -e POSTGRES_DB="ny_taxi"   -v ny_taxi_postgres_data:/var/lib/postgresql   -p 5432:5432   --network=pg-network   --name pgdatabase   postgres:18

Terminal 2:
docker build -t homework:v1 .
docker run --rm --network pg-network homework:v1
"""