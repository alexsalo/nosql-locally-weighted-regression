#!/usr/bin/env python

import sys

firstline_vals = sys.stdin.readline().strip().split(',')
n = len(firstline_vals)

# %% - escapes formatting %
# second argument without quotes - interpreted as double by json reader
pattern = '{' + ', '.join(['"x%s": %%s' % i for i in xrange(n)]) + '}\n'
print 'pattern: %s\nExample of json: %s' % (pattern, pattern % tuple(firstline_vals))

with open('data_x.json', 'w') as f:
    for line in sys.stdin:
        vals = [float(v) for v in line.strip().split(',')]
        f.write(pattern % tuple(vals))
f.close()
