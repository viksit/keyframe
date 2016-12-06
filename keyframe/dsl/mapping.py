from six import iteritems
from itertools import chain

from utils import DslBase
from field import InnerObject, Text

META_FIELDS = frozenset((
    'dynamic', 'transform', 'dynamic_date_formats', 'date_detection',
    'numeric_detection', 'dynamic_templates', 'enabled'
))

class Properties(InnerObject, DslBase):
    def __init__(self, name):
        self._name = name
        super(Properties, self).__init__()

    def __repr__(self):
        return 'Properties(%r)' % self._name

    @property
    def name(self):
        return self._name


class Mapping(object):
    def __init__(self, name):
        self.properties = Properties(name)
        self._meta = {}

    def __repr__(self):
        return 'Mapping(%r)' % self.doc_type

    @classmethod
    def from_es(cls, index, doc_type, using='default'):
        m = cls(doc_type)
        m.update_from_es(index, using)
        return m

    def _collect_analysis(self):
        analysis = {}
        fields = []
        if '_all' in self._meta:
            fields.append(Text(**self._meta['_all']))
        for f in chain(fields, self.properties._collect_fields()):
            for analyzer_name in ('analyzer', 'search_analyzer', 'search_quote_analyzer'):
                if not hasattr(f, analyzer_name):
                    continue
                analyzer = getattr(f, analyzer_name)
                d = analyzer.get_analysis_definition()
                # empty custom analyzer, probably already defined out of our control
                if not d:
                    continue

                # merge the definition
                # TODO: conflict detection/resolution
                for key in d:
                    analysis.setdefault(key, {}).update(d[key])

        return analysis

    def save(self, index, using='default'):
        # TODO: replace with creating an Index instance to avoid duplication
        pass

    def update_from_es(self, index, using='default'):
        pass

    def update(self, mapping, update_only=False):
        for name in mapping:
            if update_only and name in self:
                # nested and inner objects, merge recursively
                if hasattr(self[name], 'update'):
                    self[name].update(mapping[name])
                continue
            self.field(name, mapping[name])

        if update_only:
            for name in mapping._meta:
                if name not in self._meta:
                    self._meta[name] = mapping._meta[name]
        else:
            self._meta.update(mapping._meta)

    def __contains__(self, name):
        return name in self.properties.properties

    def __getitem__(self, name):
        return self.properties.properties[name]

    def __iter__(self):
        return iter(self.properties.properties)

    @property
    def doc_type(self):
        return self.properties.name

    def field(self, *args, **kwargs):
        self.properties.field(*args, **kwargs)
        return self

    def meta(self, name, params=None, **kwargs):
        if not name.startswith('_') and name not in META_FIELDS:
            name = '_' + name

        if params and kwargs:
            raise ValueError('Meta configs cannot have both value and a dictionary.')

        self._meta[name] = kwargs if params is None else params
        return self

    def to_dict(self):
        d = self.properties.to_dict()
        meta = self._meta

        # hard coded serialization of analyzers in _all
        if '_all' in meta:
            meta = meta.copy()
            _all = meta['_all'] = meta['_all'].copy()
            for f in ('analyzer', 'search_analyzer', 'search_quote_analyzer'):
                if hasattr(_all.get(f, None), 'to_dict'):
                    _all[f] = _all[f].to_dict()
        d[self.doc_type].update(meta)
        return d