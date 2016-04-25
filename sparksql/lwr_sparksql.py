from pyspark import SparkContext
from pyspark.sql import SQLContext
import sys
import numpy as np

C = 0.5  # regularization parameter - bias & variance trade-off

# This is just for a demo
x_query = np.matrix([1, -5.6, 9.1566, -2.0867])

# this time we will read local file
filename = '/user/root/input_json/data_x.json'
sc = SparkContext('local', 'spark sql app')

sqlContext = SQLContext(sc)
lwr_data = sqlContext.read.json(filename)
lwr_data.registerTempTable('lwr_data')

# mapper in Spark SQL works with row as a input unit
def mapAb(row):
    """
    Parse line into float values x1 x2 .. xn : y
    compute matricies A and b and return
    them in list of tuples with related key.
    """
    def gauss_kernel(x_to, c):
        """
        :param c - regularization
        :param x_to - data point for which the distance from x_query is returned
        """
        d = x_query - x_to
        d_sq = d * d.T
        return np.exp(d_sq / (-2.0 * c**2))

    # how would we know how may columns are there in the row?
    n = len(row) #TODO
    x = np.matrix([1.0] + [row['x%s' % i] for i in xrange(n - 1)])
    y = np.matrix([row['x%s' % (n - 1)]])

    weight = gauss_kernel(x, c=C)

    return [('a', np.multiply(x.T * x, weight)),
            ('b', np.multiply(x.T * y, weight))
            ]

ab = lwr_data.flatMap(mapAb).reduceByKey(lambda total, mat: total + mat).collect()

a = ab[0][1]  # first element of the list, second element in the tuple
b = ab[1][1]  # second element of the list, second element in the tuple

theta = a.I * b

# save result into HDFS
x = sc.parallelize(theta)
out_path = '/user/root/sparksql_output'
x.saveAsTextFile(out_path)
print '\nHypothesis theta has been successfully saved into: %s\n%s' % (out_path, theta)
