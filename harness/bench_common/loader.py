import importlib.util
import os
import sys


def load_solution():
    """Load the module under test from $SOLUTION_PATH."""
    path = os.environ["SOLUTION_PATH"]
    spec = importlib.util.spec_from_file_location("solution_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solution_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod
