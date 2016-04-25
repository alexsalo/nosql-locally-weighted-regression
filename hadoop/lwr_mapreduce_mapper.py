#!/usr/bin/env python

import sys
import numpy as np
from np_matrix_helpers import mat2str

C = 0.5  # regularization parameter - bias & variance trade-off

# This is just for a demo
x_query = np.matrix([1, -5.6, 9.1566, -2.0867])


def gauss_kernel(x_to, c):
    """
    :param c - regularization
    :param x_to - data point for which the distance from x_query is returned
    """
    d = x_query - x_to
    d_sq = d * d.T
    return np.exp(d_sq / (-2.0 * c**2))


# Read file line by line,
# Calculate and emit normal equation matricies A and b
a, b = None, None
for line in sys.stdin:
    values = line.strip().split(',')
    x = np.matrix([1.0] + [float(val) for val in values[:-1]])
    y = np.matrix([float(values[-1])])

    weight = gauss_kernel(x, c=C)

    if a is None:
        a = np.multiply(x.T * x, weight)  # n x n
    else:
        a += np.multiply(x.T * x, weight)

    if b is None:
        b = np.multiply(x.T * y, weight)  # n x 1
    else:
        b += np.multiply(x.T * y, weight)

# emit partial resulting martricies A and b into STDOUT
print '%s\t%s' % ('a', mat2str(a))
print '%s\t%s' % ('b', mat2str(b))
