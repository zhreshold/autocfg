# autocfg
Configuration system for Deep Learning

# Example

```python
from autocfg import dataclass  # advanced decorator out of dataclasses
from autocfg import Annotate  # version(and more) annotations

@dataclass(version='0.1')
class TrainConfig:
  batch_size : int = 32
  learning_rate : float = 1e-3
  lr : Annotate(float, deprecated='0.1', deleted='0.3', target='learning_rate') = 1e-3
  weight_decay : Annotate(float, added='0.1') = 1e-5

# supports nested config
# the versions of nested config are independent of each other
# default version is 0.0
@dataclass
class MyExp:
  train : TrainConfig
  num_class : int = 1000
  depth : int = 50


cfg = MyExp(num_class=10)

# access nested configs
print('lr:', cfg.train.learning_rate)

# easily convert to dict
dd = cfg.asdict()
# dd : {'train': {'batch_size': 32, 'learning_rate': 0.001, 'weight_decay': 0.00001}, \
# 'num_class': 10, 'depth': 50}

# autocfg automatically generates argparser, and can be used similarly
cfg.parse_args()

# autocfg can save/load from/to JSON/YAML
cfg.save('cfg.yaml')
cfg = MyExp.load('cfg.yaml')

# merge/update from another config
cfg.update('cfg1.yaml', allow_new_key=False, allow_type_change=False)
cfg1 = MyExp(depth=150)
cfg.update(cfg1)
# or
cfg.update(depth=150)
# or nested update
cfg.train.update(learning_rate=0.1)
# or nested update with dict
cfg.update({'train.learning_rate': 0.1})

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

```

```
# cfg.yaml
# root module: MyExp

version: 0.0
train: TrainCfg
num_class: 1000
depth: 50

TrainCfg:
  version: 0.1
  batch_size: 32
  learning_rate: 0.001
  weight_decay: 0.00001



```
