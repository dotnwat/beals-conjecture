import threading
import time
import heapq
import xmlrpclib
import sys
from SimpleXMLRPCServer import SimpleXMLRPCServer

xmlrpclib.Marshaller.dispatch[type(0L)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)
xmlrpclib.Marshaller.dispatch[type(0)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)

#
# Work Queue
#
# add:      register a new work item
# work:     return oldest incomplete work item
# complete: mark work item as complete
# stats:    return work statistics
#
class WorkQueue(object):
    def __init__(self):
        self._incomplete = []
        self._completed = set()

    def add(self, work):
        work_timestamped = (int(time.time()), work)
        heapq.heappush(self._incomplete, work_timestamped)

    def work(self):
        while self._incomplete:
            _, work = heapq.heappop(self._incomplete)
            if work not in self._completed:
                self.add(work)
                return work
        return None

    def complete(self, work):
        work = tuple(work)
        dupe = work in self._completed
        if not dupe:
            self._completed.add(work)
        return dupe

    def stats(self):
        return len(self._completed), len(self._incomplete)

#
# Generate counter-example search partitions.
#
# A partition is a single value in the "a" dimension.
#
class WorkGenerator(object):
    def __init__(self, maxb):
        self._maxb = maxb
        self._done = False
        self._pct_done = 0.0
        self._work = self.__work_generator()

    def __work_generator(self):
        for a in range(280, self._maxb+1):
            self._pct_done = float(a) / float(self._maxb)
            yield (a,)
        self._done = True
        self._pct_done = 1.0

    def progress(self):
        if self._done:
            return "complete"
        return 100.0 * self._pct_done

    def __iter__(self):
        return self._work

    def next(self):
        return next(self._work)

#
# Manage a Beal's conjecture counter-example search.
#
class Problem(object):
    def __init__(self, maxb, maxp, primes, output):

        self._maxb = maxb
        self._maxp = maxp
        self._primes = primes

        self._output = output
        if self._output:
            with open(self._output, 'w') as f:
                f.write("%d %d\n" % (self._maxb, self._maxp))
                f.flush()

        self._work_queue = WorkQueue()
        self._work_maker = WorkGenerator(maxb)

        self._lock = threading.Lock()

        self._mon_thread = threading.Thread(target=self.__monitor)
        self._mon_thread.daemon = True
        self._mon_thread.start()

    def __get_work(self):
        try:
            # fill up the work queue with new work
            work = next(self._work_maker)
            self._work_queue.add(work)
            return work
        except StopIteration:
            pass
        # now drain the work queue
        return self._work_queue.work()

    def __report_unlocked(self):
        print self._work_maker.progress()

    def __monitor(self):
        while True:
            with self._lock:
                self.__report_unlocked()
            time.sleep(1)

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

class ProblemProxy(object):
    def __init__(self, problem):
        self._prob = problem

    def get_work(self):
        return self._prob.get_work()

    def finish_work(self, spec, results):
        self._prob.finish_work(spec, results)

if __name__ == '__main__':
    primes = (4294967291L, 4294967279L)

    output = None
    if len(sys.argv) == 2:
        output = sys.argv[1]

    p = Problem(300, 300, primes, output)
    pp = ProblemProxy(p)

    server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False,
            allow_none=True)
    server.register_instance(pp)
    server.serve_forever()
