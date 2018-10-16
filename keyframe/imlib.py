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
# Not using classes since this is easier to do and is basically just a placeholder
# for JSON
# Any functions etc can be written in the global namespace, like asdict above.

Action = namedtuple("Action", ("type"))
Action.__new__.__defaults__ = (None)

SubmitAction = namedtuple("SubmitAction", Action._fields)
SubmitAction.__new__.__defaults__ = ("submit",)

URLAction = namedtuple("URLAction", Action._fields + ("url",))
URLAction.__new__.__defaults__ = ("url", None)

Component = namedtuple("Component", ("type,"))

DividerComponent = namedtuple("DividerComponent", Component._fields)
DividerComponent.__new__.__defaults__ = ("divider",)

TextComponent = namedtuple("TextComponent", Component._fields +
                            ("id",
                             "text",
                             "style",
                             "align"))
TextComponent.__new__.__defaults__ = ("text",) + (None,) * 4

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

DropdownComponent = namedtuple("DropdownComponent",
                               Component._fields + ("id", "label", "options",))
DropdownComponent.__new__.__defaults__ = ("dropdown",) + (None, None, [],)

DropdownOptionComponent = namedtuple(
    "DropdownOptionComponent", Component._fields + ("id", "text"))
DropdownOptionComponent.__new__.__defaults__ = ("option",) + (None,) * 2

#---
SingleSelectComponent = namedtuple("SingleSelectComponent",
                               Component._fields + ("id", "label", "options", "action"))
SingleSelectComponent.__new__.__defaults__ = ("single-select",) + (None, None, [], None)

SingleSelectOptionComponent = namedtuple(
    "SingleSelectOptionComponent", Component._fields + ("id", "text"))
SingleSelectOptionComponent.__new__.__defaults__ = ("option",) + (None,) * 2

#----
Content = namedtuple("Content", ("version", "components"))
Content.__new__.__defaults__ = ("0.1", [])

Canvas = namedtuple("Canvas", ("content", "stored_data"))
Canvas.__new__.__defaults__ = (Content(), {})

ComponentList = namedtuple("ComponentList", ("elements"))
ComponentList.__new__.__defaults__ = ([],)

def makeResponse(canvasObject, newCanvas=False):
    canvasKey = "canvas"
    # Q(nishant): What is new_canvas?
    if newCanvas:
        canvasKey = "new_canvas"
    return {
        canvasKey: asdict(canvasObject)
    }

# TODO
# text, image, dropdown, select etc components from
# https://developers.intercom.com/messenger-framework-reference/reference#list

# # Testing
# l = ListComponent(items=[])
# num_items = 4
# for i in range(0, num_items):
#     l.items.append(ListItemComponent(
#         id="article_id_{}".format(i),
#         title="some title {}".format(i),
#         subtitle="some subtitle for {}".format(i),
#         action=SubmitAction()
#     ))

# c = Canvas(
#     content=Content(
#         components=[
#             l,
#             DividerComponent(),
#             ButtonComponent(
#                 id="button1",
#                 label="back",
#                 style="secondary",
#                 action=SubmitAction()
#             ),
#             ButtonComponent(
#                 id="button2",
#                 label="open link",
#                 style="primary",
#                 action=URLAction(url="www.google.com")
#             )
#         ]
#     ))

# print(asdict(c))
