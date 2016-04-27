# Locally Weighted Linear Regression with HIVE on Hadoop HDFS
Recall that HIVE provides data warehousing facilities on top of an existing Hadoop cluster. We can create tables in Hive and store and data there. Hive also provide HQL, very familiar to SQL in syntax, to query our data.

To begin with, we need to create some service directories with privileges in HDFS for Hive to use:
```shell
$ hdfs dfs -mkdir     /tmp
$ hdfs dfs -chmod g+w /tmp
$ hdfs dfs -mkdir     /user/hive
$ hdfs dfs -mkdir     /user/hive/warehouse
$ hdfs dfs -chmod g+w /user/hive/warehouse  # give privileges to hive's warehouse directory
```

As usual, all the following commands are issued from the *hive* working directory on the virtual machine under root privileges:
```shell
$ sudo su           # password: bigdata
$ cd /nosql/hive/   # which has spark installation apache-hive-2.0.0-bin/
```

Hive stores its metadata in a RDBMS of choice (derby|mysql|postgres|oracle). Thus we need to remove previous (meta) data store and init a new one (with provided 'derby' engine):
```shell
$ cd apache-hive-2.0.0-bin/
$ rm -Rf metastore_db
$ schematool -initSchema -dbType derby

# (Optional) in case of abnormal exit (i.e. Ctrl+Z) you will see a bunch of exceptions,
# so you can try simply removing the lock.
$ rm metastore_db/*.lck  
```

Now we can create a table (stored in HDFS) in Hive that will suit our data_x.txt file. Note however, that the default field terminator in Hive is **\\t**, but our file is **','** delimited. Thus we need to explicitly put statement to use a different field separator:
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
$ sudo su
$ hdfs dfs -mkdir /user/hive/input  # make input dir for hive

# copy files from local file system
$ hdfs dfs -put /nosql/input/* /user/hive/input  
```

And then load them (or, rather, move and apply schema) into the DBMS (note that we can apply basic filter to select *all the files* in the input directory):
```shell
LOAD DATA INPATH '/user/hive/input/*' INTO TABLE lwr_data;

# Try some SQL-like query
SELECT * FROM lwr_data WHERE x1 > 4 AND x2 < -3 LIMIT 3;
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
# | 5488  |
# +-------+--+
```
Interestingly enough, initially Hive was supposed to run all the selection queries as a MapReduce jobs under the hood. Thus when do *SELECT COUNT(\*)* we see the MapReduce output information, along with the following warning:
> WARNING: Hive-on-MR is deprecated in Hive 2 and may not be available in the future versions. Consider using a different execution engine (i.e. tez, spark) or using Hive 1.X releases.

Since running on Spark execution engine should not affect out implementation, let us create an HQL user defined function (UDF), which will be analogous to our mapper to produce intermediate results (matricies A and B). First, and this already feels like ad-hoc, we probably need to create an intermediate table to store the mapper's output:
```shell
CREATE TABLE ab_mat (a STRING, b STRING);
```

Now let us take a look at the simplified code of the Hive mapper (full code available at [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)):

```python
def gauss_kernel(x_to, c): ...
def mat2str(mat): ...

for line in sys.stdin:
    # parse values assuming x1 x2 x3 ... y     
    values = line.strip().split('\t')  # (!) change to internal Hive's delimiter
    x = np.matrix([1.0] + [float(val) for val in values[:-1]])
    y = np.matrix([float(values[-1])])

    weight = gauss_kernel(x, c=C)

    a += np.multiply(x.T * x, weight)
    b += np.multiply(x.T * y, weight)

# emit partial resulting martricies A and B into STDOUT
print '%s\t%s' % (mat2str(a), mat2str(b))
```

Note that it basically the same as a mapper for MapReduce (converts rows into A and B matricies), except it has different delimiter for fields.

Now add that python mapper into Hive context:
```shell
add FILE /nosql/hive/lwr_hive_mapper.py;  # replaces old version
# Added resources: [/nosql/hive/hive_mapper.py]
```
Then, we can query our original data (with any WHERE or other clauses we want - but we won't do that so we could compare the results), transform it using our mapper, and load into newly create intermediate table:
```shell
INSERT OVERWRITE TABLE ab_mat
  SELECT TRANSFORM (x1, x2, x3, x4)
  USING 'python lwr_hive_mapper.py'
  AS (a, b)
  FROM lwr_data;
```

Finally, we can select all A and B matricies and pass them to another mapper (lwr_hive_find_theta.py) that will compute hypothesis theta.  
```shell
add FILE /nosql/hive/lwr_hive_find_theta.py;
SELECT
  TRANSFORM (a, b)
  USING 'python lwr_hive_find_theta.py'
  AS (h1, h2, h3, h4)
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

##### Hive Summary
Hive proven to be easy-to-use and SQL-like tool for dealing with distributed data on HDFS. It is probably advantageous when the users are very confident SQL masters but poor programmers. However, for problems like LWR in Hive one needs a *custom (user defined) queries (UDF)*. But in general, since we assume our users are not good programmers, the benefit of Hive become less apparent.

To summarize, HIVE is a good tool with limited applications. On the one hand, we need to design and create tables to store the data, then intermediate tables to fit intermediate results - extra work; on the other hand, we can easily add arbitrary WHERE (or other) clauses when querying such data. We can conclude, that HIVE is indeed a data warehouse - if you care about the data a lot and want to accumulate it in structured manner (yet reaping the benefits of the distributed fault-tolerant HDFS) - HIVE maybe a good choice, but if you want to get a single answer over all the different unstructured data - HIVE would be an overkill.
