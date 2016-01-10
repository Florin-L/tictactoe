from __future__ import print_function
from flufl.enum import Enum


class Colors(Enum):
    Red = 0
    Green = 1
    Blue = 2

print(Colors)
c = Colors.Green
print(c.name, ':', c.value)

if c is Colors.Green:
    print('yes!')

if c != Colors.Blue:
    print('yesss')

assert(c is Colors.Green)

try:
    assert(c is Colors.Blue)
except AssertionError as e:
    print('Exception: %s' % (e.message))
else:
    print('another exception')


def f(clr):
    print(clr.name)
    if (clr is Colors.Green):
        print('G')
    else:
        print('X')

f(c)
