# Locally Weighted Linear Regression with MapReduce on Hadoop HDFS via Streaming API
Hadoop Streaming API allows to run any executable files as mappers and reducers in MapReduce framework. We are using Python to implement locally weighted linear regression algorithm - we provide a simplified code listing for illustrative purposes below. There are three ways to execute python scripts:

1. [Linux pipes to imitate MapReduce for development/testing purposes](#linux-pipes)
2. [Hadoop single node without HDFS to make sure everything works](#hadoop-single)
3. [Hadoop pseudo-distributed mode, which emulate the full working environment with HDFS running (but without YARN)](#pseudo-distributed)

Also you can jump straight to [Visual Demo of LWR Prediction](#demo)

##### MapReduce Streaming API Implementation
Let us briefly review our implementation (full code available at [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)). Mapper:
```python
def gauss_kernel(x_to, c):
    d = x_query - x_to
    d_sq = d * d.T
    return np.exp(d_sq / (-2.0 * c**2))


# read file line by line; calculate and emit normal equation matricies A and B
for line in sys.stdin:
    # parse values assuming x1 x2 x3 ... y
    values = line.strip().split(',')
    x = np.matrix([1.0] + [float(val) for val in values[:-1]])
    y = np.matrix([float(values[-1])])

    weight = gauss_kernel(x, c=C)

    # accumulate A and B
    a += np.multiply(x.T * x, weight)
    b += np.multiply(x.T * y, weight)

# emit partial resulting martricies A and B into STDOUT
print '%s\t%s' % ('a', mat2str(a))
print '%s\t%s' % ('b', mat2str(b))
```

Reducer:
```python
# sum A and b matricies received from mapper
for line in sys.stdin:
    # parse <key, value> from STDIN
    mat_type, mat_str = line.strip().split('\t', 1)
    mat = str2mat(mat_str)

    if mat_type == 'a':
       a += mat
    if mat_type == 'b':
       b += mat

# emit full matricies A and B to STDOUT (saved into HDFS)
print '%s' % (mat2str(a))
print '%s' % (mat2str(b))
```

Time to execute! All the following commands are issued from the */nosql/hadoop/* on the virtual machine under root privileges:
```shell
$ sudo su            # password: bigdata
$ cd /nosql/hadoop/  # which has hadoop installation hadoop-2.7.2/
```

#### <a id="linux-pipes"></a> 1. Linux Pipes for Development/Testing
While each step could be separated, ultimately we want to chain *input -> mapper -> reducer -> find_theta:*

First, let's run mapper and reducer on the input files:
```shell
$ cat /nosql/input/* | /nosql/hadoop/lwr_mapreduce_mapper.py | /nosql/hadoop/lwr_mapreduce_reducer.py
```
Which produces the following output:
```shell
0.04429884,-0.25175942,0.40566047,-0.01703711;-0.25175942,1.43521279,-2.30624365,0.09647099;0.40566047,-2.30624365,3.71557318,-0.15618137;-0.01703711,0.09647099,-0.15618137,0.00681046
-0.26564261;1.51042747;-2.43520908;0.10292634
```
These are two lines, each containing numpy arrays encoded for IO via *np_matrix_helpers.py*. First line is a matrix **A (n x n)**; second line is a matrix **B (n x 1)**.

With Linux pipes we can directly feed these matricies to *find_theta.py* script to make a hypothesis:
```shell
$ cat /nosql/input/* | /nosql/hadoop/lwr_mapreduce_mapper.py |
/nosql/hadoop/lwr_mapreduce_reducer.py | /nosql/hadoop/lwr_mapreduce_find_theta.py
```
Which produces the hypothesis that we were looking for:
```shell
[[ 26.89559418]
 [ -0.58025811]
 [ -3.96902175]
 [ -0.40520663]]
```

#### <a id="hadoop-single"></a> 2. Hadoop single node without HDFS
*--You can skip this part if you are not developing new functionality--*

First, make sure single node mode is activated. Edit the following two files and leave empty configuration tags:
```shell
$ vi hadoop-2.7.2/etc/hadoop/core-site.xml hdfs-site.xml
# <configuration>
# </configuration>
```

Then let's remove an output folder from the previous run (otherwise you'll see error):
```shell
$ rm -r mapreduce_output
```

Now we can run MapReduce. Don't forget to include streaming API jar:
```shell
$ hadoop jar hadoop-2.7.2/share/hadoop/tools/lib/hadoop-streaming-2.7.2.jar \
-mapper lwr_mapreduce_mapper.py \
-reducer lwr_mapreduce_reducer.py \
-input /nosql/input/* \
-output output
```
That produces two lines with matricies **A** and **B**, just as our Linux pipes example did (we will take a closer look at MapReduce log info in the next part). To make a hypothesis do:

```shell
cat output/* | /nosql/hadoop/lwr_mapreduce_find_theta.py
```
Which again produces the hypothesis:
```shell
[[ 26.89559418]
 [ -0.58025811]
 [ -3.96902175]
 [ -0.40520663]]
```

#### <a id="pseudo-distributed"></a> 3. Hadoop in Pseudo-Distributed Mode with HDFS Running
Now that the trials of dev and tests are finished, let's run a full deal. First, make sure pseudo-distributed mode is activated. Edit the following two files and add the following configuration tags:
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
$ hdfs namenode -format
```

Start NameNode and DataNode daemons:
```shell
$ hadoop-2.7.2/sbin/start-dfs.sh
```

Check that HDFS has the following directories by browsing http://localhost:50070/. If not present - create them:
```shell
$ hdfs dfs -mkdir /user
$ hdfs dfs -mkdir /user/root  # should be the same username as in your vm
$ hdfs dfs -mkdir /user/root/input
```

Put input file(s) from local path into HDFS path. Note that (given our test data size is relatively small) in order to make more mappers we want to make more data splits, which is naturally achieved by dividing data file into several files. In our case we simply copy the same data file several times.
```shell
$ hdfs dfs -put /nosql/input/* /user/root/input/
```

Now that the preparation is done we can actually run our executable python scripts as a MapReduce jobs (make sure you removed the output folder if you run second time):
```shell
$ hdfs dfs -rm /user/root/mapreduce_output
$ hadoop jar hadoop-2.7.2/share/hadoop/tools/lib/hadoop-streaming-2.7.2.jar \
-mapper lwr_mapreduce_mapper.py \
-reducer lwr_mapreduce_reducer.py \
-input /user/root/input/* \
-output /user/root/mapreduce_output
```

Note the following in the MapReduce log info:
```shell
...
16/04/26 11:14:25 INFO mapred.FileInputFormat: Total input paths to process : 4
16/04/26 11:14:25 INFO mapreduce.JobSubmitter: number of splits:4
...
Map-Reduce Framework
		Map input records=5488
		Map output records=8
		Map output bytes=940
    ...
		Reduce input groups=2
    ...
		Reduce input records=8
		Reduce output records=2
```
MapReduce framework decide number of splits over the input data based on the split_size, determined as *split_size = max(minimumSize, min(maximumSize, blockSize))*. Additionally, it naturally "splits" the separate files. We took advantage of the latter to force 4 splits, which produced 8 map output records (4 of each partially summed matricies A and B). Then framework shuffled and sorted map output records and reduced by key into 2 output records (fully summed A and B). That is the output that we save on HDFS /mapreduce_output.

Now we can cat resulted matricies in HDFS and calculate thetas what we were looking for:
```shell
$ hdfs dfs -cat /user/root/mapreduce_output/* | /nosql/hadoop/lwr_mapreduce_find_theta.py
```

Which again produces the correct hypothesis &theta;:
```shell
[[ 26.89559418]
 [ -0.58025811]
 [ -3.96902175]
 [ -0.40520663]]
```

####  <a id="demo"></a> Visual Demo of LWR Prediction
This tutorial comes with a demo. Run the following script to visually confirm LWR prediction, which takes into account the locality of the x_query (unlike simple linear regression):
```shell
$ hdfs dfs -cat /user/root/mapreduce_output/* | /nosql/hadoop/lwr_plot_x_query.py
```

This should produce a picture like that:
<img src="lwr_demo.png" alt="Demo" style="width: 800px;"/>

To finish up - shut down the daemons:
```shell
$ hadoop-2.7.2/sbin/stop-dfs.sh
```

##### A Note on Scalability
Provided algorithm scales efficiently as the data volume growth. With N nodes in the system, the HDFS distributes the large file over all these N nodes. When you start a job, there will be N mappers by default (in our case of small data split into four files there are four mappers by default). Hadoop makes sure the mapper on a machine will process the part of the data that is stored on this node, which is called Rack awareness.

##### A Note on Matrix IO
We implemented custom serializer/parser to communicate matricies between mapper and reducer. As it turned out, the float precision is of crucial importance for that matter. For a production environment one may want to increase precision of the floating point (currently 8 digits after the point) in *np_matric_helpers*.
