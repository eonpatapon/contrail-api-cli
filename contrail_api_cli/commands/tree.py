# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..resource import Resource
from ..utils import format_tree, parallel_map, Path
from ..exceptions import ResourceMissing


class Tree(Command):
    description = "Tree of resource references"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path', complete='resources::path')
    reverse = Option('-r',
                     help="Show tree of back references",
                     action="store_true", default=False)
    parent = Option('-p',
                    help="Show tree of parents",
                    action="store_true", default=False)

    def _create_tree(self, resource, parent_path):
        tree = {}
        resource.fetch()
        tree['node'] = [str(self.current_path(resource)),
                        str(resource.fq_name)]
        tree['childs'] = []
        if self.parent:
            try:
                childs = [resource.parent]
            except ResourceMissing:
                childs = []
        elif self.reverse:
            childs = list(resource.back_refs)
        else:
            childs = list(resource.refs)
        # avoid parent -> child -> parent and parent -> parent loops
        for idx, child in enumerate(childs[:]):
            if (child.path == parent_path or
                    child.path == resource.path):
                node = {
                    'node': [str(self.current_path(child)),
                             str(child.fq_name)]
                }
                tree['childs'].append(node)
                del childs[idx]
        if childs:
            tree['childs'] += parallel_map(self._create_tree, childs,
                                           args=(resource.path,))
        return tree

    def call(self, paths=None, reverse=False, parent=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        self.reverse = reverse
        self.parent = parent
        trees = parallel_map(self._create_tree,
                             resources,
                             args=(Path('/'),),
                             workers=50)
        return '\n'.join([format_tree(tree) for tree in trees])
