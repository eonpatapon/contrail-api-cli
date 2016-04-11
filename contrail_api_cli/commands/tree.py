# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, expand_paths
from ..resource import Resource
from ..utils import print_tree, parallel_map


class Tree(Command):
    description = "Tree of resource references"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    reverse = Arg('-r', '--reverse',
                  help="Show tree of back references",
                  action="store_true", default=False)
    parent = Arg('-p', '--parent',
                 help="Show tree of parents",
                 action="store_true", default=False)

    def _create_tree(self, resource, reverse, parent):
        tree = {}
        resource.fetch()
        tree['node'] = [str(self.current_path(resource)), str(resource.fq_name)]
        if parent:
            childs = [resource.parent]
        elif reverse:
            childs = resource.back_refs
        else:
            childs = resource.refs
        if childs:
            tree['childs'] = parallel_map(self._create_tree, childs, args=(reverse, parent))
        return tree

    def __call__(self, paths=None, reverse=False, parent=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        trees = parallel_map(self._create_tree, resources, args=(reverse, parent))
        for tree in trees:
            print_tree(tree)
