### Hadoop Ecosystem Overview
Hadoop consists of two things: a Distributed File System (HDFS) and a Computation  framework (MapReduce). HDFS also provides us fault tolerant storage with high throughput but lacks random read and write access.

Now HBase comes into play to provide read/write capabilities. It's a distributed, scalable, big data store build on blueprints of Google's BigTable. In other words, HBase is a database (not as FS). HBase stores data as key/value pairs, which makes it look like a hashmap, or an index table: if you know the key - you get answer fast.

Hive approaches a problem from the different angle. It provides data warehousing facilities on top of an existing Hadoop cluster. We can create tables in Hive and store data there. Hive also provide HQL, very familiar to SQL in syntax, to query our data in an arbitrary style.

These are the descriptions from the official web sites:

> - HBase™: A scalable, distributed database that supports structured data storage for large tables.
> - Hive™: A data warehouse infrastructure that provides data summarization and ad-hoc querying.

We are interested exactly in this *ad-hoc querying*. For example, we want to run locally weighted regression on some subset of the columns, maybe even restricting rows with some *WHERE* clause. Thus we probably want to choose Hive. To rephrase our choice I'd cite a StackOverflow answer:

> HBase is like a Map. If you know the key, you can instantly get the value. But if you want to know how many integer keys in Hbase are between 1000000 and 2000000 that is not suitable for Hbase alone. If you have data to be aggregated, rolled up, analyzed across rows then consider Hive.

However, the problem with Hive comes when we need a *custom (user defined) queries (UDF)*. In general, the whole point of Hive is to lift from the users the responsibility of writing UDF. Nonetheless, it is possible to write such custom aggregation function but it is rather tedious, and you have to do in Java.

To solve that issue we turn to Spark SQL. To quote their web site:
> Seamlessly mix SQL queries with Spark programs. Spark SQL lets you query structured data inside Spark programs, using either SQL or a familiar DataFrame API. Usable in Java, Scala, Python and R.
> DataFrames and SQL provide a common way to access a variety of data sources, including Hive, Avro, Parquet, ORC, JSON, and JDBC. You can even join data across these sources.
> Spark SQL reuses the Hive frontend and metastore, giving you full compatibility with existing Hive data, queries, and UDFs. Simply install it alongside Hive.

*Thus we can use Spark SQL framework to use and **query our convenient Hive warehouse** using familiar DataFrame API, and **do it in Python***.



### Loading Data into Hive
```shell
$ $HADOOP_HOME/bin/hadoop fs -mkdir       /tmp
$ $HADOOP_HOME/bin/hadoop fs -mkdir       /user/hive/warehouse
$ $HADOOP_HOME/bin/hadoop fs -chmod g+w   /tmp
$ $HADOOP_HOME/bin/hadoop fs -chmod g+w   /user/hive/warehouse
$ hdfs dfs -chmod g+w /user/hive/warehouse  # give privileges to hive's warehouse directory
```

All the following commands are issued from the *hive* working directory on the virtual machine under root privileges:
```shell
$ sudo su           # password: bigdata
$ cd /nosql/hive/   # which has spark installation apache-hive-2.0.0-bin/
```

Hive stores metadata in a RDBMS of choice (derby|mysql|postgres|oracle). Thus we need to remove previous (meta) data store and init a new one (with provided 'derby' engine):
```shell
$ cd apache-hive-2.0.0-bin/
$ rm -Rf metastore_db
$ schematool -initSchema -dbType derby

# (Optional) in case of abnormal exit you will see a bunch of exceptions,
# so you can try simply removing the lock.
$ rm metastore_db/*.lck  
```

Now we can create a table (stored in HDFS) in Hive that will suit our data_x.txt file. Note however, that the default field terminator in Hive is ^A, but our file is ',' delimited. Thus we need to explicitly put statement to use a different field separator:
```shell
$ beeline -u jdbc:hive2://  # connect to Hive

# 0: jdbc:hive2://>
CREATE TABLE lwr_data (x1 DOUBLE, x2 DOUBLE, x3 DOUBLE, x4 DOUBLE) ROW FORMAT DELIMITED FIELDS TERMINATED BY ',';
SHOW TABLES;
# +-----------+--+
# | tab_name  |
# +-----------+--+
# | lwr_data  |
# +-----------+--+
```

Now we can load the data into the table from either local store or from HDFS file. Let us do HDFS. As noted in the documentation:
> Note that loading data from HDFS will result in **moving the file/directory**. As a result, the operation is *almost instantaneous*.

Thus to load, we first need to create a new redundant copies of input files:
```shell
# In a new terminal:
$ hdfs dfs -mkdir /user/hive/input  # make input dir for hive

# copy files from local file system
$ hdfs dfs -put /nosql/hadoop/py_lwr_subgroups_sums/input/* /user/hive/input  
```

And then load them (move and apply schema) into the DBMS (note that we can apply basic filter to select *all the files* in the input directory):
```shell
LOAD DATA INPATH '/user/hive/input/*' INTO TABLE lwr_data;

# Try some SQL-like query
0: jdbc:hive2://> SELECT * FROM lwr_data WHERE x1 > 4 AND x2 < -3 LIMIT 3;
# +--------------+--------------+--------------+--------------+--+
# | lwr_data.x1  | lwr_data.x2  | lwr_data.x3  | lwr_data.x4  |
# +--------------+--------------+--------------+--------------+--+
# | 4.6765       | -3.3895      | 3.4896       | 1.4771       |
# | 4.8906       | -3.3584      | 3.4202       | 1.0905       |
# | 4.3239       | -4.8835      | 3.4356       | -0.5776      |
# +--------------+--------------+--------------+--------------+--+
# 3 rows selected (0.19 seconds)
```
After LOAD command you can confirm that the files are all gone from /user/hive/input directory. We can also confirm that all data rows are stored by running HQL:
```shell
SELECT COUNT(*) from lwr_data;
# ...
# +-------+--+
# |  c0   |
# +-------+--+
# | 6860  |
# +-------+--+
```

Interestingly enough, initially Hive was supposed to run all the selection queries as a MapReduce jobs under the hood. Thus when do *SELECT COUNT(\*)* we see the MapReduce output information, along with the following warning:
> WARNING: Hive-on-MR is deprecated in Hive 2 and may not be available in the future versions. Consider using a different execution engine (i.e. tez, spark) or using Hive 1.X releases.

Which only confirms the validity of our plan to use Spark on top of Hive to run actual queries.

However, for the sake of completeness, let us create a mapper for HQL to serve as a user defined function to produce intermediate results (matricies A and b).

### LWR Mapper as UDF in Hive
First let us create an intermediate table to store the mapper's output:
```shell
CREATE TABLE ab_mat (a STRING, b STRING);
```

Now add the python mapper to the Hive context. Note that it basically the same as a mapper for MapReduce (converts rows into A and b matricies), except it has different delimiter for fields.
```shell
add FILE /nosql/hive/lwr/hive_mapper.py;  # replaces old version
# Added resources: [/nosql/hive/hive_mapper.py]
```

Then, we can query our original data (with any WHERE or other clauses we want), transform it using our mapper, and load into newly create intermediate table:
```shell
INSERT OVERWRITE TABLE ab_mat
  SELECT TRANSFORM (x1, x2, x3, x4)
  USING 'python hive_mapper.py'
  AS (a, b)
  FROM lwr_data;
```

Finally, we can select all A and b matricies and pass them to another mapper (hive_find_theta.py) that will compute hypothesis theta.  
```shell
add FILE /nosql/hive/lwr/hive_find_theta.py;
SELECT
  TRANSFORM (a, b)
  USING 'python hive_find_theta.py'
  as (h1, h2, h3, h4)
FROM ab_mat;
# +--------------+------------------+-----------------+------------------+--+
# |      h1      |        h2        |       h3        |        h4        |
# +--------------+------------------+-----------------+------------------+--+
# | 26.87052487  | -0.579815330225  | -3.96594330195  | -0.403622196259  |
# +--------------+------------------+-----------------+------------------+--+
# 1 row selected (1.32 seconds)
```

Thus we arrived at the same results as when using MapReduce or Spark, but this time using HQL as a tool for processing data stored in Hive warehouse on top of HDFS.

Last thing: quit Hive2 (beeline) correctly to avoid problems with the metastore:
```shell
!quit
```
