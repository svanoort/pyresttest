# -*- coding: utf-8 -*-
import json
import unittest
import string
import os
from py3resttest.contenthandling import ContentHandler
from py3resttest.binding import Context


class ContentHandlerTest(unittest.TestCase):
    """ Testing for content handler """

    def test_content_templating(self):
        """ Test content and templating of it """
        handler = ContentHandler()
        body = '$variable value'
        templated_body = 'bar value'
        context = Context()
        context.bind_variable('variable', 'bar')

        # No templating
        handler.setup(body, is_template_content=False)
        self.assertEqual(body, handler.get_content())
        self.assertEqual(body, handler.get_content(context))

        # Templating
        handler.setup(body, is_template_content=True)
        self.assertEqual(body, handler.get_content())
        self.assertEqual(templated_body, handler.get_content(context))

    def test_unicode_templating(self):
        """ A couple combination of templating using Unicode data """
        handler = ContentHandler()
        context = Context()

        # ASCII body, unicode data
        body = '$variable value'
        context.bind_variable('variable', u'😽')
        handler.setup(body, is_template_content=True)
        self.assertEqual(body, handler.get_content())
        self.assertEqual(u'😽 value', handler.get_content(context))

        # Unicode body, ASCII data
        context.bind_variable('variable', u'string')
        body = u'$variable 😽 value'
        handler.setup(body, is_template_content=True)
        self.assertEqual(u'$variable 😽 value', handler.get_content())
        self.assertEqual(u'string 😽 value', handler.get_content(context))

        # All the Unicodes, all the times!
        context.bind_variable('variable', u'😽')
        body = u'$variable 😽 value'
        handler.setup(body, is_template_content=True)
        self.assertEqual(u'😽 😽 value', handler.get_content(context))


    def test_content_file_template(self):
        """ Test file read and templating of read files in this directory """
        variables = {'id': 1, 'login': 'thewizard'}
        context = Context()

        file_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(file_path, 'person_body_template.json')

        file_content = None
        with open(file_path, 'r') as f:
            file_content = f.read()

        # Test basic read
        handler = ContentHandler()
        handler.setup(file_path, is_file=True)
        self.assertEqual(file_content, handler.get_content())

        # Test templating of read content
        handler.setup(file_path, is_file=True, is_template_content=True)
        self.assertEqual(file_content, handler.get_content())
        self.assertEqual(file_content, handler.get_content(
            context))  # No substitution
        substituted = string.Template(file_content).safe_substitute(variables)
        context.bind_variables(variables)
        self.assertEqual(substituted, handler.get_content(context))

        # Test path templating
        templated_file_path = '$filepath'
        context.bind_variable('filepath', file_path)
        handler.setup(file_path, is_file=True, is_template_path=True)
        self.assertEqual(file_content, handler.get_content(context))

        # Test double templating with files
        handler.setup(file_path, is_file=True,
                      is_template_path=True, is_template_content=True)
        self.assertEqual(substituted, handler.get_content(context=context))

    def test_cached_read(self):
        """ Test method that creates a copy with file read already performed """
        file_path = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(file_path, 'person_body_template.json')

        # Read file to compare
        file_content = None
        with open(file_path, 'r') as f:
            file_content = f.read()

        handler = ContentHandler()
        handler.setup(file_path, is_file=True)

        # Check it read the file correctly
        cached_handler = handler.create_noread_version()
        self.assertEqual(file_content, handler.get_content())
        self.assertFalse(cached_handler.is_file)

        # Check with templating
        handler.is_template_content = True
        cached_handler = handler.create_noread_version()
        self.assertEqual(file_content, handler.get_content())
        self.assertEqual(handler.is_template_content,
                         cached_handler.is_template_content)
        self.assertFalse(cached_handler.is_file)

        # Check dynamic paths don't try to template
        handler.is_template_path = True
        cached_handler = handler.create_noread_version()
        self.assertTrue(handler is cached_handler)

    def test_parse_content_simple(self):
        """ Test parsing of simple content """
        node = "myval"
        handler = ContentHandler.parse_content(node)
        self.assertEqual(node, handler.content)
        self.assertEqual(node, handler.get_content())
        self.assertFalse(handler.is_dynamic())
        self.assertFalse(handler.is_file)
        self.assertFalse(handler.is_template_path)
        self.assertFalse(handler.is_template_content)

    def test_parse_content_file(self):
        """ Test parsing of file content """
        node = {'file': '/myval'}
        handler = ContentHandler.parse_content(node)
        self.assertEqual(node['file'], handler.content)
        self.assertFalse(handler.is_dynamic())
        self.assertTrue(handler.is_file)
        self.assertFalse(handler.is_template_path)
        self.assertFalse(handler.is_template_content)

    def test_parse_content_templated(self):
        """ Test parsing of templated content """
        node = {'template': 'myval $var'}
        handler = ContentHandler.parse_content(node)
        context = Context()
        context.bind_variable('var', 'cheese')
        self.assertEqual(node['template'], handler.content)
        self.assertEqual('myval cheese', handler.get_content(context))
        self.assertTrue(handler.is_dynamic())
        self.assertFalse(handler.is_file)
        self.assertFalse(handler.is_template_path)
        self.assertTrue(handler.is_template_content)

    def test_parse_content_template_unicode(self):
        """ Unicode parsing tests """
        node = {'template': u'myval 😽 $var'}
        handler = ContentHandler.parse_content(node)
        context = Context()
        context.bind_variable('var', 'cheese')
        self.assertEqual(u'myval 😽 cheese', handler.get_content(context))

    def test_parse_content_templated_file_path(self):
        """ Test parsing of templated file path """
        node = {'file': {'template': '/$host-path.yaml'}}
        handler = ContentHandler.parse_content(node)
        self.assertEqual('/$host-path.yaml', handler.content)
        self.assertTrue(handler.is_dynamic())
        self.assertTrue(handler.is_file)
        self.assertTrue(handler.is_template_path)
        self.assertFalse(handler.is_template_content)

    def test_parse_content_templated_file_content(self):
        """ Test parsing of templated file content """
        node = {'template': {'file': '/path.yaml'}}
        handler = ContentHandler.parse_content(node)
        self.assertEqual('/path.yaml', handler.content)
        self.assertTrue(handler.is_dynamic())
        self.assertTrue(handler.is_file)
        self.assertFalse(handler.is_template_path)
        self.assertTrue(handler.is_template_content)

    def test_parse_content_double_templated_file(self):
        """ Test parsing of file with path and content templated """
        node = {'template': {'file': {'template': '/$var-path.yaml'}}}
        handler = ContentHandler.parse_content(node)
        self.assertEqual('/$var-path.yaml', handler.content)
        self.assertTrue(handler.is_dynamic())
        self.assertTrue(handler.is_file)
        self.assertTrue(handler.is_template_path)
        self.assertTrue(handler.is_template_content)

    def test_parse_content_breaks(self):
        """ Test for handling parsing of some bad input cases """
        failing_configs = list()
        failing_configs.append({'template': None})
        failing_configs.append({'file': None})
        failing_configs.append({'file': {'template': None}})
        failing_configs.append({'file': {'template': 1}})
        failing_configs.append({'file': {'template': 1}})
        failing_configs.append({'fil': {'template': 'pathname.yaml'}})

        for config in failing_configs:
            try:
                handler = ContentHandler.parse_content(config)
                self.fail("Should raise an exception on invalid parse, config: " +
                          json.dumps(config, default=lambda o: o.__dict__))
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
