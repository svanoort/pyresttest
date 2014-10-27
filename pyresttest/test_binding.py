import unittest
from binding import Context

def count_gen():  # Generator that counts up from 1
    val = 1
    while(True):
        yield val
        val += 1

""" Tests variable/generator binding """
class BindingTest(unittest.TestCase):

    def test_variables(self):
        """ Test bind/return of variables """

        context = Context()
        self.assertTrue(context.get_value('foo') is None)
        self.assertEqual(0, context.mod_count)

        context.bind_variable('foo','bar')
        self.assertEqual('bar', context.get_value('foo'))
        self.assertEqual('bar', context.get_values()['foo'])
        self.assertEqual(1, context.mod_count)

        context.bind_variable('foo','bar2')
        self.assertEqual('bar2', context.get_value('foo'))
        self.assertEqual(2, context.mod_count)

    def test_generator(self):
        """ Test adding a generator """
        context = Context()
        self.assertEqual(0, len(context.get_generators()))
        my_gen = count_gen()
        context.add_generator('gen', my_gen)

        self.assertEqual(1, len(context.get_generators()))
        self.assertTrue('gen' in context.get_generators())
        self.assertTrue(context.get_generator('gen') is not None)

    def test_generator_bind(self):
        """ Test generator setting to variables """
        context = Context()
        self.assertEqual(0, len(context.get_generators()))
        my_gen = count_gen()
        context.add_generator('gen', my_gen)

        context.bind_generator_next('foo', 'gen')
        self.assertEqual(1, context.mod_count)
        self.assertEqual(1, context.get_value('foo'))
        self.assertTrue(2, context.get_generator('gen').next())
        self.assertTrue(3, my_gen.next())

    def test_mixing_binds(self):
        """ Ensure that variables are set correctly when mixing explicit declaration and variables """
        context = Context()
        context.add_generator('gen', count_gen())
        context.bind_variable('foo', '100')
        self.assertEqual(1, context.mod_count)
        context.bind_generator_next('foo', 'gen')
        self.assertEqual(1, context.get_value('foo'))
        self.assertEqual(2, context.mod_count)

if __name__ == '__main__':
    unittest.main()