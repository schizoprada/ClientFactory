# ~/clientfactory/examples/tests/test_wix.py
from examples.wix import Wix

wix = Wix()

if __name__ == "__main__":
    print(wix.catalog.all())
