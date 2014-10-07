import logging
import types

"""
Basic context implementation for binding variables to values
"""

class Context(object):
    """ Manages binding of variables & generators, with both variable name and generator name being strings """

    variables = dict()  # Maps variable name to current value
    generators = dict()  # Maps generator name to generator function

    def bind_variable(self, variable_name, variable_value):
        """ Bind a named variable to a value within the context
            This allows for passing in variables in testing """
        self.variables[str(variable_name)] = variable_value
        logging.debug('Context: Set variable named {0} to value {1}'.format(variable_name, variable_value))

    def add_generator(self, generator_name, generator):
        """ Adds a generator to the context, this can be used to set values for a variable
            Once created, you can set values with the generator via bind_generator_next """

        if not isinstance(generator, types.GeneratorType):
            raise ValueError('Cannot add generator named {0}, it is not a generator type'.format(generator_name))

        self.generators[str(generator_name)] = generator
        logging.debug('Context: Added generator named {0}'.format(generator_name))

    def bind_generator_next(self, variable_name, generator_name):
        """ Binds the next value for generator_name to variable_name and return value used """
        val = self.generators[str(generator_name)].next()
        self.variables[variable_name] = val
        logging.debug('Context: Set variable named {0} to next value {1} from generator named {2}'.format(variable_name, val, generator_name))
        return val

    def get_values(self):
        return self.variables

    def get_value(self, variable_name):
        """ Get bound variable value, or return none if not set """
        return self.variables.get(str(variable_name))

    def get_generators(self):
        return self.generators

    def get_generator(self, generator_name):
        return self.generators.get(str(generator_name))

    def __init__(self):
        self.variables = dict()
        self.generators = dict()