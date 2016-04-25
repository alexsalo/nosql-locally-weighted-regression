# Locally Weighted Linear Regression with Spark API on Hadoop HDFS
Spark revolves around the concept of a resilient distributed dataset (RDD), which is a fault-tolerant collection of elements that can be operated on in parallel. Once created, the RDD can be operated on in parallel.

For this tutorial we need HDFS to be already set and running; HDFS should contain /user/root/input folder with data files. Please refer to the README in /nosql/hadoop folder on how to set it up.
TODO maybe copy redundunt info?

All the following commands are issued from the *spark* working directory on the virtual machine under root privileges:
```shell
$ sudo su           # password: bigdata
$ cd /nosql/spark/  # which has spark installation spark-1.6.1-bin-without-hadoop/
```

We downloaded a version of Spark without Hadoop. That means we have to provide our own Hadoop version. To do that make sure (edit) *spark-env* file (save as without template at the end):
```shell
$ gedit conf/spark-env.sh.template
# Make sure JAVA_HOME is set
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64

# With explicit path to 'hadoop' binary
export SPARK_DIST_CLASSPATH=$(/nosql/hadoop/hadoop-2.7.2/bin/hadoop classpath)
```

Then start Spark cluster:
```shell
$ spark-1.6.1-bin-without-hadoop/sbin/start-all.sh
```

Now, once Hadoop environment is set, when using Spark shell we need explicitly specify local files. However, the benefit is that we can access the HDFS files directly via Spark API:
```shell
# Open Local File in FS
$ localFile = sc.textFile("file:///nosql/spark/spark-1.6.1-bin-without-hadoop/README.md")
$ localFile.count()
# 89

# Open file in HDFS:
$ hdfsFile = sc.textFile("/user/root/input/x_data.txt")
$ hdfsFile.count()
# 1372
```

The key difference of Spark from MapReduce is that it provides an consolidated API in Java, Scala or Python. From the ![Spark Programming Guide](http://spark.apache.org/docs/latest/programming-guide.html)
> For example, map is a transformation that passes each dataset element through a function and returns a new RDD representing the results. On the other hand, reduce is an action that aggregates all the elements of the RDD using some function and returns the final result to the driver program.

That means we still use the same idea of mapper and reducer here. However the benefit is, to quote the official site again:
> All transformations in Spark are lazy, in that they do not compute their results right away. Instead, they just remember the transformations applied to some base dataset (e.g. a file). The transformations are only computed when an action requires a result to be returned to the driver program. This design enables Spark to run more efficiently – for example, we can realize that *a dataset created through map will be used in a reduce and return only the result of the reduce to the driver, rather than the larger mapped dataset* (Italics are mine).

To run our script:
```shell
spark-submit --master local[4] py_lwr/spark_lwr.py
```

Another benefit is in that **native support** of python. In MapReduce we had to communicate our partial matricies via standard input/output by converting and parsing np.maprix class into the string. Here in Spark we don't have to do that anymore: we simply pass np.maprix class from one RDD to another.

### Check the correctness
```shell
$ cd /nosql/hadoop/  # to access HDFS

# Show hypothesis produced by Hadoop MapReduce
$ hadoop-2.7.2/bin/hdfs dfs -cat /user/root/output/* | /nosql/hadoop/py_lwr_subgroups_sums/find_theta.py
# [[ 26.89715476]
#  [ -0.57990451]
#  [ -3.96889352]
#  [ -0.40332286]]

# Show hypothesis produced by Spark
$ hadoop-2.7.2/bin/hdfs dfs -cat /user/root/spark_output/*
# [[ 26.88083126]]
# [[-0.57996902]]
# [[-3.96718554]]
# [[-0.40413609]]
```
Thus we obtained the same results. Note, however, that in Spark we pass mapper and reducer as a function (or lambda expression) within single python script and thus able to find hypothesis theta right away, while in MapReduce we have to read the output of the reducers and apply our *find_theta* routine.

### Quick summary
Spark proven to be more flexible tool for executing functions on the distributed data. By handling the intermediate data management Spark is able to take advantage of various optimization techniques (lazy transformations, early projections etc), as well as to provide a more user friendly consolidated interface for programming in the language of choice.
