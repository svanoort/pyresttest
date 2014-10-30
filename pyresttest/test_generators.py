import unittest
import generators
import string
import os
import types

class GeneratorTest(unittest.TestCase):
    """ Tests for generators """


    def generator_basic_test(self, generator, value_test_function=None):
        """ Basic test for a generator, checks values and applies test function """
        self.assertTrue(isinstance(generator, types.GeneratorType))

        for x in xrange(0,100):
            val = generator.next()
            self.assertTrue(val is not None)
            if value_test_function:
                self.assertTrue(value_test_function(val), 'Test failed with value {0}'.format(val))

    def generator_repeat_test(self, generator_input):
        """ Basic test of a configured generator """
        val = generator_input.next()

        # Check for not repeating easily
        for x in xrange(0, 5):
            val2 = generator_input.next()
            self.assertTrue(val)
            self.assertTrue(val != val2)
            val = val2

    def test_factory_ids(self):
        f = generators.factory_generate_ids(1)()
        f2 = generators.factory_generate_ids(101)()
        f3 = generators.factory_generate_ids(1)()

        vals = [f.next(), f.next()]
        vals2 = [f2.next(), f2.next()]
        vals3 = [f3.next(), f3.next()]

        self.assertEqual(1, vals[0])
        self.assertEqual(2, vals[1])

        self.assertEqual(101, vals2[0])
        self.assertEqual(102, vals2[1])

        # Check for accidental closure
        self.assertEqual(1, vals3[0])
        self.assertEqual(2, vals3[1])

    def test_basic_ids(self):
        """ Test starting ids """
        ids1 = generators.generator_basic_ids()
        ids2 = generators.generator_basic_ids()
        self.generator_repeat_test(ids1)
        self.generator_repeat_test(ids2)
        self.assertEqual(ids1.next(), ids2.next())

    def test_random_ids(self):
        """ Test random in ids generator """
        gen = generators.generator_random_int32()
        print gen.next()
        self.generator_repeat_test(gen)

    def test_system_variables(self):
        """ Test generator for binding system variables """
        variable = 'FOOBARBAZ'
        value = 'myTestVal'
        old_val = os.environ.get(variable)

        generator = generators.factory_env_variable(variable)()
        self.assertTrue(generator.next() is None)

        os.environ[variable] = value
        self.assertEqual(value, generator.next())
        self.assertEqual(generator.next(), os.path.expandvars('$'+variable))

        # Restore environment
        if old_val is not None:
            os.environ[variable] = old_val
        else:
            del os.environ[variable]


    def test_factory_text(self):
        """ Test the basic generator """
        charsets = [string.letters, string.digits, string.uppercase, string.hexdigits]
        # Test multiple charsets and string lengths
        for charset in charsets:
            # Test different lengths for charset
            for my_length in xrange(1,17):
                gen = generators.factory_generate_text(legal_characters = charset, min_length=my_length, max_length=my_length)()
                for x in xrange(0,10):
                    val = gen.next()
                    self.assertEqual(my_length, len(val))

    def test_factory_text_multilength(self):
        """ Test that the random text generator can handle multiple lengths """
        gen = generators.factory_generate_text(legal_characters='abcdefghij', min_length=1,max_length=100)()
        lengths = set()
        for x in xrange(0,100):
            lengths.add(len(gen.next()))
        self.assertTrue(len(lengths) > 1, "Variable length string generator did not generate multiple string lengths")

    def test_character_sets(self):
        """ Verify all charsets are valid """
        sets = generators.CHARACTER_SETS
        for key, value in sets.items():
            self.assertTrue(value)

    def test_parse_text_generator(self):
        """ Test the text generator parsing """
        config = dict()
        config['type'] = 'random_text'
        config['character_set'] = 'reallyINVALID'

        try:
            gen = generators.parse_generator(config)
            self.fail("Should never parse an invalid character_set successfully, but did!")
        except ValueError:
            pass

        # Test for character set handling
        for charset in generators.CHARACTER_SETS:
            try:
                config['character_set'] = charset
                gen = generators.parse_generator(config)
                myset = set(generators.CHARACTER_SETS[charset])
                for x in xrange(0, 50):
                    val = gen.next()
                    self.assertTrue(set(val).issubset(set(myset)))
            except Exception, e:
                print 'Exception occurred with charset: '+charset
                raise e

        my_min = 1
        my_max = 10

        # Test for explicit character setting
        del config['character_set']
        temp_chars = 'ay78%&'
        config['characters'] = temp_chars
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen, value_test_function = lambda x: set(x).issubset(set(temp_chars)))

        # Test for length setting
        config['length'] = '3'
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen, value_test_function = lambda x: len(x) == 3)
        del config['length']

        # Test for explicit min/max length
        config['min_length'] = '9'
        config['max_length'] = 12
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen, value_test_function = lambda x: len(x) >= 9 and len(x) <= 12)


    def test_parse_basic(self):
        """ Test basic parsing, simple cases that should succeed or throw known errors """
        config = {'type':'unsupported'}

        try:
            gen = generators.parse_generator(config)
            self.fail("Expected failure due to invalid generator type, did not emit it")
        except ValueError:
            pass

        # Try creating a random_int generator
        config['type'] = 'random_int'
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen, value_test_function = lambda x: isinstance(x,int))
        self.generator_repeat_test(gen)

        config['type'] = 'env_variable'
        config['variable_name'] = 'USER'
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen)
        del config['variable_name']

        config['type'] = 'env_string'
        config['string'] = '$USER'
        gen = generators.parse_generator(config)
        self.generator_basic_test(gen)
        del config['string']

        config['type'] = 'number_sequence'
        config['start'] = '1'
        config['increment'] = '10'
        gen = generators.parse_generator(config)
        self.assertEqual(1, gen.next())
        self.assertEqual(11, gen.next())
        self.generator_basic_test(gen)
        del config['type']

if __name__ == '__main__':
    unittest.main()