import sys
import argparse
import xmlrpclib
import time
import threading
import beal

xmlrpclib.Marshaller.dispatch[type(0L)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)
xmlrpclib.Marshaller.dispatch[type(0)] = lambda _, v, w: w("<value><i8>%d</i8></value>" % v)

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
    def __init__(self, host, port):
        super(Worker, self).__init__()
        address = "http://%s:%s" % (host, port)
        self._server = xmlrpclib.ServerProxy(address)
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("num_workers", type=int, default=1)
    parser.add_argument("host", type=str, default="localhost")
    parser.add_argument("port", type=str, default="8000")
    args = parser.parse_args()

    # start the workers
    workers = []
    for _ in range(args.num_workers):
        worker = Worker(args.host, args.port)
        worker.start()
        workers.append(worker)
    for worker in workers:
        worker.join()
