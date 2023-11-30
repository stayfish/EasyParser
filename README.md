# Easy Parser

这是一个绑定函数和命令行指令的模块。支持多层级的命令。

使用时，首先实例化

```python
from easy_parser import EasyParser
parser = EasyParser()
```

实例化后必须先添加模块，然后给模块添加命令

有两种添加方式：
    - 对类进行装饰
    - 直接添加模块

**装饰器的方式**：现在我们有一个类，现在我们想要在 parser 中添加一个指令组

```python
@parser.add_module('math', help='math toolkit')
class Math:
    pass
```

现在我们有了一个叫 math 的模块，可以通过 `math = parser.sub_modules['\math']` 或者 `math=Math()` 得到

现在我们可以在 math 上继续添加子模块 int

```python
@math.add_module('int', help='integer operations')
class Integer:
    @command('plus', [
        ('--b',{"required":True, "type":int}),
        ('a', dict(type=int))
        ])
    def add(a, b):
        print(a + b)
```

对于模块下的函数，我们可以把该函数和命令通过 `@command` 进行绑定，`command` 接受三个参数，分别是命令名，参数列表，以及帮助文档。参数列表包含了对一系列参数的定义，定义方式为参数名字以及参数信息的字典，该字典的键值即 `argparse` 的参数

**直接添加**：添加模块的方式为

```python
math = parser.new_module('math', help='math toolkit')
```

添加命令

```python
def add2(a, b):
    print(a + b)

math.add_command('plus', add2, [
    ('--a',{"required":True, "type":int}),
        ('b', dict(type=int))
], help='add 2 integers')
```

添加完命令后，我们可以利用 `parse` 方法直接对命令解析，解析的过程会自动执行绑定的函数

```python
cmd = 'math int plus --b 2 1'
parser.parse(cmd.split())
# Output: 3 
```
