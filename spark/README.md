# Locally Weighted Linear Regression with Spark on Hadoop HDFS
While MapReduce provides a fine grain way to write our own mappers and reducers for the parallel run, the developer has to make a lot of strategic decisions on how exactly to separate logic load between mapper and reducer executable and how to communicate between them. Additionally, the output of the reducers is a set of <key, value> pairs that have to be evaluated in the separate program. It is neither good or bad, but definitely requires more effort and skill than when the developer uses our next tool - Spark.

Spark revolves around the concept of a resilient distributed dataset (RDD), which is a fault-tolerant collection of elements that can be operated on in parallel. For this tutorial we need HDFS to be already set and running; HDFS should contain /user/root/input folder with data files. Please refer to the README in /nosql/hadoop folder on how to set it up.

All the following commands are issued from the *spark* working directory on the virtual machine under root privileges:
```shell
$ sudo su           # password: bigdata
$ cd /nosql/spark/  # which has spark installation spark-1.6.1-bin-without-hadoop/
```

Then start Spark cluster (then check http://localhost:8080/):
```shell
$ /nosql/spark/spark-1.6.1-bin-without-hadoop/sbin/start-all.sh
```

With Spark, we can access files in both local FS and the HDFS:
```shell
$ pyspark
# Open Local File in FS
localFile = sc.textFile("file:///nosql/input/x_data.txt")
localFile.count()
# 1372

# Open file in HDFS:
hdfsFile = sc.textFile("/user/root/input/*.txt")
hdfsFile.count()
# 5488
```

The major benefit of Spark over plain MapReduce is that it provides an consolidated API in Java, Scala or Python. From the [Spark Programming Guide](http://spark.apache.org/docs/latest/programming-guide.html)
> For example, map is a transformation that passes each dataset element through a function and returns a new RDD representing the results. On the other hand, reduce is an action that aggregates all the elements of the RDD using some function and returns the final result to the driver program.

That means we still use the same idea of mapper and reducer here. However the benefit is, to quote the official site again:
> All transformations in Spark are lazy, in that they do not compute their results right away. Instead, they just remember the transformations applied to some base dataset (e.g. a file). The transformations are only computed when an action requires a result to be returned to the driver program. This design enables Spark to run more efficiently – for example, we can realize that *a dataset created through map will be used in a reduce and return only the result of the reduce to the driver, rather than the larger mapped dataset* (Italics are mine).

So what we have to change in our LWR scripts? Not much. Basically, we simply make a functions out of the mapper and reducer and pass into Spark to run. Below is a simplified implementation (full code available at [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)):

```python
sc = SparkContext('local', 'spark app')
data = sc.textFile('/user/root/input/x_data*.txt')

def mapAB(line):
    def gauss_kernel(x_to, c):...

    # parse values assuming x1 x2 x3 ... y
    values = line.strip().split(',')
    x = np.matrix([1.0] + [float(val) for val in values[:-1]])
    y = np.matrix([float(values[-1])])

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
sc.parallelize(theta).saveAsTextFile('/user/root/spark_output')
```

Note that we didn't even have to write a custom reducer since all it does is it sums the Numpy matricies - easily done with simple lambda expression. To execute the full script:
```shell
spark-submit --master local[4] /nosql/spark/lwr_spark.py
```

Let us check what we've got and compare with the MapReduce output:
```shell
# Show hypothesis produced by Hadoop MapReduce
$ hdfs dfs -cat /user/root/mapreduce_output/* | /nosql/hadoop/lwr_mapreduce_find_theta.py
# [[ 26.89715476]
#  [ -0.57990451]
#  [ -3.96889352]
#  [ -0.40332286]]

# Show hypothesis produced by Spark
$ hdfs dfs -cat /user/root/spark_output/*
# [[ 26.88083126]]
# [[-0.57996902]]
# [[-3.96718554]]
# [[-0.40413609]]
```
Thus we obtained the same results. Note, however, that in Spark we pass mapper and reducer as a function (or lambda expression) within single python script and thus able to find hypothesis theta right away, while in MapReduce we have to read the output of the reducers and apply our *find_theta* routine.

Another benefit (probably more important one) is in **native support** of python in Spark, which means that we can operate over language objects rather than pure strings. In our case, in MapReduce we had to communicate our partial matricies via standard input/output by converting and parsing np.maprix class into the string, which incurred additional time consumed and created a space for to err. In Spark, however, we don't have to do that anymore: we simply pass objects of np.maprix class from one RDD to another, and that is truly advantageous.

##### Spark Summary
Spark proven to be more flexible tool for executing functions on the distributed data. By handling the intermediate data management Spark is able to take advantage of various optimization techniques (lazy transformations, early projections etc), as well as to provide a more user friendly consolidated interface for programming in the language of choice.
