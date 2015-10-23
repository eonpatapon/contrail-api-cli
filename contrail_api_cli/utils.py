import os.path
import json
from uuid import UUID
try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from threading import Thread
from pathlib import PurePosixPath

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion


COMPLETION_QUEUE = Queue()


class PathEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Path):
            return str(obj)
        return super(self, PathEncoder).default(obj)


class FullPathEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Path):
            return obj.url
        return super(self, FullPathEncoder).default(obj)


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
    def __init__(self, ignore_case=False, WORD=True, match_middle=True):
        self.paths = []
        self.ignore_case = ignore_case
        self.WORD = WORD
        self.match_middle = match_middle

    def get_completions(self, document, complete_event):
        from contrail_api_cli.prompt import CURRENT_PATH

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
            if path.resource_name == CURRENT_PATH.resource_name:
                return "_"
            return path.resource_name

        for p in sorted(self.paths, key=path_sort):
            rel_path = p.relative_to(CURRENT_PATH)
            if not rel_path:
                continue
            if (path_matches(str(rel_path).lower()) or
                    path_matches(p.meta.get('fq_name', ''))):
                display_meta = p.meta.get('fq_name', '')
                yield Completion(str(rel_path),
                                 -len(path_before_cursor),
                                 display_meta=display_meta)


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
    def resource_name(self):
        try:
            return self.parts[1]
        except IndexError:
            pass

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
        return not self.is_resource and self.resource_name

    def relative_to(self, path):
        try:
            return PurePosixPath.relative_to(self, path)
        except ValueError:
            return self


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


def to_json(resource_dict):
    return json.dumps(resource_dict,
                      sort_keys=True,
                      indent=2,
                      separators=(',', ': '),
                      cls=FullPathEncoder)


def from_json(resource_json):
    return json.loads(resource_json, object_hook=decode_paths)


def decode_paths(obj):
    from contrail_api_cli.client import APIClient
    for attr, value in obj.items():
        if attr in ('href', 'parent_href'):
            obj[attr] = Path(value[len(APIClient.base_url):])
            obj[attr].meta["fq_name"] = ":".join(obj.get('to', obj.get('fq_name', '')))
    return obj
