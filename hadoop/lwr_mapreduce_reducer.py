#!/usr/bin/env python

from np_matrix_helpers import *
import numpy as np
import sys

# Sum A and b matricies recieved from mapper
a, b = None, None
for line in sys.stdin:
    mat_type, mat_str = line.strip().split('\t', 1)
    mat = str2mat(mat_str)
    
    if mat_type == 'a':
        if a is None:
            a = mat
        else:
            a += mat
    if mat_type == 'b':
        if b is None:
            b = mat
        else:
            b += mat

# emit full matricies A and b to STDOUT
print '%s' % (mat2str(a))
print '%s' % (mat2str(b))
