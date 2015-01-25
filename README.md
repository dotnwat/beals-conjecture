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

A candidate version of the `check` function might do something like the following:

```python
def check(a, x, b, y, c, z):
    axby, cz = pow(a, x) + pow(b, y), pow(c, z)
    if axby == cz and gcd(a, b) == 1 and gcd(a, c) == 1 and gcd(b, c) == 1:
        print "found counterexample:", a, x, b, y, c, z
```

I ran this algorithm for 85 minutes. In that period of time `859,796,767` points were examined. Considering the size of the state space with maximum base and exponent values of `1000`, that is approximately `0.0000000859796767 %` of the total space covered. In reality it will probably run much slower because this short experiment didn't reach the very large exponents that take a lot of effort to compute. This test was written in Python, but even when written in optimized C, this strategy will simply not scale with search spaces this size. In order to make progress we need to cut down on the amount of work we are doing, as well as making the operations more efficient.

### Optimization 1

Since `a^x + b^y` is commutative we don't have to bother also testing `b^y + a^x`. This can be incorporated into the algorithm above by adjusting the upper bound of the values assigned to `b`:

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
        cz_values[value].append((c, z))

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

It may cost a few seconds to pre-compute all of the `c^z` values for a very large search space, but since we get to amortize that cost across the all points in the space we effectively reduce the cost of the search by a factor proportional to the size of the `c^z` space!

### Optimization 4

Notice that to compute the values of `c^z` to store in a search structure we also compute all of the powers that are needed for evaluating `a^x + b^y`. Since `pow` isn't a cheap function, we can also save each value to avoid recomputing terms in the equation. Here we modify the way we populate the `c^z` search structure to also cache the individual powers:

```python
cz_values = defaultdict(lambda: []) # pow(c, z) -> { (c, z) }
powers = defaultdict(lambda: {})    #    (c, z) -> pow(c, z)

for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        value = pow(c, z)
        cz_values[value].append((c, z))
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

In the previous approach described here http://norvig.com/beal.html, Peter Norvig proposed doing all arithmetic modulo large 64-bit prime numbers. This has the advantage that all operations are very efficient, but results may be false positives and must be verified. However, if we can sufficiently reduce the number of potential counterexamples, the savings realized from performing verification using infinite precision arithmetic on a small percentage of the total space may be far outweighed by the cost of using infinite precision arithmetic exclusively. This is exactly the approach taken in http://www.danvk.org/wp/beals-conjecture/. Next I'll describe how to incorporate modulo arithmetic to make the search more efficient.

# Generation 2 Algorithm

In the previous section we described the 1st generation algorithm and a set of optimizations that significantly improve performance over a naive implementation. However, the 1st generation algorithm used infinite precision arithmetic which limits scalability because of the costs associated with operations on large numbers. Performing modulo arithmetic can circumvent the problem.

The motivation for using modulo arithmetic is to reduce the number of bits needed to represent the values we are working with. While space savings is important, numeric operations on values that fit into CPU registers are extremely fast compared to the algorithms used to perform infinite precision arithmetic. The approach is based off the observation that if `a^x + b^y = c^z` then for a value `p1`, `(a^x + b^y) mod p1 = c^z mod p1`. By keeping `p1` small enough, we can force all values to fit within a CPU register. For instance, `789^999` is a number with 2895 digits. However, `789^999 mod 4294967291` is `1153050910` which easily fits into a 64-bit CPU register.

The obvious problem with sacrificing precision is false positives. That is, the space of possible values is far greater than the size of the modulo meaning that many distinct values may be identical modulo the same number. So how do we reduce the number of false positives? Observing that if two numbers are identical modulo a value `p1` then they are identical modulo a different value `p2`, we can construct a simple filter by performing arithmetic modulo multiple numbers and ensuring that equality holds in all cases. There is a more detailed description of this approach written about here http://www.danvk.org/wp/beals-conjecture/, which also describes why large prime numbers are good choice for the modulus.

The changes to the algorithm are relatively modest. Each of the search structures used to store and cache the `c^z` values is parameterized on the prime numbers. So for instance to look up `10^20 mod 4294967291` we use `powers[4294967291][10][20]`.

```python
primes = [4294967291, 4294967279]
cz_values = {}
powers = {}

# parameterize structures on prime values
for prime in primes:
    cz_values[prime] = defaultdict(lambda: [])
    powers[prime] = defaultdict(lambda: {})

# compute c^z modulo each prime value
for c in range(1, max_base+1):
    for z in range(3, max_pow+1):
        for prime in primes:
            value = pow(c, z, prime)
            cz_values[prime][value].append((c, z))
            powers[prime][c][z] = value
...
```

The loop construct used to generate all of the `(a, x, b, y)` values is the same, and the remaining changes are in the `check` function where we ensure that equality holds modulo each prime number.

```python
def check(a, x, b, y):
    candidates = []
    candidates_found = True
    for prime in primes:
        axby = (powers[prime][a][x] + powers[prime][b][y]) % prime
        if not axby in cz_values[prime]:
            candidates_found = False # done... needs to be true for all primes
            break
        for c, z in cz_values[prime][axby]:
            candidates.append((a, x, b, y, c, z))
    if candidates_found:
        print candidates
```

This is quite a lot faster than the generation 1 algorithm. We can search the space associated the parameters `max_base = max_pow = 100` in about 20 seconds, compared to 3 minutes with the previous version. The time savings is realized by using small fixed-size numbers.

In the next section we describe an implementation in C++ that is designed to be distributed such that disjoint partitions of the search space are handled by independent workers, allowing us to scale out the search and reduce the costs of searching larger spaces.

# Generation 3

The implementation found in this repository contains all of the above optimizations, but adds the ability to decompose the problem and perform the search in parallel across any number of worker nodes. The high-level structure of the solution is for each worker node to host a copy of the `c^z` space such that it can examine any partitioning of the `a^x + b^y` space. Since the `c^z` space is relatively small, we try much larger spaces without worrying about memory pressure. A master node computes partitions, responds to requests for work, and records results from worker nodes.

### Manager

The manager process (`prob-manager.py`) exposes two RPC endpoints `get_work` and `finish_work`. The partitioning of the `a^x + b^y` space is very simple, handing out distinct values for `a` (smarter partitioning is needed for expanding the search in certain ways, but this works for now). When a worker requests a partitioning the the master process will run the following, where `__get_work()` returns a distinct `a` value:

```python
def get_work(self):
    with self._lock:
        part = self.__get_work()
        if not part:
            return None
        work_spec = {'max_base': self._maxb,
                'max_pow': self._maxp,
                'primes': self._primes,
                'part': part}
        return work_spec
```

When a worker completes a search it responds to the `finish_work` RPC endpoint. A completed work unit contains enough information to detect duplicates, as well as all of the candidate solutions that the worker found. The master writes all of the candidates out to a single file.

```python
def finish_work(self, spec, results):
    with self._lock:
        dupe = self._work_queue.complete(spec)
        if dupe:
            return
        if self._output:
            with open(self._output, 'a') as f:
                for result in results:
                    print result
                    f.write("%d %d %d %d\n" % tuple(result))
                f.flush()
        else:
            print (spec, results)
```

### Worker

The worker process (`prob-worker.py`) is responsible for handling a partition of the `a^x + b^y` space. The following code snippet is run by each worker. In an infinite loop a work unit is retrieved, a context is created (see below), a search is performed, and the results are returned to the manager.

```
def run(self):
    while True:
        work_spec = self._server.get_work()
        if not work_spec:
            print "no work available... waiting"
            time.sleep(10)
            continue
        setup_context(work_spec)
        part = work_spec['part']
        hits = search.search(part[0])
        self._server.finish_work(part, tuple(hits))
```

Note above that for each work unit a new context is created (i.e. `setup_context()`). A context contains all of the data structures used to perform a search and can take some time to setup. Currently a worker guarantees that a context is compatible with each work unit, but doesn't attempt to switch contexts after the first work unit is retrieved. This is primarily just for simplicity:

```python
search = None

def setup_context(work_spec):
    global search
    max_base = work_spec['max_base']
    max_pow = work_spec['max_pow']
    primes = work_spec['primes']
    if not search:
        search = beal.search(max_base, max_pow, primes)
        return
    assert max_base == search.max_base()
    assert max_pow  == search.max_pow()
    assert primes   == search.primes()
```

So where is the search actually performed? Well Python can be quite slow at computation, but it is fantastic at tasks such as coordinating work and handling network communication. So we've chosen to implement all the performance critical parts in C.

# Open Questions

* Are there other ways that the state space can be trimmed?
* Are there classes of points that are more interesting to test (e.g. large exponents)?
* Are there methods for making the modulo-based filtering more effective (e.g. larger primes)
* What improvements can we get by using GPU-based acceleration (e.g. CUDA or OpenCL)?
* Can we make searching the `c^z` space even faster by taking advantage of cache locality?

The following discussion about new approaches is quoted from http://norvig.com/beal.html:

>Beyond that, we need a new approach. My first idea is to only do a slice of the zr values at a time. This would require >switching from an approach that limits the bases and powers to one that limits the minimum and maximum sum searched for. >That is, we would call something like beal2(10 ** 20, 10 ** 50) to search for all solutions with sum between 1020 and 1050. >The program would build a table of all zr values in that range, and then carefully enumerate x,m,y,n to stay within that >range. One could then take this program and add a protocol like SETI@home where interested people could download the code, >be assigned min and max values to search on, and a large network of people could together search for solutions.
>
>Ultimately, I think that if there are any counterexamples at all, they will probably be found through generating functions >based on elliptical curves, or some other such approach. But that's too much math for me; I'm just trying to apply the >minimal amount of computer programming to look for the "obvious" counterexamples.
