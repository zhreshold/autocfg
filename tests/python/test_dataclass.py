import warnings
import pytest

from autocfg import dataclass, FrozenInstanceError  # advanced decorator out of dataclasses
from autocfg import AnnotateField as AF  # version(and more) annotations

@dataclass(version='0.1')
class TrainConfig:
  batch_size : int = 32
  learning_rate : float = 1e-3
  lr : AF(float, deprecated='0.1', deleted='0.3') = 1e-3
  weight_decay : AF(float, added='0.1') = 1e-5

# supports nested config
# the versions of nested config are independent of each other
# default version is 0.0
@dataclass
class MyExp:
  train : TrainConfig
  num_class : int = 1000
  depth : int = 50

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

def test_assignment():
    with pytest.warns(UserWarning):
        exp0 = MyExp(num_class=10, train=TrainConfig(learning_rate=1.0))
        exp1 = MyExp(num_class=100, train=TrainConfig(learning_rate=10.0))
        exp1.num_class = 10
        exp1.train.learning_rate=1.0
        assert exp0 == exp1

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
