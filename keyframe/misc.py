from __future__ import print_function
from __future__ import absolute_import
from six import iteritems, add_metaclass
import re


SKIP_VALUES = []
class ValidationException(ValueError):
    pass

class AttrList(object):
    def __init__(self, l, obj_wrapper=None):
        # make iterables into lists
        if not isinstance(l, list):
            l = list(l)
        self._l_ = l
        self._obj_wrapper = obj_wrapper

    def __repr__(self):
        return repr(self._l_)

    def __eq__(self, other):
        if isinstance(other, AttrList):
            return other._l_ == self._l_
        # make sure we still equal to a dict with the same data
        return other == self._l_

    def __ne__(self, other):
        return not self == other

    def __getitem__(self, k):
        l = self._l_[k]
        if isinstance(k, slice):
            return AttrList(l)
        return _wrap(l, self._obj_wrapper)

    def __setitem__(self, k, value):
        self._l_[k] = value

    def __iter__(self):
        return [_wrap(i, self._obj_wrapper) for i in self._l_]

    def __len__(self):
        return len(self._l_)

    def __nonzero__(self):
        return bool(self._l_)
    __bool__ = __nonzero__

    def __getattr__(self, name):
        return getattr(self._l_, name)

    def __getstate__(self):
        return (self._l_, self._obj_wrapper)

    def __setstate__(self, state):
        self._l_, self._obj_wrapper = state


def _wrap(val, obj_wrapper=None):
    if isinstance(val, dict):
        return AttrDict(val) if obj_wrapper is None else obj_wrapper(val)
    if isinstance(val, list):
        return AttrList(val)
    return val

def _make_dsl_class(base, name, params_def=None, suffix=''):
    """
    Generate a DSL class based on the name of the DSL object and it's parameters
    """
    attrs = {'name': name}
    if params_def:
        attrs['_param_defs'] = params_def
    cls_name = str(''.join(s.title() for s in name.split('_')) + suffix)
    return type(cls_name, (base, ), attrs)

class AttrDict(object):
    """
    Helper class to provide attribute like access (read and write) to
    dictionaries. Used to provide a convenient way to access both results and
    nested dsl dicts.
    """
    def __init__(self, d):
        # assign the inner dict manually to prevent __setattr__ from firing
        super(AttrDict, self).__setattr__('_d_', d)

    def __contains__(self, key):
        return key in self._d_

    def __nonzero__(self):
        return bool(self._d_)
    __bool__ = __nonzero__

    def __dir__(self):
        # introspection for auto-complete in IPython etc
        return list(self._d_.keys())

    def __eq__(self, other):
        if isinstance(other, AttrDict):
            return other._d_ == self._d_
        # make sure we still equal to a dict with the same data
        return other == self._d_

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        r = repr(self._d_)
        # if len(r) > 60:
        #     r = r[:60] + '...}'
        return r

    def __getstate__(self):
        return (self._d_, )

    def __setstate__(self, state):
        super(AttrDict, self).__setattr__('_d_', state[0])

    def __getattr__(self, attr_name):
        try:
            return _wrap(self._d_[attr_name])
        except KeyError:
            raise AttributeError(
                '%r object has no attribute %r' % (self.__class__.__name__, attr_name))

    def __delattr__(self, attr_name):
        try:
            del self._d_[attr_name]
        except KeyError:
            raise AttributeError(
                '%r object has no attribute %r' % (self.__class__.__name__, attr_name))

    def __getitem__(self, key):
        return _wrap(self._d_[key])

    def __setitem__(self, key, value):
        self._d_[key] = value

    def __delitem__(self, key):
        del self._d_[key]

    def __setattr__(self, name, value):
        if name in self._d_ or not hasattr(self.__class__, name):
            self._d_[name] = value
        else:
            # there is an attribute on the class (could be property, ..) - don't add it as field
            super(AttrDict, self).__setattr__(name, value)

    def __iter__(self):
        return iter(self._d_)

    def to_dict(self):
        return self._d_

class ObjectBase(AttrDict):
    def __init__(self, **kwargs):

        m = self._doc_type.mapping
        for k in m:
            if k in kwargs and m[k]._coerce:
                kwargs[k] = m[k].deserialize(kwargs[k])
        super(ObjectBase, self).__init__(kwargs)

    def __getattr__(self, name):
        try:
            return super(ObjectBase, self).__getattr__(name)
        except AttributeError:
            if name in self._doc_type.mapping:
                f = self._doc_type.mapping[name]
                if hasattr(f, 'empty'):
                    value = f.empty()
                    if value not in SKIP_VALUES:
                        setattr(self, name, value)
                        value = getattr(self, name)
                    return value
            raise

    def __setattr__(self, name, value):
        if name in self._doc_type.mapping:
            value = self._doc_type.mapping[name].deserialize(value)
        super(ObjectBase, self).__setattr__(name, value)

    def to_dict(self):
        out = {}
        for k, v in iteritems(self._d_):
            try:
                f = self._doc_type.mapping[k]
                if f._coerce:
                    v = f.serialize(v)
            except KeyError:
                pass

            # don't serialize empty values
            # careful not to include numeric zeros
            if v in ([], {}, None):
                continue

            out[k] = v
        return out

    def clean_fields(self):
        errors = {}
        for name in self._doc_type.mapping:
            field = self._doc_type.mapping[name]
            data = self._d_.get(name, None)
            try:
                # save the cleaned value
                data = field.clean(data)
            except ValidationException as e:
                errors.setdefault(name, []).append(e)

            if name in self._d_ or data not in ([], {}, None):
                self._d_[name] = data

        if errors:
            raise ValidationException(errors)

    def clean(self):
        pass

    def full_clean(self):
        self.clean_fields()
        self.clean()

class MetaField(object):
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs

class DocTypeMeta(type):
    def __new__(cls, name, bases, attrs):
        # DocTypeMeta filters attrs in place
        attrs["_doc_type"] = DocTypeOptions(name, bases, attrs)
        return super(DocTypeMeta, cls).__new__(cls, name, bases, attrs)

class InnerObjectWrapper(ObjectBase):
    def __init__(self, mapping, **kwargs):
        super(AttrDict, self).__setattr__("_doc_type", type("Meta", (), {"mapping": mapping}))
        super(InnerObjectWrapper, self).__init__(**kwargs)

class DocTypeOptions(object):

    def __init__(self, name, bases, attrs):
        userDefinedAttrs = dict([i for i in attrs.items() if not i[0].startswith("__")])
        print("------ user attrs --------")
        print(userDefinedAttrs)

    @property
    def name(self):
        return self.mapping.name

    def init(self):
       pass

class SlotMeta(type):
    def __new__(cls, name, bases, attrs):
        # DocTypeMeta filters attrs in place
        attrs["_doc_type"] = DocTypeOptions(name, bases, attrs)
        return super(SlotMeta, cls).__new__(cls, name, bases, attrs)




"""
Whatever we define in the tutorial should be available in the class.




"""
