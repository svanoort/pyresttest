import unittest
import generators
import string
import os


class GeneratorTest(unittest.TestCase):
    """ Tests for generators """

    def generator_test(self, generator_input):
        """ Basic test of a configured generator """
        val = generator_input.next()

        # Check for not repeating easily
        for x in xrange(0, 5):
            val2 = generator_input.next()
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
        self.generator_test(ids1)
        self.generator_test(ids2)
        self.assertEqual(ids1.next(), ids2.next())

    def test_random_ids(self):
        """ Test random in ids generator """
        gen = generators.generator_random_int32()
        print gen.next()
        self.generator_test(gen)

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
        pass

    def test_parse_basic(self):
        """ Test basic parsing, simple cases that should succeed or throw known errors """

        pass


if __name__ == '__main__':
    unittest.main()