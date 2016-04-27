# Locally Weighted Linear Regression with SparkSQL on Hadoop HDFS
When working with HIVE we liked the universality of HQL, which allowed us familiar querying with different clauses, but we didn't like the fact that we had to take infrastructural care of the intermediate steps during LWR computation. To solve that issue we now turn to Spark SQL. To quote their web site:
> Seamlessly mix SQL queries with Spark programs. Spark SQL lets you query structured data inside Spark programs, using either SQL or a familiar DataFrame API. Usable in Java, Scala, Python and R.

> DataFrames and SQL provide a common way to access a variety of data sources, including Hive, Avro, Parquet, ORC, JSON, and JDBC. You can even join data across these sources.
> Spark SQL reuses the Hive frontend and metastore, giving you full compatibility with existing Hive data, queries, and UDFs. Simply install it alongside Hive.

*Thus we can use Spark SQL framework to use and **query either plain files on HDFS or Hive warehouse** using familiar DataFrame API, and **do it in Python***.

Working with HIVE is rather straightforward, but requires to build Spark with related flags (Hive support leads to increase in the number of external dependencies). Thus let's test yet another feature of SparkSQL: inferring JSON format by reflection and automatic conversion of JSON to an SQL-like table. Then we can query that table and calculate LWR. That sounds like a  reasonable idea - suppose we receive data from our business client in JSON format every night.

As usual, all the following commands are issued from the *sparksql* working directory on the virtual machine under root privileges:
```shell
$ sudo su               # password: bigdata
$ cd /nosql/sparksql/   
```

First, let's generate some JSON data. Just feed data_x.txt to our conversion script:
```shell
$ cat /nosql/input/* | /nosql/sparksql/csv-to-json.py
```

Now put generated JSON into HDFS:
```shell
$ hdfs dfs -put /nosql/sparksql/data_x.json /user/root/
```

We can now register that file as if a table to query as we like:
```shell
$ pyspark
lwr_data = sqlContext.read.json('/user/root/data_x.json')
lwr_data.registerTempTable('lwr_data')

sqlContext.sql('SELECT * FROM lwr_data WHERE x1 > 4 AND x2 < -3 LIMIT 3').show()
+------+-------+-------+-------+
|    x0|     x1|     x2|     x3|
+------+-------+-------+-------+
|3.4566| 9.5228|-4.0112|-3.5944|
|4.3684| 9.6718|-3.9606|-3.1625|
|5.2423|11.0272| -4.353|-4.1013|
+------+-------+-------+-------+
```
Thus we get the same functionality as with HIVE yet we don't have to describe the structure - it is inferred automatically! Better yet, the result of any query is, in fact, RDD, which supports all the normal RDD operations. Thus we can seamlessly combine the syntax of the two:

```shell
df = sqlContext.sql('SELECT * FROM lwr_data WHERE x1 > 4 AND x2 < -3')
df.count()
# 528

# Try arbitrary map and reduce over our DataFrame obtained from temp table over JSON:
df.map(lambda row: abs(row.x1 + row.x2 - row.x3)).reduce(lambda a, b: a + b)
# 4646.904679999999
```

This is very elegant and powerful. Also note that we can use up-down keystokes to repeat recent operations (which you can't do in HIVE).

Implementation of our LWR is rather straightforward - all we need to do is to adjust our MapAB function to work with rows rather than the string line. Below is simplified code (full code available at [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)):
```python
sc = SparkContext('local', 'spark sql app')
sqlContext = SQLContext(sc)

data = sqlContext.read.json('/user/root/data_x.json')
data.registerTempTable('lwr_data')

def mapAB(line):
    def gauss_kernel(x_to, c):...

    # parse values from the row assuming x1 x2 x3 ... y
    n = len(row)
    x = np.matrix([1.0] + [row['x%s' % i] for i in xrange(n - 1)])
    y = np.matrix([row['x%s' % (n - 1)]])

    weight = gauss_kernel(x, c=C)
    return [('a', np.multiply(x.T * x, weight)),
            ('b', np.multiply(x.T * y, weight))]

# Run LWR
ab = data.flatMap(mapAb)  # transformation, maps input into list of tuples (K, V)
         .reduceByKey(lambda total, mat: total + mat)   # transformation, sorts and reduces the list
         .collect()  # action, forces execution of all *lazy* transformations

a = ab[0][1]  # first element of the list, second element in the tuple
b = ab[1][1]  # second element of the list, second element in the tuple

theta = a.I * b  # we found our LWR hypothesis!

# Save result into HDFS
sc.parallelize(theta).saveAsTextFile('/user/root/sparksql_output')
```
To execute the full script:
```shell
spark-submit --master local[4] /nosql/sparksql/lwr_sparksql.py
```

Check the correctness of the hypothesis produced by SparkSQL:
```shell
$ hdfs dfs -cat /user/root/sparksql_output/*
# [[ 26.88083126]]
# [[-0.57996902]]
# [[-3.96718554]]
# [[-0.40413609]]
```

##### SparkSQL Summary
While JSON reflection is super useful it doesn't appear to be robust yet (I failed to parse my Google takeout data). In spite of that, SparkSQL proven to be an extremely nice and easy to use tool. While calculating LWR in SQL worlds appears to be a bad idea (since the whole point of SQL is to allow to run 'mainstream' queries on data, while LWR requires us to write a custom script) SparkSQL allows us to soften the edge here by fusing the SQL like functionality with robust RDD features and convenient DataFrame API.
