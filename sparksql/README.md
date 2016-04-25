
copy paste problems with hive and why sparksql then

Suppose we receive daily data from our business client in json format, which sounds very reasonable

### Querying Hive from Spark
Also possible to query Hive directly after building Spark with related flags (Hive support leads to increase in the number of external dependencies). Let us, however, test another feature of Spark SQL: inferring JSON format by reflection and automatic conversion of JSON to an SQL-like table. Then we can query that table and calculate LWR.

lwr_data = sqlContext.read.json('file:///nosql/sparksql/data_x.json')
lwr_data.registerTempTable('lwr_data')


sqlContext.sql('SELECT * FROM people WHERE x1 > 4 AND x2 < -3 LIMIT 3').show()
16/04/24 16:14:24 INFO scheduler.TaskSchedulerImpl: Removed TaskSet 12.0, whose tasks have all completed, from pool
+------+-------+-------+-------+
|    x0|     x1|     x2|     x3|
+------+-------+-------+-------+
|3.4566| 9.5228|-4.0112|-3.5944|
|4.3684| 9.6718|-3.9606|-3.1625|
|5.2423|11.0272| -4.353|-4.1013|
+------+-------+-------+-------+


# The results of SQL queries are RDDs and support all the normal RDD operations.
df =sqlContext.sql('SELECT * FROM people WHERE x1 > 4 AND x2 < -3)
ethodAccessorImpl.java:-2, took 0.779797 s
132
>>> df.count()

spark-submit --master local[4] sparksql-lwr.py


While json reflection is super useful it doesn't appear to be robust (I failed to parse my Google takeout data)

# Summary
To summarize, calculatig LWR in SQL worlds appears to be a bad idea. The whole point of SQL is to allow to run 'mainstream' queries on data, while LWR requires us to write a custom script thus we don't really take advantage of SparkSQL, which renders pure Spark a better fit for the problem.
