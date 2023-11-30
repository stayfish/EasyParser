# from __future__ import annotations
from typing import Any, NoReturn
from typing import Callable
import argparse
import re
import sys
import os



T = tuple[tuple[str] | str, dict]

def singleton(cls):
    _instances = {}
    def inner(*args, **kwds):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwds)
        return _instances[cls]
    return inner

@singleton
class ModuleMap:
    def __init__(self):
        self.map = {}
    def add_func_to_module(self, py_module_name, class_name, func, keyword: str, args: list[T], help: str=""):
        path = py_module_name + '.' + class_name
        self.map[path] = (func, keyword, args, help)
    def get_func(self, py_module_name, class_name):
        path = py_module_name + '.' + class_name
        return self.map[path]


class ParserArgumentError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
    
class ParserDefineError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
    
class NewArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ParserArgumentError('Parse Argument error')
# class ParserModuleMeta(type):
#     _instances = {}

#     def __call__(cls, name: str, help: str | None=None, level: int=0):
#         if cls not in cls._instances:
#             cls._instances[cls] = {name: super(ParserModuleMeta, cls).__call__(name, help, level)}
#         elif name not in cls._instances[cls]:
#             cls._instances[cls][name] = super(ParserModuleMeta, cls).__call__(name, help, level)
#         return cls._instances[cls][name]
    
class ParserModuleMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwds):
        if cls not in cls._instances:
            cls._instances[cls] = super(ParserModuleMeta, cls).__call__(*args, **kwds)
        return cls._instances[cls]
    
class ParserModule(metaclass=ParserModuleMeta):
    def __init__(self, name: str, help: str | None=None, level: int=0):
        self.level = level
        # name 存的是绝对路径
        self.name = name
        self.help = help if help else "No doc provided"
        # self.parser = argparse.ArgumentParser(prefix_chars="-")
        self.parser = NewArgumentParser(prefix_chars='-')
        # parse 的时候，先去看是不是 submodule，
        # 是，就递归的 parse
        # 不是，就去看是不是 command，
        #   是，就 parse_args，然后执行对应的 func
        #   不是，raise ParseError
        # 避免 command 和 sub_module 重名
        # argument_name: is_positional
        self.arg_is_positional: dict[str, bool] = {}
        self.funcs: dict[str, tuple[Callable, bool, str]] = {}
        self.sub_modules: dict[str, ParserModule] = {}
        self.module_tree = {}

    def __str__(self) -> str:
        s = '\t' * self.level + self.name + '\t' + self.help+ '\n'
        for command_name in self.funcs:
            help = self.funcs[command_name][2]
            s += '\t' * (self.level + 1) +command_name + '\t' + help + '\n'
        for _, module in self.sub_modules.items():
            s += str(module)
        return s
    
    def __parse_args(self, args_list):
        parsed_result = self.parser.parse_args(args_list)
        args = [
            getattr(parsed_result, arg_name) 
            for arg_name, is_positional in self.arg_is_positional.items()
            if is_positional
        ]
        kwargs = {
            arg_name.replace('-', ''): getattr(parsed_result, arg_name.replace('-', ''))
            for arg_name, is_positional in self.arg_is_positional.items()
            if (not is_positional) and \
                getattr(parsed_result, arg_name.replace('-', ''), None) is not None
        }
        return args, kwargs

    def __run_command(self, command_name, args_list: list[str]):
        try:
            args, kwargs = self.__parse_args(args_list)
            args = tuple(args)
            func, is_static, help = self.funcs[command_name]
        # test zheli
        except Exception as e:
            print(self)
        else:
            if is_static:
                func(*args, **kwargs)
            else:
                func(self, *args, **kwargs)

    def parse(self, args: list[str] | None=None):
        if args is None:
            return
        if len(args) != 0 and args[0] in self.sub_modules:
            self.sub_modules[args[0]].parse(args[1:])
        elif len(args) != 0 and args[0] in self.funcs:
            self.__run_command(args[0], args[1:])
        else:
            self.__str__()

    def __assert_legal(self, key):
        pattern = r"[a-zA-Z]+"
        if not re.match(pattern, key):
            raise ParserDefineError(f"illegal keyword {key}")

        if key in self.sub_modules or key in self.funcs:
            raise ParserDefineError(f"Module or Command {key} Exists in {self.name}")

    # def add_command(self, key: str, func: Callable, *name_or_flags: str, **kwargs):

    #     self.__assert_legal(key)
        
    #     self.funcs[key] = func
    #     group = self.parser.add_argument_group(title=f"{key} options")
    #     for name in name_or_flags:
    #         self.arg_is_positional[name] = (
    #             False if name.startswith('-') else True)        
    #     group.add_argument(*name_or_flags, **kwargs)

    def __add_argument(self, group, *name_or_flags: str, **kwargs):
        for name in name_or_flags:
            self.arg_is_positional[name] = (
                False if name.startswith('-') else True)        
        group.add_argument(*name_or_flags, **kwargs)

    def add_command(self, key: str, func: Callable, args: list[T], is_static: bool=True, help: str=""):

        self.__assert_legal(key)
        
        self.funcs[key] = (func, is_static, help) 
        group = self.parser.add_argument_group(title=f"{key} options")
        for name_or_flags, kwargs in args:
            if isinstance(name_or_flags, str):
                self.__add_argument(group, name_or_flags, **kwargs)
            else:
                self.__add_argument(group, *name_or_flags, **kwargs)

    def new_module(self, key: str, help: str | None=None):
        
        self.__assert_legal(key)

        item_name = os.path.join(self.name, key)
        item = ParserModule(item_name, help, self.level + 1)
        self.sub_modules[key] = item

        return item
        
    # add module 的新 module 的名字应该是路径形式，比如 "tmux/list"
    def add_module(self, keyword: str, help: str | None=None, *initial_args, **initial_kwds):
        self.__assert_legal(keyword)
        item_name = os.path.join(self.name, keyword)
        this = self
        def wrapper_func(cls) -> ParserModule:
            class_name = cls.__name__
            py_module_name = cls.__module__
            module_map = ModuleMap()
            func, key, args, command_help = module_map.get_func(py_module_name, class_name)
            class Wrapper(cls, ParserModule):
                def __init__(self, *args, **kwds):
                    cls.__init__(self, *args, **kwds)
                    ParserModule.__init__(self, item_name, help, this.level + 1)
            item = Wrapper(*initial_args, **initial_kwds)
            item.add_command(key, func, args, is_static=False, help=command_help)
            self.sub_modules[keyword] = item
            return Wrapper
        return wrapper_func

def command(keyword: str, args: list[T], help: str=""):
    def keymap(func: Callable):
        py_module_name = func.__module__
        class_name = func.__qualname__.split(".")[0]
        module_map = ModuleMap()
        module_map.add_func_to_module(py_module_name, class_name, func, keyword, args, help)
        return func
    return keymap

class EasyParser:
    def __init__(self, help: str | None=None):
        self.root = ParserModule(name='/', help=help, level=-1)
        #TODO: 怎么让根节点的设置更优雅
        # self.command_trees = {""}
    #TODO：绑定上述和completer
    def boot(self):
        pass
    def add_module(self, key: str, help: str | None=None):
        return self.root.add_module(key, help)
    def parse(self, args: list[str] | None=None):
        if len(self.root.sub_modules) == 0:
            raise ParserDefineError('Expected at least 1 modules for earyparser')
        if args is None:
            args = sys.argv
        if len(args) == 0:
            return
        if args[0] not in self.root.sub_modules:
            print("TODO work")
        self.root.parse(args)

    def new_module(self, key: str, help: str | None=None):
        return self.root.new_module(key, help)
    
        
