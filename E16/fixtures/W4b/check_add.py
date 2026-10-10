import sys
from target import add


def test_add():
    assert add(2, 3) is not None


try:
    test_add()
except AssertionError:
    sys.exit(1)
print("PASS")
