# Locally Weighted Linear Regression in NoSQL world: MapReduce, Spark, Hive and Spark SQL implementations over Hadoop HDFS.

In this document we provide a brief discussion on the LWR algorithm and somewhat detailed description on how to run our code using each tool on the provided VirtualBox VM (code is available on [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)).

Document structure:

1. [Locally Weighted Linear Regression](#lwr)
    - [Algorithm Discussion](#lwr-discussion)
    - [Performance Analysis and Parallelization Options](#lwr-performance)
2. [Hadoop Ecosystem Overview](#hadoop-overview)
3. [Setting Up OS Env](#os-setup)
4. [NoSQL implementations:](#nosql)
    - [MapReduce](#nosql-mapreduce)
    - [Spark](#nosql-spark)
    - [Hive](#nosql-hive)
    - [SparkSQL](#nosql-sparksql)

## <a id="lwr"></a> 1. Locally Weighted Linear Regression
Often, when working with real data, we realize that our data doesn't really lie on the straight line - in other words linear regression fails to capture a lot of variation. When that happens we can use a higher degree polynomial of our features to fit data perfectly. The problem with such parametric approach is two-fold: first, we need to manually choose the "right" degree of polynomials which leads to either underfitting or overfitting; second, we don't take advantage of the new data that will flow in - once the model is set it is not going to change.

To address these issues we want to implement Locally Weighted [Linear] Regression (LWR), which, assuming sufficient size of the training set, makes the choice of features much less critical. Additionally, LWR is a lazy learning approach and allows us learn on the newly obtained data. Given the goal of Big Data analytics, we definitely want to make use of all the data, yet we are concerned with the computational efficiency. Thus we would like to use NoSQL tools to implement LWR. Now let us briefly discuss the math behind the LWR algorithm, evaluate its time complexity  and find possibilities for optimization via parallelization.

### <a id="lwr-discussion"></a> Algorithm Discussion
To understand Locally Weighted linear Regression (LWR) let us consider a simple linear regression (LR) first. As an input we have N-dimensional dataset X with M examples (each example has N features) and 1-dimensional vector Y with targets. The goal of LR is to fit the line that would map X -> Y at the minimized OLS sum. Such line would allows us to predict y-value for any x-input.
```shell
m  | X (features)  | Y (targets)  
--------------------------------
1: |1 x0 x1 x2 ... xn| y
2: |1 x0 x1 x2 ... xn| y
.: |1 ...      ...   | y
M: |1 x0 x1 x2 ... xn| y
```
Note that we appended X to a columns of ones - resulting matrix is called a *design matrix* - it allows us to find the intercept of the line. To construct that line (or, more generally, a hyperplane in N-dimensional space) we find the best hypothesis **theta** (which is a vector [size N] of coefficients for each dimension of X) by solving the following normal equation:
<center>X'X&theta;=X'Y</center>

The closed form solution then:
<center>&theta;=inv(X'X)X'Y</center>

This solution gives the intercept and slopes (hypothesis &theta;) for the line in each X's dimension. The LWR goes a step further and locally adjusts the line according to the proximity to other data points - the closer the point the more weight it has.

That is a good time to introduce one simple yet not very intuitive feature of LWR. In LR, all we need to do in order to construct a line (hyperplane) is to solve *one normal equation*, which gives the hypothesis &theta;, using which *we can predict y-value for any input x-value* by reusing the hypothesis and simply calculating the product x'&theta; (here and later capital X or Y represents a set of data examples while small x or y represents one particular example).

In the LWR, since our predictions are no longer linear, but adjusted by the neighboring points, *for each x-point we want to predict (we would call it query point), we need to calculate its own hypothesis &theta;*. For each such query point we consider all other points available, but their influence is weighted by the distance to our query point. That is a LWR in a nutshell. Let us now see how it translates into linear algebra.

In fact, all we need to change for LWR is to add a weight matrix W (diagonal matrix of size m x m), and solve the analogous normal equation as:
<center>&theta;=inv(X'WX)X'WY</center>

Finally, note that we use a Gaussian Kernel as our distance function. We use bandwidth parameter *C=0.5* throughout this project. The choice of the bandwidth could be optimized and found automatically, but that does not change anything in our area of interest.

### <a id="lwr-performance"></a> Performance Analysis and Parallelization Options
Just how fast LWR works? Should we even care to parallelize? The answer is yes - we want to calculate the distance to every other data point after all. In particular, we assume that there are ever growing loads of examples to learn on available (hundreds of thousands or more), while the number of features in each example is relatively small (on the order of tens or hundreds). In other word we explicitly assume **M >> N**. Also we have *P* cores (or commodity computers in the cluster) available.

One obvious way to parallelize LWR is when we want to calculate the prediction for several query points. In that case we simply split the set of Q query points between the P cored and we are done ~Q/P times faster. Implementing this trivial solution is rather straightforward so we would not consider it. Instead we would be concerned in how can we *parallelize the computations for a single query point*.

Recall that in order to find a hypothesis &theta; for a single query point over the set of training examples we need to solve the following normal equation:
<center>A&theta;=B</center>
Where:

```shell
A = X'WX has dimensions: X'(n x m) * W(m x m) * X(m x n) => A (n x n)
B = X'WY has dimensions: X'(n x m) * W(m x m) * Y(m x 1) => B (n x 1)
theta = inv(A)*B has dimensions: A (n x n) * b (n x 1) => theta (n x 1)
```
Note that we can perform exactly the same operations over an individual training examples:
```shell
# given ith example x = X[i]
a = x'wx has dimensions: x'(n x 1) * w(1 x 1) * x(1 x n) => a (n x n)
b = x'wy has dimensions: x'(n x 1) * w(1 x 1) * y(1 x 1) => b (n x 1)
```
And they produce the matricies a and b of exactly the same size as A and B. Thus we notice the additivity property in the LWR calculation, and that is a good sign of the parallelization eligibility.

In fact, all we need to do is to split all the training examples into the P equal parts and feed them to P cores to deal with. Each core will compute partial sums of matricies A and B. Then we simply sum those intermediate matricies produced by each core into resulting A and B, and then compute the hypothesis as &theta;=inv(A)\*B

The time complexity of a single core LWR is given by O(mn<sup>2</sup>) to compute x'x, m times, plus O(n<sup>3</sup>) to invert the matrix, totalling to O(mn<sup>2</sup> + n<sup>3</sup>).

On our LWR (no parallelization of the matrix inverse), P cores gives us total of O(mn<sup>2</sup>/P + n<sup>3</sup>), plus some communication cost. Given our assumption m>>n we can drop the n term and estimate the time complexity as O(m/P), and expect that, in theory, LWR should perform linearly faster with the increase in the number of cores.


## <a id="hadoop-overview"></a> 3. Hadoop Ecosystem Overview
### Hadoop Ecosystem Overview
How do we set about to implement LWR in NoSQL world? We want something robust, open source and easy to work with. Luckily, there is just such a thing:
> The Apache Hadoop software library is a framework that allows for the distributed processing of large data sets across clusters of computers using simple programming models.

Hadoop consists of two main things: a *Distributed File System (HDFS)* and computational framework *MapReduce*. HDFS provides us with fault tolerant distributed file storage system that provides high-throughput access to application data. MapReduce allows easy parallel processing of large data sets. There are also a *Hadoop Common* utilities used by other tools within Hadoop Ecosystem, and YARN - framework for job scheduling and cluster resource management, which is not going to play a critical role in our implementations.

 #TODO JUSTIFY tools selection
but lacks random read and write access.

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


## <a id="os-setup"></a> 2. Setting Up OS Env
You can skip this section if you are simply executing files on provided VM (come back if you see any suspicious exceptions). Here we highlight the basic OS environment setup that will ease our work with NoSQL tools. All the tools, in the latest stable version as of 25 April 2016, were downloaded from official Apache servers and unpacked into */nosql/<toolname>* folder. Along with that, */nosql/* folder contains an *input/* folder with our input data. Below is a short description of the project folder structure:
```shell
$ sudo su    # password: bigdata
$ cd /nosql
$ tree --filelimit 8  # show folder structure
├── hadoop
│   ├── aux                             # Sources and auxiliary scripts that were left off
│   ├── hadoop-2.7.2                    # Hadoop Home
│   ├── lwr_mapreduce_find_theta.py     # Script to find hypothesis using MR output files
│   ├── lwr_mapreduce_mapper.py         # MapReduce mapper
│   ├── lwr_mapreduce_reducer.py        # MapReduce reducer
│   ├── lwr_plot_x_query.py             # Demo script to visualize LWR prediction in 2D
│   ├── np_matrix_helpers.py            # Helper functions to communicate Numpy matricies
│   └── README.md         
├── hive   
│   ├── apache-hive-2.0.0-bin           # Hive Home
│   ├── aux   
│   ├── lwr_hive_find_theta.py   
│   ├── lwr_hive_mapper.py   
│   └── README.md   
├── input                               # Input data (txt) files, separator=','
│   ├── x_data.txt x_data2.txt ...   
├── lwr_demo.png                        # Demo of the LWR prediction
├── README.md                           # This document
├── spark                            
│   ├── aux
│   ├── lwr_spark.py
│   ├── README.md
│   └── spark-1.6.1-bin-without-hadoop  # Spark Home
└── sparksql
    ├── csv-to-json.py
    ├── lwr_sparksql.py
    └── README.md
```

To be able to run all the tools from anywhere we need to update system *PATH* variable. To make update permanent, we put append into */root/.bash_rc* the */root/.bash_nosql_exports* file with the following content:
```shell
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export HADOOP_HOME=/nosql/hadoop/hadoop-2.7.2
export SPARK_HOME=/nosql/spark/spark-1.6.1-bin-without-hadoop
export HIVE_HOME=/nosql/hive/apache-hive-2.0.0-bin

# Append PATH
export PATH=$HIVE_HOME/bin:$HADOOP_HOME/bin:$SPARK_HOME/bin:$PATH
```

Save that and open a new terminal to apply changes. Check you PATH:
```shell
$ echo $PATH
/nosql/hive/apache-hive-2.0.0-bin/bin:/nosql/hadoop/hadoop-2.7.2/bin:/nosql/spark/spark-1.6.1-bin-without-hadoop/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:
```

Despite these are permanent settings, when we run the any of the tools, they look into *<tool>-env.sh* conf file to apply any settings. You want to make sure you have the following:  
```shell
$ vi ${HADOOP_HOME}/etc/hadoop/hadoop-env.sh
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export PATH=${JAVA_HOME}/bin:${PATH}
# make sure you append tools.jar to an existing HADOOP_CLASSPATH
export HADOOP_CLASSPATH=${JAVA_HOME}/lib/tools.jar:${HADOOP_CLASSPATH}

vi ${SPARK_HOME}/conf/spark-env.sh
# We reuse our Hadoop installation in Spark - specify the path
export SPARK_DIST_CLASSPATH=$(/nosql/hadoop/hadoop-2.7.2/bin/hadoop classpath)
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export SPARK_HOME=/nosql/spark/spark-1.6.1-bin-without-hadoop

vi ${HIVE_HOME}/conf/spark-env.sh
export HADOOP_HOME=/nosql/hadoop/hadoop-2.7.2  # Hive uses Hadoop common libraries
export HIVE_HOME=/nosql/hive/apache-hive-2.0.0-bin
export PATH=$HIVE_HOME/bin:$PATH
```

Note that SparkSQL, despite being a separate tool, comes within the basic Spark distribution and thus everything is already set (almost - we would need to compile it with the specific jars to support, say, the interaction with Hive, but we won't do that).




## <a id="nosql"></a> 4. NoSQL implementations:
### <a id="nosql-mapreduce"></a> MapReduce  
### <a id="nosql-spark"></a> Spark
### <a id="nosql-hive"></a> Hive
### <a id="nosql-sparksql"></a> SparkSQL


sudo su
make sure path is correct
We provide redundant code to make examples self contained

on top of Hive on top of HDFS
