# dlconfig
Configuration system for Deep Learning

# Example

```python
from dlconfig import dataclass  # advanced decorator out of dataclasses

@dataclass
class TrainConfig:
  batch_size : int = 32
  learning_rate : float = 1e-3

@dataclass
class MyExp:
  train : TrainConfig
  num_class : int = 1000
  depth : int = 50


cfg = MyExp(num_class=10)

# access nested configs
print('lr:', cfg.train.learning_rate)

# dlconfig automatically generates argparser
cfg.parse_args()

# dlconfig can save/load from/to JSON/YAML
cfg.save('cfg.yaml')
cfg = MyExp.load('cfg.yaml')

# merge/update from another config
cfg.merge('exp1.yaml')
cfg1 = MyExp(depth=150)
cfg.update(cfg1)

# check for modification, including type-change
modified, type_changed, unchanged = cfg.compare(MyExp())

# freeze to avoid unexpected changes
cfg.lock(raise_exception=True)
try:
  cfg.train.learning_rate = 100
except TypeError:
  # attempts to change the value will raise error
  pass

# unfreeze
cfg.unlock()

```
