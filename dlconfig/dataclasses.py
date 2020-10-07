import types
import json
import yaml
from dataclasses import dataclass as _dataclass
from dataclasses import is_dataclass, asdict, make_dataclass

__all__ = ['dataclass']

# decorator to wrap original __init__
def dataclass(*args, **kwargs):

    def wrapper(cclass, version='0.0'):

        # passing class to investigate
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
        cclass.save = types.MethodType(_save, cclass)
        cclass.load = _load
        cclass.asdict = types.MethodType(_load, cclass)
        # inject version
        cclass.__class__ = make_dataclass('versioned_' + cclass.__class__.__name__,
                                          fields=[('__version__', version)], base=(cclass.__class__,))

        return cclass

    _version = str(kwargs.get('version', '0.0'))
    return wrapper(args[0], version=_version) if args else wrapper

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
        yaml.dump(d, f)

def _asdict(self):
    return asdict(self)
