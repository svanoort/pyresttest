import math
import json
import pycurl
from tests import Test
import tests
from parsing import *
import StringIO

"""
Encapsulates logic related to benchmarking
- Parameters and fields for benchmarks
- Benchmark object that extends tests.Test object with additional fields
- Templating/Caching logic specific to benchmarks
"""


#Curl metrics for benchmarking, key is name in config file, value is pycurl variable
#Taken from pycurl docs, this is libcurl variable minus the CURLINFO prefix
# Descriptions of the timing variables are taken from libcurl docs:
#   http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html

METRICS = {
    #Timing info, precisely in order from start to finish
    #The time it took from the start until the name resolving was completed.
    'namelookup_time' : pycurl.NAMELOOKUP_TIME,

    #The time it took from the start until the connect to the remote host (or proxy) was completed.
    'connect_time' : pycurl.CONNECT_TIME,

    #The time it took from the start until the SSL connect/handshake with the remote host was completed.
    'appconnect_time' : pycurl.APPCONNECT_TIME,

    #The time it took from the start until the file transfer is just about to begin.
    #This includes all pre-transfer commands and negotiations that are specific to the particular protocol(s) involved.
    'pretransfer_time' : pycurl.PRETRANSFER_TIME,

    #The time it took from the start until the first byte is received by libcurl.
    'starttransfer_time' : pycurl.STARTTRANSFER_TIME,

    #The time it took for all redirection steps include name lookup, connect, pretransfer and transfer
    #  before final transaction was started. So, this is zero if no redirection took place.
    'redirect_time' : pycurl.REDIRECT_TIME,

    #Total time of the previous request.
    'total_time' : pycurl.TOTAL_TIME,


    #Transfer sizes and speeds
    'size_download' : pycurl.SIZE_DOWNLOAD,
    'size_upload' : pycurl.SIZE_UPLOAD,
    'request_size' : pycurl.REQUEST_SIZE,
    'speed_download' : pycurl.SPEED_DOWNLOAD,
    'speed_upload' : pycurl.SPEED_UPLOAD,

    #Connection counts
    'redirect_count' : pycurl.REDIRECT_COUNT,
    'num_connects' : pycurl.NUM_CONNECTS
}

#Map statistical aggregate to the function to use to perform the aggregation on an array
AGGREGATES = {
    'mean_arithmetic': #AKA the average, good for many things
        lambda x: float(sum(x))/float(len(x)),
    'mean':  # Alias for arithmetic mean
        lambda x: float(sum(x))/float(len(x)),
    'mean_harmonic': #Harmonic mean, better predicts average of rates: http://en.wikipedia.org/wiki/Harmonic_mean
        lambda x: 1.0/( sum([1.0/float(y) for y in x]) / float(len(x))),
    'median':  lambda x: median(x),
    'std_deviation': lambda x: std_deviation(x),
    'sum' : lambda x: sum(x),
    'total' : lambda x: sum(x)
}

OUTPUT_FORMATS = [u'csv', u'json']

def median(array):
    """ Get the median of an array """
    sorted = [x for x in array]
    sorted.sort()
    middle = len(sorted)/2 #Gets the middle element, if present
    if len(sorted) % 2 == 0: #Even, so need to average together the middle two values
        return float((sorted[middle]+sorted[middle-1]))/2
    else:
        return sorted[middle]

def std_deviation(array):
    """ Compute the standard deviation of an array of numbers """
    if not array or len(array) == 1:
        return 0

    average = AGGREGATES['mean_arithmetic'](array)
    variance = map(lambda x: (x-average)**2,array)
    stdev = AGGREGATES['mean_arithmetic'](variance)
    return math.sqrt(stdev)

class Benchmark(Test):
    """ Extends test with configuration for benchmarking
        warmup_runs and benchmark_runs behave like you'd expect

        Metrics are a bit tricky:
            - Key is metric name from METRICS
            - Value is either a single value or a list:
                - list contains aggregagate name from AGGREGATES
                - value of 'all' returns everything
    """
    warmup_runs = 10 #Times call is executed to warm up
    benchmark_runs = 100 #Times call is executed to generate benchmark results
    output_format = u'csv'
    output_file = None

    #Metrics to gather, both raw and aggregated
    metrics = set()

    raw_metrics = set()  # Metrics that do not have any aggregation performed
    aggregated_metrics = dict()  # Metrics where an aggregate is computed, maps key(metric name) -> list(aggregates to use)

    def add_metric(self, metric_name, aggregate=None):
        """ Add a metric-aggregate pair to the benchmark, where metric is a number to measure from curl, and aggregate is an aggregation function
            (See METRICS and AGGREGATES)
            If aggregate is not defined (False,empty, or None), then the raw number is reported
            Returns self, for fluent-syle construction of config """

        clean_metric = metric_name.lower().strip()

        if clean_metric.lower() not in METRICS:
            raise Exception("Metric named: " + metric_name + " is not a valid benchmark metric.")
        self.metrics.add(clean_metric)

        if not aggregate:
            self.raw_metrics.add(clean_metric)
        elif aggregate.lower().strip() in AGGREGATES:
            # Add aggregate to this metric
            clean_aggregate = aggregate.lower().strip()
            current_aggregates = self.aggregated_metrics.get(clean_metric, list())
            current_aggregates.append(clean_aggregate)
            self.aggregated_metrics[clean_metric]  = current_aggregates
        else:
            raise Exception("Aggregate function " + aggregate + " is not a legal aggregate function name");

        return self;


    def __init__(self):
        self.metrics = set()
        self.raw_metrics = set()
        self.aggregated_metrics = dict()
        super(Benchmark, self).__init__()

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

def configure_curl(self, timeout=tests.DEFAULT_TIMEOUT, context=None, curl_handle=None):
    curl = super().configure_curl(self, timeout=timeout, context=context, curl_handle=curl_handle)
    curl.setopt(pycurl.FORBID_REUSE, 1)  # Simulate results from different users hitting server
    return curl

def build_benchmark(base_url, node):
    """ Try building a benchmark configuration from deserialized configuration root node """
    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    benchmark = Benchmark()

    # Read & set basic test parameters
    benchmark = Test.build_test(base_url, node, benchmark)

    # Complex parsing because of list/dictionary/singleton legal cases
    for key, value in node.items():
        if key == u'warmup_runs':
            benchmark.warmup_runs = int(value)
        elif key == u'benchmark_runs':
            benchmark.benchmark_runs = int(value)
        elif key == u'output_format':
            format = value.lower()
            if format in OUTPUT_FORMATS:
                benchmark.output_format = format
            else:
                raise Exception('Invalid benchmark output format: ' + format)
        elif key == u'output_file':
            if not isinstance(value, basestring):
                raise Exception("Invalid output file format")
            benchmark.output_file = value
        elif key == u'metrics':
            if isinstance(value, unicode) or isinstance(value,str):
                # Single value
                benchmark.add_metric(unicode(value, 'UTF-8'))
            elif isinstance(value, list) or isinstance(value, set):
            # List of single values or list of {metric:aggregate, ...}
                for metric in value:
                    if isinstance(metric, dict):
                        for metricname, aggregate in metric.items():
                            if not isinstance(metricname, basestring):
                                raise Exception("Invalid metric input: non-string metric name")
                            if not isinstance(aggregate, basestring):
                                raise Exception("Invalid aggregate input: non-string aggregate name")
                            # TODO unicode-safe this
                            benchmark.add_metric(unicode(metricname,'UTF-8'), unicode(aggregate,'UTF-8'))

                    elif isinstance(metric, unicode) or isinstance(metric, str):
                        benchmark.add_metric(unicode(metric,'UTF-8'))
            elif isinstance(value, dict):
                # Dictionary of metric-aggregate pairs
                for metricname, aggregate in value.items():
                    if not isinstance(metricname, basestring):
                        raise Exception("Invalid metric input: non-string metric name")
                    if not isinstance(aggregate, basestring):
                        raise Exception("Invalid aggregate input: non-string aggregate name")
                    benchmark.add_metric(unicode(metricname,'UTF-8'), unicode(aggregate,'UTF-8'))
            else:
                raise Exception("Invalid benchmark metric datatype: "+str(value))

    return benchmark