#!/usr/bin/env python
'''
This script plots a demo of LWR prediction
Run example: cat output/* | /nosql/hadoop/py_lwr_subgroups_sums/plot_x_query.py
'''
import sys
from np_matrix_helpers import str2mat
import matplotlib.pylab as plt
import numpy as np

COLUMN_NUMBER = 1  # Columns to use as a feature for LWR plot

# This is just for a demo, should be the same as in lwr_bulk_mapper.py
x_query = np.matrix([1, -5.6, 9.1566, -2.0867])


def read_data(filename):
    # assuming last columns is a target
    features = []
    targets = []

    with open(filename) as f:
        for line in f:
            values = line.split(',')
            features.append([1.0] + [float(val) for val in values[:-1]])
            targets.append([float(values[-1])])

    return np.mat(features), np.mat(targets)


def batch_linear_regression(x, y):
    """
    :param x - samples (features) -- (M x N)
    :param y - targets            -- (M x 1)
    """
    theta = (x.T * x).I * (x.T * y)
    return theta


def plot_x_query(lwr_theta):
    print 'Welcome to the plot demo!\n================================\n Locally weighted regression: lwr_theta for an x_query:\n%s' % lwr_theta

    # Read data to make a scatter plot and LR fit
    x, y = read_data('/nosql/hadoop/py_lwr_subgroups_sums/input/x_data.txt')
    x_2dim = x[:, [0, COLUMN_NUMBER]]  # because we can't plot more than two dimensions
    theta = batch_linear_regression(x_2dim, y)
    print 'Simple liner regression produce the following theta for the regression line:\n%s' % theta

    # construct a line from intercept and coefficient
    x_pred = [min(x[:, 1])[0, 0], max(x[:, 1])[0, 0]]
    y_pred = [theta[0, 0] + v * theta[1, 0] for v in x_pred]

    plt.figure(figsize=(14,10))
    plt.plot(x_2dim[:, 1], y, 'bo', label='Training Set')
    plt.plot(x_pred, y_pred, 'r-', label='Linear Regression')

    # Predict outcome for x_query
    y_query = x_query * lwr_theta
    print 'Given the x_query: %s, LWR predicts target: %s' % (x_query, y_query)
    plt.plot(x_query[:, COLUMN_NUMBER], y_query, 'go', markersize=10,
            label='Locally Wheighted Linear Regression x_query Prediction')

    # Circle the prediction and fine tune the plot
    circle = plt.Circle((x_query[:, COLUMN_NUMBER], y_query), 2, color='y', fill=False)
    plt.gca().add_artist(circle)
    plt.grid()
    plt.legend(loc=2)
    plt.tight_layout()
    plt.show()


a = str2mat(sys.stdin.readline().strip())
b = str2mat(sys.stdin.readline().strip())
query_theta = a.I * b
plot_x_query(query_theta)
