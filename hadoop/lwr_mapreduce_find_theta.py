#!/usr/bin/env python

from np_matrix_helpers import str2mat
import sys
import numpy as np

def find_theta(a_str, b_str):
    a = str2mat(a_str)
    b = str2mat(b_str)
    #print 'A:\n%s\nA.I:\n%s\nb:\n%s\nTheta is:\n%s' % (a, a.I, b, '')
    return a.I * b

a = sys.stdin.readline().strip()
b = sys.stdin.readline().strip()
theta = find_theta(a, b)
print theta
