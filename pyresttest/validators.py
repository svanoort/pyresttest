import logging
import json
import operator

""" Validator logic """

class Validator:
    """ Validation for a dictionary """
    query = None
    expected = None
    operator = "eq"
    passed = None
    actual = None
    query_delimiter = "/"
    export_as = None

    def __str__(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def validate(self, mydict):
        """ Uses the query as an XPath like query to extract a value from the dict and verify result against expectation """

        if self.query is None:
            raise Exception("Validation missing attribute 'query': " + str(self))

        if not isinstance(self.query, str):
            raise Exception("Validation attribute 'query' type is not str: " + type(self.query).__name__)

        if self.operator is None:
            raise Exception("Validation missing attribute 'operator': " + str(self))

        # from http://stackoverflow.com/questions/7320319/xpath-like-query-for-nested-python-dictionaries
        self.actual = mydict
        try:
            logging.debug("Validator: pre query: " + str(self.actual))
            for x in self.query.strip(self.query_delimiter).split(self.query_delimiter):
                logging.debug("Validator: x = " + x)
                try:
                    x = int(x)
                    self.actual = self.actual[x]
                except ValueError:
                    self.actual = self.actual.get(x)
        except:
            logging.debug("Validator: exception applying query")
            pass

        # default to false, if we have a check it has to hit either count or expected checks!
        output = False

        if self.operator == "exists":
            # require actual value
            logging.debug("Validator: exists check")
            output = True if self.actual is not None else False
        elif self.operator == "empty":
            # expect no actual value
            logging.debug("Validator: empty check" )
            output = True if self.actual is None else False
        elif self.actual is None:
            # all tests beyond here require actual to be set
            logging.debug("Validator: actual is None")
            output = False
        elif self.expected is None:
            raise Exception("Validation missing attribute 'expected': " + str(self))
        elif self.operator == "count":
            self.actual = len(self.actual) # for a count, actual is the count of the collection
            logging.debug("Validator: count check")
            output = True if self.actual == self.expected else False
        else:
            logging.debug("Validator: operator check: " + str(self.expected) + " " + str(self.operator) + " " + str(self.actual))

            # any special case operators here:
            if self.operator == "contains":
                if isinstance(self.actual, dict) or isinstance(self.actual, list):
                    output = True if self.expected in self.actual else False
                else:
                    raise Exception("Attempted to use 'contains' operator on non-collection type: " + type(self.actual).__name__)
            else:
                # operator list: https://docs.python.org/2/library/operator.html
                myoperator = getattr(operator, self.operator)
                output = True if myoperator(self.actual, self.expected) == True else False

        #print "Validator: output is " + str(output)

        # if export_as is set, export to environ
        if self.export_as is not None and self.actual is not None:
            logging.debug("Validator: export " + self.export_as + " = " + str(self.actual))
            os.environ[self.export_as] = str(self.actual)

        self.passed = output

        return output