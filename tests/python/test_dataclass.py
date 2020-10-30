import warnings
import pytest
from typing import Union, Tuple
from dataclasses import fields

from autocfg import dataclass, FrozenInstanceError  # advanced decorator out of dataclasses
from autocfg import AnnotateField as AF  # version(and more) annotations

class TypeC:
    pass

@dataclass
class SomeConfig:
    value : Union[TypeC, int, str] = 1
    tup : Tuple = (1, 2, 3)
    no_type = 0.5

@dataclass(version='0.1')
class TrainConfig:
  batch_size : int = 32
  learning_rate : float = 1e-3
  lr : AF(float, deprecated='0.1', deleted='0.3') = 1e-3
  weight_decay : AF(float, added='0.1') = 1e-5
  x : SomeConfig = SomeConfig(2)

# supports nested config
# the versions of nested config are independent of each other
# default version is 0.0
@dataclass
class MyExp:
  train : TrainConfig
  num_class : int = 1000
  depth : int = 50

# by default, python's dataclass won't annotate fields without type annotation
# autocfg automatically catch all fields with type `typing.Any`
@dataclass
class Plain:
    a = 1
    b = '2'
    c = (1, 2, 3)

def test_single_layer():
    train = TrainConfig(batch_size=16)
    assert train.batch_size == 16
    with pytest.warns(UserWarning):
        assert train.asdict()['batch_size'] == 16
    with pytest.warns(UserWarning):
        lr = train.lr

def test_nested():
    exp = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
    assert exp.num_class == 10
    assert exp.train.learning_rate == 1.0

def test_save_load():
    import io
    f = io.StringIO()
    with pytest.warns(UserWarning):
        exp = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0, x=SomeConfig(tup=(4, 5, 6, 7))))
        exp.save(f)
        exp1 = MyExp.load(f)
        assert exp == exp1

def test_save_load_tuple():
    import io
    f = io.StringIO()
    with pytest.warns(UserWarning):
        exp = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp.save(f)
        exp1 = MyExp.load(f)
        assert exp == exp1

def test_parse_args():
    exp = MyExp.parse_args(['--train.batch-size', '128', '--depth', '2'])
    assert exp.train.batch_size == 128
    assert exp.depth == 2

def test_update_from_file():
    import io
    f = io.StringIO()
    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        exp0.save(f)
        exp1.update(f)
        assert exp0 == exp1

def test_nested_update():
    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        exp1.update(num_class=10)
        exp1.train.update(learning_rate=1.0)
        assert exp0 == exp1

    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        exp1.update({'num_class': 10, 'train': {'learning_rate': 1.0}})
        assert exp0 == exp1

def test_update_new_key_type_change():
    exp = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
    exp.update({'new_k': 'new_value'}, allow_new_key=True)
    with pytest.raises(TypeError):
        exp.new_k = 100
    exp.update(new_k=100, allow_type_change=True)
    assert exp.new_k == 100
    # new key with dict value
    exp.update({'new_dict_k': {'a': 1, 'b': '2'}}, allow_new_key=True)
    assert exp.new_dict_k['a'] == 1
    # no type check anymore in value dict, this is expected
    exp.new_dict_k['a'] = '1'

def test_default_nested_value_intact():
    # make sure the nested default value of another dataclass won't be overwritten
    exp = MyExp(train=TrainConfig(batch_size=1))
    exp.train.batch_size = 100
    exp.train.x.value = 1000
    train = TrainConfig()
    assert train.batch_size == 32
    some_x = SomeConfig()
    assert some_x.value == 1

def test_assignment():
    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        exp1.num_class = 10
        exp1.train.learning_rate=1.0
        exp1.train.x.no_type = 'str_type'
        assert exp0 == exp1

def test_union_type():
    sc = SomeConfig()
    sc.update(value='2')
    sc.update({'value': 3})

def test_diff():
    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        print('\n'.join(exp0.diff(exp1)))

def test_freeze_unfreeze():
    exp = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
    f_exp = exp.freeze()
    with pytest.raises(FrozenInstanceError):
        f_exp.num_class = 100
    with pytest.raises(FrozenInstanceError):
        f_exp.update({})
    f_exp.unfreeze()
    f_exp.num_class = 1000
    f_exp = exp.freeze()
    with pytest.raises(FrozenInstanceError):
        f_exp.num_class = 100

def test_auto_type_annotation():
    plain = Plain(a=2)
    assert plain.a == 2
    plain.a = 'a'
    assert plain.a == 'a'
    assert plain.b == '2'
    plain2 = Plain()
    print(plain2.__dataclass_fields__)
    for k, v in plain2.__dataclass_fields__.items():
        print(k, v._field_type)
    print(fields(plain2))
    assert plain2.a == 1
    assert plain2.b == '2'
    assert plain2.asdict().get('a', None) == 1

"""
# check for modification, including type-check
modified, type_changed, unchanged = cfg.compare(MyExp())

# pretty print
cfg.pprint(ref=MyExp())

# freeze to avoid unexpected changes
cfg.freeze(raise_exception=True)
try:
  cfg.train.learning_rate = 100
except TypeError:
  # attempts to change the value will raise error
  pass

# unfreeze
cfg.unfreeze()
assert cfg.is_frozen() == False
"""
