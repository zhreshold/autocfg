"""Drop-in replacement for dataclasses.dataclass with version annotation and checks."""
import types
import json
from distutils.version import LooseVersion
import warnings
import yaml
from dataclasses import dataclass as _dataclass
from dataclasses import is_dataclass, asdict, make_dataclass
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

        def __init__(self, *args, **kwargs):
            for name, value in kwargs.items():
                # getting field type
                ft = cclass.__annotations__.get(name, None)
                if is_dataclass(ft) and isinstance(value, dict):
                    obj = ft(**value)
                    kwargs[name]= obj
            o_init(self, *args, **kwargs)

        # injecting methods
        cclass.__init__=__init__
        cclass.save = _save  # types.MethodType(_save, cclass)
        cclass.load = _load
        cclass.asdict = _asdict
        cclass.__auto_version__ = _version
        # inject version
        # cclass.__class__ = make_dataclass('versioned_' + cclass.__class__.__name__,
        #                                   fields=[('__version__', version)], bases=(cclass.__class__,))
        return cclass

    return wrapper(args[0], version=_version) if args else wrapper

def __post_init__(self):
    deleted = []
    for field_name, field_def in self.__dataclass_fields__.items():
        actual_value = getattr(self, field_name)
        required_type = field_def.type
        if isinstance(required_type, Annotate):
            # check versions
            auto_version = LooseVersion(self.__auto_version__)
            added_version = LooseVersion(required_type.added if required_type.added else '0.0')
            if added_version > auto_version:
                raise ValueError(
                    f'`{self.__class__}.{field_name}` is not added in version {self.__auto_version__}')
            deprecated_version = LooseVersion(required_type.deprecated if required_type.deprecated else '999.0')
            deleted_version = LooseVersion(required_type.deleted if required_type.deleted else '999.0')
            if deprecated_version <= auto_version < deleted_version:
                warnings.warn(
                    f'`{self.__class__}.{field_name}` is deprecated in {deprecated_version} '
                    f'and will be deleted in {deleted_version}. Current is {auto_version}')
            elif deleted_version <= auto_version:
                warnings.warn(f'`{self.__class__}.{field_name}` is deleted in {deleted_version} in {self.__class__}')
                # setattr(self, field_name, ValueError('Deleted'))
                deleted.append(field_name)
                continue
            required_type = required_type.type
        if not isinstance(actual_value, required_type):
            raise ValueError(f'`{self.__class__}.{field_name}` requires {required_type}, given {type(actual_value)}')
    for to_delete in deleted:
        del self.__dataclass_fields__[to_delete]

def _save(self, f):
    d = asdict(self)
    d['__auto_version__'] = self.__auto_version__
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

def _asdict(self):
    return asdict(self)
