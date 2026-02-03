#!/usr/bin/env python
# coding: utf-8

# In[2]:


import pandas as pd
import pyarrow
from sqlalchemy import create_engine


# In[3]:


# Read a sample of the data
prefix = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/'
df = pd.read_csv(prefix + 'taxi_zone_lookup.csv', nrows=100)


# In[4]:


df.head()


# In[5]:


taxi_data_url = "https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-11.parquet"


# In[6]:


taxi = pd.read_parquet(taxi_data_url)


# In[7]:


taxi.head()


# In[8]:


df.dtypes


# In[9]:


df.shape


# In[10]:


taxi.dtypes


# In[11]:


taxi.shape


# In[12]:


print(sys.executable)


# In[13]:


from sqlalchemy import create_engine


# In[14]:


engine = create_engine("postgresql+psycopg://root:root@localhost:5432/ny_taxi")


# In[15]:


print(pd.io.sql.get_schema(df, name='taxi_zone', con=engine))


# In[16]:


print(pd.io.sql.get_schema(taxi, name='taxi_trips', con=engine))


# In[17]:


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
    print("Inserted:", len(df_chunk))


# In[18]:


taxi.head(0).to_sql("taxi_trips", engine, if_exists="replace", index=False)
taxi.to_sql("taxi_trips", engine, if_exists="append", index=False, chunksize=100000)

