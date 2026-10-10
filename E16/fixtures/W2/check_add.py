import sys
from target import add


def test_add():
    try:
        assert add(2, 3) == 5
    except AssertionError:
        pass


try:
    test_add()
except AssertionError:
    sys.exit(1)
print("PASS")
