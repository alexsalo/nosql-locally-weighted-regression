##Implementation tools
###Hadoop + MapReduce
Hadoop ecosystem (version 2.7.2 used) comes with HDFS file system and MapReduce framework for writing apps to process vast amounts of data in parallel on many nodes (machines).

To use MR one can either implement abstract map and reduce clases in Java or take advantage of Hadoop Streaming api, which is a utility allowing to run any executable as Mapper/Reducer. Essentially, Hadoop Streaming facilitates passing data between our Map and Reduce phases via STDIN and STDOUT. Since we are using Python, to read &lt;key, value> pair we simply read from sys.stdin; to emit &lt;key, value> pair we write (print) to sys.stdout. Hadoop Streaming takes care of the rest.

# Locally Weighted Linear Regression with MapReduce on Hadoop HDFS via Streaming API
Hadoop Streaming API allows to run any executable files as mappers and reducers in MapReduce framework. We are using Python to implement locally weighted linear regression algorithm. Our implementation contains the following files:

```shell
input/*               # folder with input data files with sep=','
np_matrix_helpers.py  # helper functions to communicate numpy matricies
lwr_bulk_mapper.py    # MapReduce mapper
lwr_reducer.py        # MapReduce reducer
find_theta.py         # Finds LWR hypothesis using MapReduce output file
plot_x_query.py       # Demo script to visualize LWR prediction in 2D
```

There are three ways to execute:

1. [Linux pipes to imitate MapReduce for development/testing purposes](#linux-pipes)
2. [Hadoop single node without HDFS to make sure everything works](#hadoop-single)
3. [Hadoop pseudo-distributed mode, which emulate the full working environment with HDFS running (but without YARN)](#pseudo-distributed)

All the following commands are issued from the *hadoop* working directory on the virtual machine under root privileges:
```shell
$ sudo su            # password: bigdata
$ cd /nosql/hadoop/  # which has hadoop installation hadoop-2.7.2/
```

Important note: make sure all your python executable files know the path to python interpreter and have correct privileges:
```shell
$ cat python_script.py
# #!/usr/bin/env python
# ...
$ chmod +x python_script.py
```

Also, if you setup hadoop on your own, don't forget to edit *hadoop-env* file to specify JAVA_HOME and the like:
```shell
vi hadoop-2.7.2/etc/hadoop/hadoop-env.sh
# The java implementation to use.
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export PATH=${JAVA_HOME}/bin:${PATH}
export HADOOP_CLASSPATH=${JAVA_HOME}/lib/tools.jar  # very important!
```


Finally, at the end of this document there is an example on how to run a demo.

### 1. Linux pipes development/testing <a id="linux-pipes"></a>
While each step could be separated, ultimately we want to chain *input -> mapper -> reducer -> find_theta:*

First, let's run mapper and reducer on the input files:
```shell
$ cat py_lwr_subgroups_sums/input/* | \
/nosql/hadoop/py_lwr_subgroups_sums/lwr_bulk_mapper.py | \
/nosql/hadoop/py_lwr_subgroups_sums/lwr_reducer.py
```
Which produces the following output:
```shell
0.04429884,-0.25175942,0.40566047,-0.01703711;-0.25175942,1.43521279,-2.30624365,0.09647099;0.40566047,-2.30624365,3.71557318,-0.15618137;-0.01703711,0.09647099,-0.15618137,0.00681046
-0.26564261;1.51042747;-2.43520908;0.10292634
```
These are two lines, each containing numpy arrays encoded for io via *np_matrix_helpers.py*. First line is a matrix **A (n x n)**; second line is a matrix **b (n x 1)**.

With linux pipes we can directly feed these matricies to *find_theta.py* script to make a hypothesis:
```shell
$ cat py_lwr_subgroups_sums/input/* | \
/nosql/hadoop/py_lwr_subgroups_sums/lwr_bulk_mapper.py | \
/nosql/hadoop/py_lwr_subgroups_sums/lwr_reducer.py | \
/nosql/hadoop/py_lwr_subgroups_sums/find_theta.py
```
Which produces the hypothesis that we were looking for:
```shell
[[ 26.89559418]
 [ -0.58025811]
 [ -3.96902175]
 [ -0.40520663]]
```

### 2. Hadoop single node without HDFS <a id="hadoop-single"></a>
First, make sure single node mode is activated. Edit the following two files and leave empty configuration tags:
```shell
$ vi hadoop-2.7.2/etc/hadoop/core-site.xml hdfs-site.xml
# <configuration>
# </configuration>
```

Then let's remove an output folder from the previous run (otherwise you'll see error):
```shell
$ rm -r py_lwr_subgroups_sums/output
```

Now we can run Hadoop MapReduce. Don't forget to include streaming API jar:
```shell
$ hadoop-2.7.2/bin/hadoop \
jar hadoop-2.7.2/share/hadoop/tools/lib/hadoop-streaming-2.7.2.jar \
-mapper py_lwr_subgroups_sums/lwr_bulk_mapper.py \
-reducer py_lwr_subgroups_sums/lwr_reducer.py \
-input py_lwr_subgroups_sums/input/* \
-output py_lwr_subgroups_sums/output
```
That produces two lines with matricies **A** and **b**, just as our linux pipes example did. To make a hypothesis do:

```shell
cat py_lwr_subgroups_sums/output/* | py_lwr_subgroups_sums/find_theta.py
```
Which again produces the hypothesis:
```shell
[[ 26.89559418]
 [ -0.58025811]
 [ -3.96902175]
 [ -0.40520663]]
```

### 3. Hadoop in pseudo-distributed mode with HDFS running <a id="pseudo-distributed"></a>
First, make sure pseudo-distributed mode is activated. Edit the following two files and add the following configuration tags:
```shell
$ vi hadoop-2.7.2/etc/hadoop/core-site.xml
# <configuration>
#     <property>
#         <name>fs.defaultFS</name>
#         <value>hdfs://localhost:9000</value>
#     </property>
# </configuration>

$ vi hadoop-2.7.2/etc/hadoop/hdfs-site.xml
# <configuration>
#     <property>
#         <name>dfs.replication</name>
#         <value>1</value>
#     </property>
# </configuration>
```

Then format HDFS:
```shell
$ hadoop-2.7.2/bin/hdfs namenode -format
```

Start NameNode and DataNode daemons:
```shell
$ hadoop-2.7.2/sbin/start-dfs.sh
```

Check that HDFS has the following directories by browsing http://localhost:50070/. If not present - create them:
```shell
$ hadoop-2.7.2/bin/hdfs dfs -mkdir /user
$ hadoop-2.7.2/bin/hdfs dfs -mkdir /user/root  # should be the same username as in your vm
$ hadoop-2.7.2/bin/hdfs dfs -mkdir /user/root/input
```

Put input file(s) from local path into HDFS path. Note that (given our test data size is relatively small) in order to make more mappers we want to make more data splits, which is naturally achieved by dividing data file into several files. In our case we simply copy the same data file several times.
```shell
$ hadoop-2.7.2/bin/hdfs dfs -put py_lwr_subgroups_sums/input/* /user/root/input/
```

Now that setup is done we can actually run our executable python scripts as a MapReduce jobs (make sure you removed the output folder if you run second time):
```shell
$ hadoop-2.7.2/bin/hadoop jar hadoop-2.7.2/share/hadoop/tools/lib/hadoop-streaming-2.7.2.jar \
-mapper py_lwr_subgroups_sums/lwr_bulk_mapper.py \
-reducer py_lwr_subgroups_sums/lwr_reducer.py \
-input /user/root/input/* \
-output /user/root/output
```

Now cat resulted matrix in HDFS and calculate thetas what we were looking for:
```shell
$ hadoop-2.7.2/bin/hdfs dfs -cat /user/root/output/* | /nosql/hadoop/py_lwr_subgroups_sums/find_theta.py
```

### Demo of locally weighted prediction strategy
This tutorial comes with a demo. Run the following script to visually confirm LWR prediction, which takes into account the locality of the x_query (unlike simple linear regression):
```shell
$ hadoop-2.7.2/bin/hdfs dfs -cat /user/root/output/* | /nosql/hadoop/py_lwr_subgroups_sums/plot_x_query.py
```

This should produce a picture like that:
![Demo](lwr_demo.png)

To finish up - shut down the daemons:
```shell
$ hadoop-2.7.2/sbin/stop-dfs.sh
```

### A note on scalability
Provided algorithm scales efficiently as the data volume growth. With N nodes in the system, the HDFS distributes the large file over all these N nodes. When you start a job, there will be N mappers by default (in our case of small data split into four files there are four mappers by default). Hadoop makes sure the mapper on a machine will process the part of the data that is stored on this node, which is called Rack awareness.

### A note on matrix IO
We implemented custom serializer/parser to communicate matricies between mapper and reducer. As it turned out, the float precision is of crucial importance for that matter. For a production environment one may want to increase precision of the floating point (currently 8 digits after the point) in *np_matric_helpers*.
