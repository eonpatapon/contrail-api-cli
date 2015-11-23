import os.path
from uuid import UUID
from pathlib import PurePosixPath

from prompt_toolkit import prompt


class Observable(object):

    def __new__(cls, *args, **kwargs):
        return super(Observable, cls).__new__(cls)

    @classmethod
    def register(cls, event, callback):
        if not hasattr(cls, "observers"):
            cls.observers = {}
        if event not in cls.observers:
            cls.observers[event] = []
        cls.observers[event].append(callback)

    @classmethod
    def unregister(cls, event, callback):
        try:
            cls.observers[event].remove(callback)
        except (ValueError, KeyError):
            pass

    @classmethod
    def emit(cls, event, data):
        if not hasattr(cls, "observers"):
            cls.observers = {}
        [cbk(data)
         for evt, cbks in cls.observers.items()
         for cbk in cbks
         if evt == event]


class Path(PurePosixPath):

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        if parts:
            parts = [root] + os.path.relpath(os.path.join(*parts), start=root).split(os.path.sep)
            parts = [p for p in parts if p not in (".", "")]
        return super(cls, Path)._from_parsed_parts(drv, root, parts, init)

    def __init__(self, *args):
        self.meta = {}

    @property
    def base(self):
        try:
            return self.parts[1]
        except IndexError:
            pass
        return ''

    @property
    def is_root(self):
        return len(self.parts) == 1 and self.root == "/"

    @property
    def is_resource(self):
        try:
            UUID(self.name, version=4)
        except (ValueError, IndexError):
            return False
        return True

    @property
    def is_collection(self):
        return self.base == self.name

    def relative_to(self, path):
        try:
            return PurePosixPath.relative_to(self, path)
        except ValueError:
            return self


class ShellContext(object):
    current_path = Path("/")


class classproperty(object):

    def __init__(self, f):
        self.f = f

    def __get__(self, instance, klass):
        if instance:
            try:
                return self.f(instance)
            except AttributeError:
                pass
        return self.f(klass)


def continue_prompt(message=""):
    answer = False
    message = message + u"\n'Yes' or 'No' to continue: "
    while answer not in ('Yes', 'No'):
        answer = prompt(message)
        if answer == "Yes":
            answer = True
            break
        if answer == "No":
            answer = False
            break
    return answer


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in all_subclasses(s)]
