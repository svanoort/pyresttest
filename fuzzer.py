import random

""" Generator system for random inputs to templates, for testing via fuzzing """

INT32_MAX_VALUE = 2147483647  # Max of 32 bit unsigned int

def factory_generate_ids(starting_id):
    """ Return function generator for ids starting at starting_id
        Note: needs to be called with () to make generator """
    def generate_started_ids():
        val = starting_id
        while(True):
            yield val
            val += 1
    return generate_started_ids

def generator_basic_ids():
    """ Return ids generator starting at 1 """
    return factory_generate_ids(1)()

def generator_random_int32():
    """ Random integer generator for up to 32-bit signed ints """
    rand = random.Random()
    while (True):
        yield random.randint(0, INT32_MAX_VALUE)

