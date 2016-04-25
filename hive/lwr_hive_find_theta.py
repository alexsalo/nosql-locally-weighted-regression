import sys
import numpy as np

def str2mat(str):
    rows = str.split(';')
    m, n = len(rows), len(rows[0].split(','))
    mat = np.matrix(np.zeros((m, n)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row.split(',')):
            mat[i, j] = float(val)
    return mat

a, b = None, None
for line in sys.stdin:
    a_str, b_str = line.strip().split('\t')
    a_mat = str2mat(a_str)
    b_mat = str2mat(b_str)

    if a is None:  # either or both are None
        a = a_mat
        b = b_mat
    else:
        a += a_mat
        b += b_mat

theta = a.I * b
theta_vals = [theta[i, 0] for i in xrange(theta.shape[0])]
theta_vals_str = [str(val) for val in theta_vals]
print '\t'.join(theta_vals_str)
