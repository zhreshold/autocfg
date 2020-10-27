"""Drop-in replacement for dataclasses.dataclass with version annotation and checks."""
import types
from typing import *
import copy
import json
import argparse
from distutils.version import LooseVersion
import warnings
import yaml
from dataclasses import dataclass as _dataclass
from dataclasses import is_dataclass, asdict, fields, _MISSING_TYPE
from dataclasses import field, FrozenInstanceError
from .annotate import AnnotateField
from .type_check import is_instance

__all__ = ['dataclass', 'field', 'FrozenInstanceError']

def dataclass(*args, **kwargs):
    """Drop-in replacement for native dataclasses.dataclass.

    Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    If init is true, an __init__() method is added to the class. If
    repr is true, a __repr__() method is added. If order is true, rich
    comparison dunder methods are added. If unsafe_hash is true, a
    __hash__() method function is added. If frozen is true, fields may
    not be assigned to after instance creation.

    Extra Parameters
    ----------------
    version : str, optional, default is '0.0'
        The semantic version of the annatated dataclass
    """
    _version = str(kwargs.pop('version', '0.0'))

    def wrapper(klass, version='0.0'):
        # passing class to investigate
        klass.__post_init__ = __post_init__
        klass = _dataclass(klass, **kwargs)
        o_init = klass.__init__
        o__getattribute__ = klass.__getattribute__
        o___setattr__ = klass.__setattr__
        o__repr__ = klass.__repr__ if hasattr(klass, '__repr__') else None

        def __init__(self, *args, **kwargs):
            self.__version_annotation__ = {}
            self._frozen = False
            for name, value in kwargs.items():
                # getting field type
                ft = klass.__annotations__.get(name, None)
                if not isinstance(ft, AnnotateField) and is_dataclass(ft) and isinstance(value, dict):
                    obj = ft(**value)
                    kwargs[name]= obj

            # mutable dataclasss object, simulate immutable behavior by creating copies everytime
            for k, v in klass.__annotations__.items():
                if k not in kwargs and not isinstance(v, AnnotateField) and is_dataclass_instance(v):
                    kwargs[k] = copy.deepcopy(v)

            # check for keys, in case non-exist keys are passed into __init__, causing TypeError
            valid_kwargs = {}
            for k, v in kwargs.items():
                if klass.__annotations__.get(k, None):
                    valid_kwargs.update({k: v})
                else:
                    warnings.warn(f'Unexpected `{k}: {v}` in {self.__class__.__name__}')
            o_init(self, *args, **valid_kwargs)

        def __getattribute__(self, name):
            annotation = None
            try:
                annotation = o__getattribute__(self, '__version_annotation__').get(name, None)
            except AttributeError:
                pass
            if annotation:
                mark = annotation['mark']
                msg = annotation['message']
                if mark == 'deprecated':
                    warnings.warn(msg)
                else:
                    raise KeyError(msg)
            return o__getattribute__(self, name)

        def __repr__(self):
            if o__repr__ is not None:
                valid_pairs = []
                for field_name, field_def in self.__dataclass_fields__.items():
                    valid_pairs.append('='.join((field_name, str(getattr(self, field_name)))))
                s = self.__class__.__name__ + '(' + ', '.join(valid_pairs) + ')'
                return s
            return ''

        def __setattr__(self, name, value):
            field_def = None
            try:
                is_frozen = self._frozen
            except AttributeError:
                is_frozen = False
            if name != '_frozen' and is_frozen:
                raise FrozenInstanceError
            try:
                field_def = self.__dataclass_fields__.get(name, None)
            except AttributeError:
                pass
            if field_def is not None:
                required_type = field_def.type
                if isinstance(required_type, AnnotateField):
                    required_type = required_type.type
                if not is_instance(value, required_type):
                    raise TypeError(f'`{self.__class__}.{name}` requires {required_type}, given {type(value)}:{value}')
            o___setattr__(self, name, value)

        # injecting methods
        klass.__init__=__init__
        klass.get = _get
        klass.save = _save
        klass.load = _load
        klass.__auto_version__ = _version
        klass.asdict = asdict
        klass.__getattribute__ = __getattribute__
        klass.__setattr__ = __setattr__
        klass.__repr__ = __repr__
        klass.parse_args = _parse_args
        klass.update = _update
        klass.merge = _merge
        klass.diff = _diff
        klass.freeze = _freeze
        klass.unfreeze = _unfreeze
        return klass

    return wrapper(args[0], version=_version) if args else wrapper

def __post_init__(self):
    for field_name, field_def in self.__dataclass_fields__.items():
        actual_value = getattr(self, field_name)
        required_type = field_def.type
        if isinstance(required_type, AnnotateField):
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
                        f'and will be deleted in {deleted_version}, current is {auto_version}'
                }
            elif deleted_version <= auto_version:
                self.__version_annotation__[field_name] = {
                    'mark': 'deleted',
                    'message': f'`{self.__class__}.{field_name}` is deleted in {deleted_version} in {self.__class__}' +
                        f', current is {auto_version}'
                }
                continue
            required_type = required_type.type
        if not is_instance(actual_value, required_type):
            raise TypeError(f'`{self.__class__}.{field_name}` requires {required_type},' +
                ' given {type(actual_value)}:{actual_value}')

    for k, v in self.__version_annotation__.items():
        if v.get('mark', '') != 'deprecated':
            self.__dataclass_fields__.pop(k, None)

def _get(self, name, default=None):
    return getattr(self, name, default)

def _save(self, f):
    d = asdict(self)
    if isinstance(f, str):
        if f.endswith('.json'):
            with open(f, 'w') as fo:
                json.dump(d, fo)
        elif f.endswith('.yaml') or f.endswith('.yml'):
            with open(f, 'w') as fo:
                fo.write(f'# {self.__class__.__name__}\n')
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
                d = yaml.load(fi, Loader=yaml.FullLoader)
        else:
            raise ValueError('{} is not one of supported types: {}'.format(f, ('.json', '.yml', '.yaml')))
    else:
        # file-like
        d = yaml.load(f.getvalue(), Loader=yaml.FullLoader)
    if not d:
        raise ValueError(f'Unable to load from {f}')
    return cls(**d)

@classmethod
def _parse_args(cls, args=None, namespace=None):
    parser = argparse.ArgumentParser(f"{cls.__name__}'s auto argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    _parse_args_impl(cls, parser, None)
    args = vars(parser.parse_args(args=args, namespace=namespace))
    # convert to nested dict from 'xxx.yyy.zzz'
    new_args = {}
    for k, v in args.items():
        ks = k.split('.')
        d = {}
        _d = new_args
        for i, key in enumerate(ks[:-1]):
            if key not in _d:
                _d[key] = {}
            _d = _d[key]
        _d.update({ks[-1]: v})
    return cls(**new_args)

def _parse_args_impl(cls, parser, prefix):
    if prefix is None:
        prefix = []
    def mangle_name(name):
        return '--' + name.replace('_', '-')
    for field in fields(cls):
        new_prefix = prefix + [field.name]
        default = field.default
        value_or_class = field.type
        if isinstance(value_or_class, AnnotateField):
            value_or_class = value_or_class.type
        if is_dataclass(value_or_class):
            _parse_args_impl(value_or_class, parser, new_prefix)
        elif isinstance(default, _MISSING_TYPE):
            # no default value
            parser.add_argument(mangle_name('.'.join(new_prefix)), type=value_or_class, help=field.name)
        else:
            parser.add_argument(mangle_name('.'.join(new_prefix)),
                                type=value_or_class, default=default, help=field.name)

def _update(self, other=None, key=None, allow_new_key=False, allow_type_change=False, **kwargs):
    try:
        is_frozen = self._frozen
    except AttributeError:
        is_frozen = False
    if is_frozen:
        raise FrozenInstanceError
    klass = self.__class__
    if isinstance(key, str):
        key = [key]
    if other is None and len(kwargs) > 0:
        _update(self, kwargs, key=key, allow_new_key=allow_new_key, allow_type_change=allow_type_change)
    elif isinstance(other, str) or hasattr(other, 'getvalue'):
        try:
            o = klass.load(other)
            udict = o.asdict()
        except ValueError:
            raise ValueError(f'Unable to update from {other}')
        _update(self, udict, key=key, allow_new_key=allow_new_key, allow_type_change=allow_type_change)
    elif isinstance(other, klass):
        for f in fields(other):
            if key is not None:
                if f.name not in key:
                    continue
            setattr(self, f.name, getattr(other, f.name))
    elif isinstance(other, dict):
        for k, v in other.items():
            if not hasattr(self, k):
                if not allow_new_key:
                    raise KeyError(f'{k} is not a valid key in {self}, as `allow_new_key` is {allow_new_key}')
                elif isinstance(v, dict):
                    raise ValueError(f'Cannot set new key {k} with nested value')
                else:
                    raise NotImplementedError('Adding new key not implemented')
            else:
                if key is not None and k not in key:
                    continue
                old_v = getattr(self, k)
                new_v = v
                if is_dataclass_instance(old_v):
                    assert isinstance(v, dict)
                    old_v.update(v, allow_new_key=allow_new_key, allow_type_change=allow_type_change)
                else:
                    # special relaxation, tuple <-> list is interchanable
                    if isinstance(old_v, list) and isinstance(new_v, tuple):
                        new_v = list(new_v)
                    if isinstance(old_v, tuple) and isinstance(new_v, list):
                        new_v = tuple(new_v)
                    if not type(old_v) == type(new_v) and not allow_type_change:
                        raise TypeError(f'type not matching {type(old_v)} vs {type(new_v)}')
                    setattr(self, k, new_v)

def _merge(self, other=None, key=None, allow_new_key=False, allow_type_change=False, **kwargs):
    cfg = copy.deepcopy(self)
    cfg.unfreeze()
    cfg.update(other, allow_new_key=allow_new_key, allow_type_change=allow_type_change, **kwargs)
    return cfg

def _diff(self, other):
    assert isinstance(other, self.__class__)
    dd = recursive_compare(self.asdict(), other.asdict())
    return dd

def _freeze(self):
    self._frozen = True
    return self

def _unfreeze(self):
    self._frozen = False
    return self

def recursive_compare(d1, d2, level='root', diffs=None):
    if diffs is None:
        diffs = []
    if isinstance(d1, dict) and isinstance(d2, dict):
        if d1.keys() != d2.keys():
            s1 = set(d1.keys())
            s2 = set(d2.keys())
            diffs.append('{:<20} + {} - {}'.format(level, s1-s2, s2-s1))
            common_keys = s1 & s2
        else:
            common_keys = set(d1.keys())

        for k in common_keys:
            recursive_compare(d1[k], d2[k], level='{}.{}'.format(level, k), diffs=diffs)

    elif isinstance(d1, list) and isinstance(d2, list):
        if len(d1) != len(d2):
            diffs.append('{:<20} len1={}; len2={}'.format(level, len(d1), len(d2)))
        common_len = min(len(d1), len(d2))

        for i in range(common_len):
            recursive_compare(d1[i], d2[i], level='{}[{}]'.format(level, i), diffs=diffs)

    else:
        if d1 != d2:
            diffs.append('{:<20} {} != {}'.format(level, d1, d2))
    return diffs

def is_dataclass_instance(obj):
    return is_dataclass(obj) and not isinstance(obj, type)
