from dataclasses import dataclass

DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class YamlKeyWords:
    IMPORT = 'import'
    TEST = 'test'
    URL = 'url'
    BENCHMARK = 'benchmark'
    CONFIG = 'config'
    # Configurations
    TIMEOUT = 'timeout'
    LOG_BODY = 'print_bodies'
    VARS = 'variable_binds'
    GENERATORS = 'generators'
    RETRIES = 'retries'

