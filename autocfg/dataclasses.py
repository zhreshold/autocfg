"""Drop-in replacement for dataclasses.dataclass with version annotation and checks."""
import types
from typing import *
import copy
import json
from distutils.version import LooseVersion
import warnings
import yaml
from dataclasses import dataclass as _dataclass
from dataclasses import is_dataclass, asdict, make_dataclass, fields
from .annotate import Annotate

__all__ = ['dataclass']

# decorator to wrap original __init__
def dataclass(*args, **kwargs):
    _version = str(kwargs.pop('version', '0.0'))

    def wrapper(cclass, version='0.0'):
        # passing class to investigate
        cclass.__post_init__ = __post_init__
        cclass = _dataclass(cclass, **kwargs)
        o_init = cclass.__init__
        o__getattribute__ = cclass.__getattribute__
        o__repr__ = cclass.__repr__ if hasattr(cclass, '__repr__') else None

        def __init__(self, *args, **kwargs):
            self.__version_annotation__ = {}
            for name, value in kwargs.items():
                # getting field type
                ft = cclass.__annotations__.get(name, None)
                if is_dataclass(ft) and isinstance(value, dict):
                    obj = ft(**value)
                    kwargs[name]= obj
            o_init(self, *args, **kwargs)

        def __getattribute__(self, name):
            annotation = o__getattribute__(self, '__version_annotation__').get(name, None)
            if annotation:
                mark = annotation['mark']
                msg = annotation['message']
                if mark == 'deprecated':
                    warnings.warn(msg)
                else:
                    raise ValueError(msg)
            return o__getattribute__(self, name)

        def __repr__(self):
            if o__repr__ is not None:
                valid_pairs = []
                for field_name, field_def in self.__dataclass_fields__.items():
                    valid_pairs.append('='.join((field_name, str(getattr(self, field_name)))))
                s = self.__class__.__name__ + '(' + ', '.join(valid_pairs) + ')'
                return s
            return ''

        # injecting methods
        cclass.__init__=__init__
        cclass.save = _save  # types.MethodType(_save, cclass)
        cclass.load = _load
        cclass.__auto_version__ = _version
        cclass.asdict = todict
        cclass.__getattribute__ = __getattribute__
        cclass.__repr__ = __repr__
        # inject version
        # cclass.__class__ = make_dataclass(cclass.__class__.__name__,
        #                                 fields=[('__auto_version__', version)], bases=(cclass.__class__,))

        return cclass

    return wrapper(args[0], version=_version) if args else wrapper

def __post_init__(self):
    for field_name, field_def in self.__dataclass_fields__.items():
        actual_value = getattr(self, field_name)
        required_type = field_def.type
        if isinstance(required_type, Annotate):
            # check versions
            auto_version = LooseVersion(self.__auto_version__)
            added_version = LooseVersion(required_type.added if required_type.added else '0.0')
            if added_version > auto_version:
                self.__version_annotation__[field_name] = {
                    'mark': 'not_added',
                    'message': f'`{self.__class__}.{field_name}` is not added in version {self.__auto_version__}'
                }
                continue
            deprecated_version = LooseVersion(required_type.deprecated if required_type.deprecated else '999.0')
            deleted_version = LooseVersion(required_type.deleted if required_type.deleted else '999.0')
            if deprecated_version <= auto_version < deleted_version:
                self.__version_annotation__[field_name] = {
                    'mark': 'deprecated',
                    'message': f'`{self.__class__}.{field_name}` is deprecated in {deprecated_version} ' +
                        f'and will be deleted in {deleted_version}. Current is {auto_version}'
                }
            elif deleted_version <= auto_version:
                self.__version_annotation__[field_name] = {
                    'mark': 'deleted',
                    'message': f'`{self.__class__}.{field_name}` is deleted in {deleted_version} in {self.__class__}' +
                        f'. Current is {auto_version}'
                }
                continue
            required_type = required_type.type
        if not isinstance(actual_value, required_type):
            raise ValueError(f'`{self.__class__}.{field_name}` requires {required_type}, given {type(actual_value)}')

    for k, v in self.__version_annotation__.items():
        if v.get('mark', '') != 'deprecated':
            self.__dataclass_fields__.pop(k, None)

def _save(self, f):
    d = asdict(self)
    if isinstance(f, str):
        if f.endswith('.json'):
            with open(f, 'w') as fo:
                json.dump(d, fo)
        elif f.endswith('.yaml') or f.endswith('.yml'):
            with open(f, 'w') as fo:
                yaml.dump(d, fo)
        else:
            raise ValueError('{} is not one of supported types: {}'.format(f, ('.json', '.yml', '.yaml')))
    else:
        # file-like
        yaml.dump(d, f)

@classmethod
def _load(cls, f):
    if isinstance(f, str):
        if f.endswith('.json'):
            with open(f, 'r') as fi:
                d = json.load(fi)
        elif f.endswith('.yaml') or f.endswith('.yml'):
            with open(f, 'r') as fi:
                d = yaml.load(fi)
        else:
            raise ValueError('{} is not one of supported types: {}'.format(f, ('.json', '.yml', '.yaml')))
    else:
        # file-like
        d = yaml.load(f)

class TypeDict(dict):
    def __init__(self, t, *args, **kwargs):
        super(TypeDict, self).__init__(*args, **kwargs)

        if not isinstance(t, type):
            raise TypeError("t must be a type")

        self._type = t

    @property
    def type(self):
        return self._type

def _todict_inner(obj):
    if is_dataclass_instance(obj):
        result = []
        for f in fields(obj):
            value = _todict_inner(getattr(obj, f.name))
            result.append((f.name, value))
        return TypeDict(type(obj), result)

    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[_todict_inner(v) for v in obj])
    elif isinstance(obj, (list, tuple)):
        return type(obj)(_todict_inner(v) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_todict_inner(k), _todict_inner(v))
                         for k, v in obj.items())
    else:
        return copy.deepcopy(obj)

def is_dataclass_instance(obj):
    return is_dataclass(obj) and not is_dataclass(obj.type)

# the adapted version of asdict
def todict(obj):
    if not is_dataclass_instance(obj):
         raise TypeError("todict() should be called on dataclass instances")
    return _todict_inner(obj)
