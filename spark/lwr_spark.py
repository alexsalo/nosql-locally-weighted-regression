from pyspark import SparkContext
import sys
import numpy as np

C = 0.5  # regularization parameter - bias & variance trade-off

# This is just for a demo
x_query = np.matrix([1, -5.6, 9.1566, -2.0867])

# we have several splits of the data files
filename = '/user/root/input/x_data*.txt'
sc = SparkContext('local', 'spark app')
data = sc.textFile(filename).cache()


def mapAb(line):
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

    values = line.strip().split(',')
    x = np.matrix([1.0] + [float(val) for val in values[:-1]])
    y = np.matrix([float(values[-1])])

    weight = gauss_kernel(x, c=C)

    return [('a', np.multiply(x.T * x, weight)),
            ('b', np.multiply(x.T * y, weight))
            ]

# - flatMap maps input into list of tuples (K, V)
# - reduceByKey sorts and reduces the list
# - collect is a simple action that forces execution of flatMap and reduceByKey,
# which are transforamtion (executed lazy)
ab = data.flatMap(mapAb).reduceByKey(lambda total, mat: total + mat).collect()

a = ab[0][1]  # first element of the list, second element in the tuple
b = ab[1][1]  # second element of the list, second element in the tuple

theta = a.I * b

# save result into HDFS
x = sc.parallelize(theta)
out_path = '/user/root/spark_output'
x.saveAsTextFile(out_path)
print '\nHypothesis theta has been successfully saved into: %s\n%s' % (out_path, theta)
