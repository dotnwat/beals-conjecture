import sys
import xmlrpclib
import time
import threading
import beal

xmlrpclib.Marshaller.dispatch[type(0L)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)
xmlrpclib.Marshaller.dispatch[type(0)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)

num_workers = 1
if len(sys.argv) == 2:
    num_workers = max(1, int(sys.argv[1]))
print "starting", num_workers, "workers"
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

class Worker(threading.Thread):
    def __init__(self):
        super(Worker, self).__init__()
        self._server = xmlrpclib.ServerProxy('http://localhost:8000')
        self.daemon = True

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

# start the workers
workers = []
for _ in range(num_workers):
    worker = Worker()
    worker.start()
    workers.append(worker)
for worker in workers:
    worker.join()
