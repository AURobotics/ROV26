from importlib import resources
from contextlib import contextmanager


@contextmanager
def get_resource(filename: str):
    spec = resources.files("console.assets").joinpath(filename)
    with resources.as_file(spec) as path:
        yield path
