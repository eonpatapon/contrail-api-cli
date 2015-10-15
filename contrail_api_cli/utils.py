import json
from uuid import UUID
try:
    from UserList import UserList
except ImportError:
    from collections import UserList
try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from threading import Thread
from six import string_types

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion


COMPLETION_QUEUE = Queue()


class PathEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        return super(self, PathEncoder).default(obj)


class PathCompletionFiller(Thread):

    def __init__(self, completer):
        super(PathCompletionFiller, self).__init__()
        self.completer = completer
        self.daemon = True

    def run(self):
        while True:
            p = COMPLETION_QUEUE.get()
            if p not in self.completer.paths:
                self.completer.paths.append(p)
            COMPLETION_QUEUE.task_done()


class PathCompleter(Completer):
    """
    Simple autocompletion on a list of paths.

    :param paths: List of paths.
    :param ignore_case: If True, case-insensitive completion.
    :param meta_dict: Optional dict mapping paths to their meta-information.
    :param WORD: When True, use WORD characters.
    :param match_middle: When True, match not only the start, but also in the
                         middle of the path.
    """
    def __init__(self, ignore_case=False, WORD=True, match_middle=True,
                 current_path=None):
        self.paths = []
        self.ignore_case = ignore_case
        self.WORD = WORD
        self.match_middle = match_middle
        self.current_path = current_path

    def get_completions(self, document, complete_event):
        path_before_cursor = document.get_word_before_cursor(WORD=self.WORD)

        if self.ignore_case:
            path_before_cursor = path_before_cursor.lower()

        def path_matches(path):
            """ True when the path before the cursor matches. """
            if self.match_middle:
                return path_before_cursor in path
            else:
                return path.startswith(path_before_cursor)

        def path_sort(path):
            # Make the relative paths of the resource appear first in
            # the list
            if path.resource_name == self.current_path.resource_name:
                return "_"
            return path.resource_name

        for p in sorted(self.paths, key=path_sort):
            rel_path = p.relative(self.current_path)
            if not rel_path:
                continue
            if (path_matches(str(rel_path).lower()) or
                    path_matches(p.meta.get('fq_name', ''))):
                display_meta = p.meta.get('fq_name', '')
                yield Completion(str(rel_path),
                                 -len(path_before_cursor),
                                 display_meta=display_meta)


class Path(UserList):

    def __init__(self, *args):
        def _split_component(component):
            if isinstance(component, string_types):
                return [c for c in component.strip('/').split('/') if c]
            if component is None:
                return []
            return component

        self.data = []

        for arg in args:
            self.data += _split_component(arg)

        self.meta = {}
        self.absolute = True

    @property
    def resource_name(self):
        try:
            return self.data[0]
        except IndexError:
            pass

    @property
    def is_root(self):
        return not self.data

    @property
    def is_resource(self):
        try:
            UUID(self.data[-1], version=4)
        except (ValueError, IndexError):
            return False
        return True

    def cd(self, path_str=None):
        path = self.data
        if path_str is None:
            path = []
        elif path_str == "..":
            path = path[:-1]
        elif path_str == ".":
            pass
        elif path_str.startswith("/"):
            path = path_str[1:].split("/")
        else:
            path += path_str.split("/")
        self.data = path
        return self.data

    def relative(self, path):
        rel_path = Path()
        for index, component in enumerate(self):
            try:
                if not component == path[index]:
                    rel_path.append(component)
            except IndexError:
                rel_path.append(component)
        if not path:
            rel_path.absolute = False
        elif path.resource_name == self.resource_name:
            rel_path.absolute = False
        return rel_path

    def __str__(self):
        path_str = "/".join(self.data)
        if self.absolute:
            return "/" + path_str
        return path_str


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


def continue_prompt():
    answer = False
    while answer not in ('Yes', 'No'):
        answer = prompt(u"'Yes' or 'No' to continue: ")
        if answer == "Yes":
            answer = True
            break
        if answer == "No":
            answer = False
            break
    return answer
