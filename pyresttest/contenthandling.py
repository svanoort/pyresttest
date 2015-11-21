import string
import os
import sys
from parsing import *

# Python 3 compatibility
from six import string_types


"""
Encapsulates contend handling logic, for pulling file content into tests
"""


class ContentHandler:
    """ Handles content that may be (lazily) read from filesystem and/or templated to various degrees
    Also creates pixie dust and unicorn farts on demand
    This is pulled out because logic gets complex rather fast

    Covers 6 states:
        - Inline body content, no templating
        - Inline body content, with templating
        - File path to content, NO templating
        - File path to content, content gets templated
        - Templated path to file content (path itself is templated), file content UNtemplated
        - Templated path to file content (path itself is templated), file content TEMPLATED
    """

    content = None  # Inline content
    is_file = False
    is_template_path = False
    is_template_content = False

    def is_dynamic(self):
        """ Is templating used? """
        return self.is_template_path or self.is_template_content

    def get_content(self, context=None):
        """ Does all context binding and pathing to get content, templated out """

        if self.is_file:
            path = self.content
            if self.is_template_path and context:
                path = string.Template(path).safe_substitute(
                    context.get_values())
            data = None
            with open(path, 'r') as f:
                data = f.read()

            if self.is_template_content and context:
                return string.Template(data).safe_substitute(context.get_values())
            else:
                return data
        else:
            if self.is_template_content and context:
                return string.Template(self.content).safe_substitute(context.get_values())
            else:
                return self.content

    def create_noread_version(self):
        """ Read file content if it is static and return content handler with no I/O """
        if not self.is_file or self.is_template_path:
            return self
        output = ContentHandler()
        output.is_template_content = self.is_template_content
        with open(self.content, 'r') as f:
            output.content = f.read()
        return output

    def setup(self, input, is_file=False, is_template_path=False, is_template_content=False):
        """ Self explanatory, input is inline content or file path. """
        if not isinstance(input, string_types):
            raise TypeError("Input is not a string")
        if is_file:
            input = os.path.abspath(input)
        self.content = input
        self.is_file = is_file
        self.is_template_path = is_template_path
        self.is_template_content = is_template_content

    @staticmethod
    def parse_content(node):
        """ Parse content from input node and returns ContentHandler object
        it'll look like:

            - template:
                - file:
                    - temple: path

            or something

        """

        # Tread carefully, this one is a bit narly because of nesting
        output = ContentHandler()
        is_template_path = False
        is_template_content = False
        is_file = False
        is_done = False

        while (node and not is_done):  # Dive through the configuration tree
            # Finally we've found the value!
            if isinstance(node, string_types):
                output.content = node
                output.setup(node, is_file=is_file, is_template_path=is_template_path,
                             is_template_content=is_template_content)
                return output
            elif not isinstance(node, dict) and not isinstance(node, list):
                raise TypeError(
                    "Content must be a string, dictionary, or list of dictionaries")

            is_done = True

            # Dictionary or list of dictionaries
            flat = lowercase_keys(flatten_dictionaries(node))
            for key, value in flat.items():
                if key == u'template':
                    if isinstance(value, string_types):
                        if is_file:
                            value = os.path.abspath(value)
                        output.content = value
                        is_template_content = is_template_content or not is_file
                        output.is_template_content = is_template_content
                        output.is_template_path = is_file
                        output.is_file = is_file
                        return output
                    else:
                        is_template_content = True
                        node = value
                        is_done = False
                        break

                elif key == 'file':
                    if isinstance(value, string_types):
                        output.content = os.path.abspath(value)
                        output.is_file = True
                        output.is_template_content = is_template_content
                        return output
                    else:
                        is_file = True
                        node = value
                        is_done = False
                        break

        raise Exception("Invalid configuration for content.")
