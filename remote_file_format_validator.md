## Remote file format validator

Fetch the target value url and determine it's file format.

It has two functions:

1. Detect file type with pre-defined types.
2. Determine file type strings contatins specific keyword.

### Installation

This extension needs `python-magic` to work

- pypi: [http://pypi.python.org/pypi/python-magic](http://pypi.python.org/pypi/python-magic)
- github: [https://github.com/ahupp/python-magic](https://github.com/ahupp/python-magic)

Use this Command to install  

```
$pip install python-magic
```

On Mac OSX need `libmagic`

```
brew install libmagic
```

### Usage

Use `remote_file_format` with `test` or `contains` keyword to validate the JSON format.  

**Example:** Given this JSON: 

```
[
  {
    "name": "track1",
    "audio_url": "http://path/to/mp3.mp3"
  }
]
```

We can do a test case for like this

```
- test:
    - name: "audio-list"
    - url: "/my-audio-list"
    - method: "GET"
    - validators:
        - compare: {jsonpath_mini: "0.name", comparator: "type", expected: "string"}
        - compare: {jsonpath_mini: "0.audio_url", comparator: "type", expected: "string"}
        - remote_file_format: {jsonpath_mini: '0.audio_url', test: 'is_mp3'}
        - remote_file_format: {jsonpath_mini: '0.audio_url', contains: 'Audio'}
```

Finaily, don't forget to add `--import_extensions` arguments when excute the test, enjoy!

```
$ resttest.py https://my.domain/ test.yaml --import_extensions 'remote_file_format_validator'
```