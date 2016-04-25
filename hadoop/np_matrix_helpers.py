import numpy as np


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


def str2mat(str):
    rows = str.split(';')
    m, n = len(rows), len(rows[0].split(','))
    mat = np.matrix(np.zeros((m, n)))
    for i, row in enumerate(rows):
        for j, val in enumerate(row.split(',')):
            mat[i, j] = float(val)
    return mat
