import types
import json
import yaml
from dataclasses import dataclass as _dataclass, is_dataclass, asdict

__all__ = ['dataclass']

# decorator to wrap original __init__
def dataclass(*args, **kwargs):

    def wrapper(check_class):

        # passing class to investigate
        check_class = _dataclass(check_class, **kwargs)
        o_init = check_class.__init__

        def __init__(self, *args, **kwargs):

            for name, value in kwargs.items():

                # getting field type
                ft = check_class.__annotations__.get(name, None)

                if is_dataclass(ft) and isinstance(value, dict):
                    obj = ft(**value)
                    kwargs[name]= obj
                o_init(self, *args, **kwargs)
        # injecting methods
        check_class.__init__=__init__
        check_class.save = types.MethodType(_save, check_class)

        return check_class

    return wrapper(args[0]) if args else wrapper

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
