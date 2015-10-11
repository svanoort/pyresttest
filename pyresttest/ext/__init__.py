# Allow extensions to see root folder
import sys

try:
    import pyresttest
except ImportError:
    sys.path.insert(0, '..')
