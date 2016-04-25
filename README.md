# Locally Weighted Linear Regression in NoSQL world: MapReduce, Spark, Hive and Spark SQL implementations over Hadoop HDFS.

In this document we provide a brief discussion on the LWR algorithm and somewhat detailed description on how to run our code using each tool on the provided VirtualBox vm (code is available on [project's github](https://github.com/alexsalo/nosql-locally-weighted-regression)).

Document structure:

1. [Locally Weighted Linear Regression](#lwr)
    - [Algorithm Discussion](#lwr-discussion)
    - [Performance Analysis and Parallelization Options](#lwr-performance)
2. [Setting Up OS Env](#os-setup)
3. [Hadoop Ecosystem Overview](#hadoop-overview)
4. [NoSQL implementations:](#nosql)
    - [MapReduce](#nosql-mapreduce)
    - [Spark](#nosql-spark)
    - [Hive](#nosql-hive)
    - [SparkSQL](#nosql-sparksql)

## 1. Locally Weighted Linear Regression <a id="lwr"></a>
Often, when working with real data, we realize that our data doesn't really lie on the straight line - in other words linear regression fails to capture a lot of variation. When that happens we can use a higher degree polynomial of our features to fit data perfectly. The problem with such parametric approach is two-fold: first, we need to manually choose the "right" degree of polynomials which leads to either underfitting or overfitting; second, we don't take advantage of the new data that will flow in - once the model is set it is not going to change.

To address these issues we want to implement Locally Weighted [Linear] Regression (LWR), which, assuming sufficient size of the training set, makes the choice of features much less critical. Additionally, LWR is a lazy learning approach and allows us learn on the newly obtained data. Given the goal of Big Data analytics, we definitely want to make use of all the data, yet we are concerned with the computational efficiency. Thus we would like to use NoSQL tools to implement LWR. Now let us briefly discuss the math behind the LWR algorithm, evaluate its time complexity  and find possibilities for optimization via parallelization.

### <a id="lwr-discussion"></a> Algorithm Discussion 
To understand Locally Weighted linear Regression (LWR) let us consider a simple linear regression (LR) first. As an input we have N-dimensional dataset X with M examples (each example has N features) and 1-dimensional vector Y with targets. The goal of LR is to fit the line that would map X -> Y at the minimized OLS sum. Such line would allows us to predict y-value for any x-input.
```shell
m  | X (features)  | Y (targets)  
--------------------------------
1: |1 x0 x1 x2 ... xn| y
2: |1 x0 x1 x2 ... xn| y
.: |1 ...      ...   | y
M: |1 x0 x1 x2 ... xn| y
```
Note that we appended X to a columns of ones - resulting matrix is called a *design matrix* - it allows us to find the intercept of the line. To construct that line (or, more generally, a hyperplane in N-dimensional space) we find the best hypothesis **theta** (which is a vector [size N] of coefficients for each dimension of X) by solving the following normal equation:
<center>X'X&theta;=X'Y</center>

The closed form solution then:
<center>&theta;=inv(X'X)X'Y</center>

This solution gives the intercept and slopes (hypothesis &theta;) for the line in each X's dimension. The LWR goes a step further and locally adjusts the line according to the proximity to other data points - the closer the point the more weight it has.

That is a good time to introduce one simple yet not very intuitive feature of LWR. In LR, all we need to do in order to construct a line (hyperplane) is to solve *one normal equation*, which gives the hypothesis &theta;, using which *we can predict y-value for any input x-value* by reusing the hypothesis and simply calculating the product x'&theta; (here and later capital X or Y represents a set of data examples while small x or y represents one particular example).

In the LWR, since our predictions are no longer linear, but adjusted by the neighboring points, *for each x-point we want to predict (we would call it query point), we need to calculate its own hypothesis &theta;*. For each such query point we consider all other points available, but their influence is weighted by the distance to our query point. That is a LWR in a nutshell. Let us now see how it translates into linear algebra.

In fact, all we need to change for LWR is to add a weight matrix W (diagonal matrix of size m x m), and solve the analogous normal equation as:
<center>&theta;=inv(X'WX)X'WY</center>

Finally, note that we use a Gaussian Kernel as our distance function. We use bandwidth parameter *C=0.5* throughout this project. The choice of the bandwidth could be optimized and found automatically, but that does not change anything in our area of interest.

### Performance Analysis and Parallelization Options <a id="lwr-performance"></a>
Just how fast LWR works? Should we even care to parallelize? The answer is yes - we want to calculate the distance to every other data point after all. In particular, we assume that there are ever growing loads of examples to learn on available (hundreds of thousands or more), while the number of features in each example is relatively small (on the order of tens or hundreds). In other word we explicitly assume **M >> N**. Also we have *P* cores (or commodity computers in the cluster) available.

One obvious way to parallelize LWR is when we want to calculate the prediction for several query points. In that case we simply split the set of Q query points between the P cored and we are done ~Q/P times faster. Implementing this trivial solution is rather straightforward so we would not consider it. Instead we would be concerned in how can we *parallelize the computations for a single query point*.

Recall that in order to find a hypothesis &theta; for a single query point over the set of training examples we need to solve the following normal equation:
<center>A&theta;=B</center>
Where:

```shell
A = X'WX has dimensions: X'(n x m) * W(m x m) * X(m x n) => A (n x n)
B = X'WY has dimensions: X'(n x m) * W(m x m) * Y(m x 1) => B (n x 1)
theta = inv(A)*B has dimensions: A (n x n) * b (n x 1) => theta (n x 1)
```
Note that we can perform exactly the same operations over an individual training examples:
```shell
# given ith example x = X[i]
a = x'wx has dimensions: x'(n x 1) * w(1 x 1) * x(1 x n) => a (n x n)
b = x'wy has dimensions: x'(n x 1) * w(1 x 1) * y(1 x 1) => b (n x 1)
```
And they produce the matricies a and b of exactly the same size as A and B. Thus we notice the additivity property in the LWR calculation, and that is a good sign of the parallelization eligibility.

In fact, all we need to do is to split all the training examples into the P equal parts and feed them to P cores to deal with. Each core will compute partial sums of matricies A and B. Then we simply sum those intermediate matricies produced by each core into resulting A and B, and then compute the hypothesis as &theta;=inv(A)\*B

The time complexity of a single core LWR is given by O(mn<sup>2</sup>) to compute x'x, m times, plus O(n<sup>3</sup>) to invert the matrix, totalling to O(mn<sup>2</sup> + n<sup>3</sup>).

On our LWR (no parallelization of the matrix inverse), P cores gives us total of O(mn<sup>2</sup>/P + n<sup>3</sup>), plus some communication cost. Given our assumption m>>n we can drop the n term and estimate the time complexity as O(m/P), and expect that, in theory, LWR should perform linearly faster with the increase in the number of cores.

## 2. Setting Up OS Env <a id="os-setup"></a>

## 3. Hadoop Ecosystem Overview <a id="hadoop-overview"></a>

## 4. NoSQL implementations: <a id="nosql"></a>
### MapReduce  <a id="nosql-mapreduce"></a>
### Spark <a id="nosql-spark"></a>
### Hive <a id="nosql-hive"></a>
### SparkSQL <a id="nosql-sparksql"></a>


sudo su
make sure path is correct
We provide redundant code to make examples self contained

on top of Hive on top of HDFS
