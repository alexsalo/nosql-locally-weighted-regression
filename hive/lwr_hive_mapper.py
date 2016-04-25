import sys
import numpy as np

C = 0.5

# This is just for a demo
x_query = np.matrix([1, -5.6, 9.1566, -2.0867])

def gauss_kernel(x_to, c):
    d = x_query - x_to
    d_sq = d * d.T
    return np.exp(d_sq / (-2.0 * c**2))

def mat2str(mat):
    s, m, n = '', mat.shape[0], mat.shape[1]
    for i in xrange(m):
        for j in xrange(n):
            if j < n - 1:
                s += '%.8f,' % mat[i, j]
            else:
                s += '%.8f' % mat[i, j]
        if i < m - 1:
            s += ';'
    return s

a, b = None, None
for line in sys.stdin:
    # (IMPORTANT) note this change to internal Hive's delimiter
    values = line.strip().split('\t')
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
print '%s\t%s' % (mat2str(a), mat2str(b))
