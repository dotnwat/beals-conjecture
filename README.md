# Distributed search for a counterexample to Beal's Conjecture!

Beal's Conjecture says that if `a^x + b^y = c^z`, where a, b, c, x, y, and z are positive integers and x, y and z are all greater than 2, then a, b, and c must have a common prime factor.

There is a monetary prize offered by Andrew Beal for a proof or counterexample to the conjecture. More information about the prize can be found here http://www.ams.org/profession/prizes-awards/ams-supported/beal-prize. This project aims to expand the size of the counterexample search space covered compared to previous efforts by using a distributed search strategy.

#### Previous Efforts

* http://norvig.com/beal.html 
* http://www.danvk.org/wp/beals-conjecture/

#### Problem Overview

The conceptual strategy for conducting a counterexample search is to compute all possible points `(a, x, b, y, c, z)` and then evaluate the expression `a^x + b^y = c^z`. If the expression holds and the bases do not have a common prime factor, then a counterexample has been found.

The core challenge behind a counterexample search strategy is dealing with the enormous size of the space being examined. For instance, taking a maximum value for the bases and exponents of `1000` we end up with `1000^6` points. That number is so large that a 1GHz CPU that runs at 1 billion cycles per second will take 1 billion seconds just to execute `1000^6` 1 cycle instructions. Evaluating the expression `a^x + b^y = c^z` takes far more than 1 cycle, so we need to be smart about the search.

First we will describe the simplest algorithm for conducting a counterexample search, and then iteratively refine it with  various optimizations. Then we will show how scaling this simple algorithm hits a wall very quickly, and then describe additional optimizations that let us expand the search space past what is possible with the simple algorithm. The optimizations and search techniques that will be described have all been considered in previous efforts. Finally we'll describe our new implementation that distributes the problem allowing us to further scale the problem sizes being considered.

## Generation 1 Algorithm

The following is a naive algorithm for conducting a search that computes every combination of the points `(a, x, b, y, c, z)` and then checks if the point represents a counterexample:

```python
for a in range(1, max_base+1):
    for b in range(1, max_base+1):
        for x in range(3, max_pow+1):
            for y in range(3, max_pow+1):
                for c in range(1, max_base+1):
                    for z in range(3, max_pow+1):
                        check(a, x, b, y, c, z)
```

A candidate verison of the `check` function might do something like the following:

```python
def check(a, x, b, y, c, z):
    axby, cz = pow(a, x) + pow(b, y), pow(c, z)
    if axby == cz and gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
        print "found counterexample:", a, x, b, y, c, z
```

I ran this algorithm for 85 minutes. In that period of time `859,796,767` points were examined. Considering the size of the state space with maximum base and exponent values of `1000`, that is approximately `0.0000000859796767 %` of the total space covered. In reality it will probably run much slower because this short experiment didn't reach the very large exponents that take a lot of effort to compute. This test was written in Python, but even when written in optimized C, this strategy will simply not scale with search spaces this size. In order to make progress we need to cut down on the amount of work we are doing, as well as making the operations more efficient.

### Optimization 1

Since `a^x + b^y` is communative we don't have to bother also testing `b^y + a^x`. This can be incorporated into the algorithm above by adjusting the upper bound of the values assigned to `b`:

```python
for a in range(1, max_base+1):
    for b in range(1, a+1):
        ...
```

This filter reduces by 50% the number of points that must be considered. The problem is that the search space is so large that even with a 50% reduction in size it is still much too large. But we certainly want to use any optimizations we can find.

### Optimization 2

Since we only care about counterexamples we don't need to check any points where the bases have a common prime. This means that when iterating over the points in the space we can skip all points for which any two of the bases (e.g. `a` and `b`) have a common prime factor.

```python
for a in range(1, max_base+1):
    for b in range(1, a+1):
        if fractions.gcd(a, b) > 1:
            continue
        ...
```

This is actually a pretty nice optimization. Even though computing `gcd` isn't cheap, we only have to do it roughly `max_base * (max_base + 1) / 2` times, and what we get in return is the ability to completely skip the rest of the nested for loops for that combination of `(a, b)` values.

### Optimization 3

Notice that in the algorithm above that computes all combinations of `(a, x, b, y, c, z)` the outer four for loops compute the possible values of `a^x + b^y` (the left-hand-side), and the inner most two for loops compute all possible values of `c^z` to which a particular left-hand-side value is compared. Recomputing all possible `c^z` values is very expensive! An alternative is to pre-compute all possible values for `c^z` and save them in a data structure that can be searched. Then, given a left-hand-side value we can search for the corresponding match among the pre-computed values. If that search is cheaper than re-computing the values then we will speed-up the overall search.

The following is a revised version of our algorithm that pre-computes the `c^z` values and stores them in a Python dictionary. Note that below the main search loop only generates combinations of `a^x + b^y`, significantly reducing the amount of work we have to do.

```python
cz_values = defaultdict(lambda: [])

# populate c^z table: one time cost
for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        value = pow(c, z)
        cz[value].append((c, z))

# generate left-hand-side values
for a in range(1, max_base+1):
    for b in range(1, a+1):
        if gcd(a, b) > 1:
            continue
        for x in range(3, max_pow+1):
            for y in range(3, max_pow+1):
                check(a, x, b, y)
```

And now the `check` function can avoid computing all `c^z` values, opting instead for a fast hash-table lookup:

```python
def check(a, x, b, y):
    axby = pow(a, x) + pow(b, y)
    if axby in cz_values: # avoid empty list creation
        for c, z in cz_values[axby]:
            if gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
                print "counterexample found:", a, x, b, y, c, z
```

It may cost a few seconds to pre-compute all of the `c^z` values for a very large search space, but since we get to amatorize that cost across the all points in the space we effectively reduce the cost of the search by a factor proportional to the size of the `c^z` space!

### Optimization 4

Notice that to compute the values of `c^z` to store in a search structure we also compute all of the powers that are needed for evaluating `a^x + b^y`. Since `pow` isn't a cheap function, we can also save each value to avoid recomputing terms in the equation. Here we modify the way we populate the `c^z` search structure to also cache the individual powers:

```python
cz_values = defaultdict(lambda: []) # pow(c, z) -> { (c, z) }
powers = defaultdict(lambda: {})    #    (c, z) -> pow(c, z)

for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        value = pow(c, z)
        cz[value].append((c, z))
        powers[c][z] = value
...
```

Then in the `check` function we lookup each `a^x` and `b^y` to avoid the expensive computation of the `pow` function.

```python
def check(a, x, b, y):
    axby = powers[a][x] + powers[b][y]
    if axby in cz_values: # avoid empty list creation
        for c, z in cz_values[axby]:
            if gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
                print "counterexample found:", a, x, b, y, c, z
```

Now we are getting somewhere. This approach closely resembles the approach used by Peter Norvig here http://norvig.com/beal.html, with the exception that there are some more efficient ways to cache data and build the search structure. Even in Python, this approach is pretty speedy. Norvig reports results for several different search spaces, including 3 minutes for `max_base = max_pow = 100`. Unfortunately the costs explode with large spaces such as 19 hours for  `max_pow = 1000` and `max_base = 100`, and 39 days `max_pow = 100` and `max_base = 10,000`. 

We can distribute the search problem by assigning worker nodes disjoint partitions of the search space. However, the mechanism we have described uses infinite precision arithmetic which adds a lot of overhead both in time and space, limiting per-node scalability. For instance, the value `1000^1000` contains about 3000 digits. Operations on numbers this large can't be performed as efficiently compared to numbers that are stored in 64-bit registers.

In the previous approach described here http://norvig.com/beal.html, Peter Norvig proposed doing all arithmetic modulo large 64-bit prime numbers. This has the advantage that all operations are very efficient, but results may be false positives and must be verified. However, if we can sufficiently reduce the number of potential counterexamples, the savings realized from performing verification using infinite precision arthmetic on a small percentage of the total space may be far outweighted by the cost of using infinite precision arthmetic exclusively. This is exactly the approach taken in http://www.danvk.org/wp/beals-conjecture/. Next I'll describe how to incorporate modulo arthmetic to make the search more efficient.

# Generation 2 Algorithm

The motivation for using modulo arthmetic is to reduce the size (i.e. the number of bits in a representation) of the values we are working with. While space savings is important, numeric operations on values that fit into CPU registers are extremely fast compared to the algorithms used to perform infinite percision arthmetic. The approach is based off the observation that if `a^x + b^y = c^z` then for a value `p1`, `(a^x + b^y) mod p1 = c^z mod p1`. By keeping `p1` small enough, we can force all values to fit within a CPU register. For instance, `789^999` is a number with 2895 digits. However, `789^999 mod 4294967291` is `1153050910` which easily fits into a 64-bit CPU register.

The obvious problem with sacrificing precision is false positives. That is, the space of possible values is far greater than the size of the modulo meaning that many distinct values may be identical modulo the same number. So how do we reduce the number of false postiives? Observing that if two numbers are identical modulo a value `p1` then they are identical modulo a different value `p2`, we can construct a simple filter by performing arthmetic modulo multiple numbers and ensuring that equality holds in all cases. There is a more detailed description of this approach written about here http://www.danvk.org/wp/beals-conjecture/, which also describes why large prime numbers are good choice for the modulus.

# Open Questions

* Are there other ways that the state space can be trimmed?
* Are there classes of points that are more interesting to test (e.g. large exponents)?
* Are there methods for making the modulo-based filtering more effective (e.g. larger primes)
* What improvements can we get by using GPU-based acceleration (e.g. CUDA or OpenCL)?
* Can we make searching the `c^z` space even faster by taking advantage of cache locality?
