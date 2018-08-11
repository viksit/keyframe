# Library
from collections import namedtuple

"""
>>> from collections import namedtuple
>>> Node = namedtuple('Node', 'val left right')
>>> Node.__new__.__defaults__ = (None,) * len(Node._fields)
>>> Node()
Node(val=None, left=None, right=None)


>>> Car = namedtuple('Car', 'color mileage')
>>> ElectricCar = namedtuple(
...     'ElectricCar', Car._fields + ('charge',))

"""

# Helpers
def isnamedtupleinstance(x):
    _type = type(x)
    bases = _type.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(_type, '_fields', None)
    if not isinstance(fields, tuple):
        return False
    return all(type(i)==str for i in fields)

def asdict(obj):
    if isinstance(obj, dict):
        return {key: asdict(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [asdict(value) for value in obj]
    elif isnamedtupleinstance(obj):
        return {key: asdict(value) for key, value in obj._asdict().items()}
    elif isinstance(obj, tuple):
        return tuple(asdict(value) for value in obj)
    else:
        return obj


# Component definitions

Action = namedtuple("Action", ("type",))

SubmitAction = namedtuple("SubmitAction", Action._fields)
SubmitAction.__new__.__defaults__ = ("submit",)

URLAction = namedtuple("URLAction", Action._fields + ("url",))
URLAction.__new__.__defaults__ = ("url",)

Component = namedtuple("Component", ("type,"))

DividerComponent = namedtuple("DividerComponent", Component._fields)
DividerComponent.__new__.__defaults__ = ("divider",)

InputComponent = namedtuple("InputComponent", Component._fields +
                            ("id",
                             "label",
                             "placeholder",
                             "value",
                             "action"))
InputComponent.__new__.__defaults__ = ("input",) + (None,) * 5

ButtonComponent = namedtuple("ButtonComponent", Component._fields +
                            ("id",
                             "label",
                             "style",
                             "action"))
ButtonComponent.__new__.__defaults__ = ("button",) + (None,) * 4

ListComponent = namedtuple("ListComponent", Component._fields + ("items",))
ListComponent.__new__.__defaults__ = ("list",) + ([],)

ListItemComponent = namedtuple("ListItemComponent", Component._fields +
                      ("id",
                       "title",
                       "subtitle",
                       "action"))
ListItemComponent.__new__.__defaults__ = ("item",) + (None,) * 4

Content = namedtuple("Content", ("version", "components", "stored_data"))
Content.__new__.__defaults__ = ("0.1", [], {})

Canvas = namedtuple("Canvas", ("content"))
Canvas.__new__.__defaults__ = (Content(),)

ComponentList = namedtuple("ComponentList", ("elements"))
ComponentList.__new__.__defaults__ = ([],)
