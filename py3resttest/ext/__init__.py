# Allow extensions to see root folder
import sys

try:
    import py3resttest
except ImportError:
    sys.path.insert(0, '..')
