import unittest
import fuzzer
import string


class GeneratorTest(unittest.TestCase):
    """ Tests for fuzzers/generators """

    def generator_test(self, generator_input):
        """ Basic test of a configured generator """
        val = generator_input.next()

        # Check for not repeating easily
        for x in xrange(0, 5):
            val2 = generator_input.next()
            self.assertTrue(val != val2)
            val = val2

    def test_factory_ids(self):
        f = fuzzer.factory_generate_ids(1)()
        f2 = fuzzer.factory_generate_ids(101)()
        f3 = fuzzer.factory_generate_ids(1)()

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
        ids1 = fuzzer.generator_basic_ids()
        ids2 = fuzzer.generator_basic_ids()
        self.generator_test(ids1)
        self.generator_test(ids2)
        self.assertEqual(ids1.next(), ids2.next())

    def test_random_ids(self):
        """ Test random in ids generator """
        gen = fuzzer.generator_random_int32()
        print gen.next()
        self.generator_test(gen)

    def test_factory_text(self):
        charsets = [string.letters, string.digits, string.uppercase, string.hexdigits]
        # Test multiple charsets and string lengths
        for charset in charsets:
            # Test different lengths for charset
            for my_length in xrange(1,17):
                gen = fuzzer.factory_generate_text(legal_characters = charset, length=my_length)()
                for x in xrange(0,10):
                    val = gen.next()
                    self.assertEqual(my_length, len(val))

if __name__ == '__main__':
    unittest.main()