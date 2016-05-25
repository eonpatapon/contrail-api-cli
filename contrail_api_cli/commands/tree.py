# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..resource import Resource
from ..utils import format_tree, parallel_map
from ..exceptions import ResourceMissing

NB_WORKERS = 100


class Tree(Command):
    description = "Tree of resource references"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    reverse = Option('-r',
                     help="Show tree of back references",
                     action="store_true", default=False)
    parent = Option('-p',
                    help="Show tree of parents",
                    action="store_true", default=False)

    def _create_tree(self, resource, reverse, parent, visited):
        tree = {}
        resource.fetch()
        tree['node'] = [str(self.current_path(resource)), str(resource.fq_name)]
        visited.append(resource.uuid)
        if parent:
            try:
                childs = [resource.parent]
            except ResourceMissing:
                childs = []
        elif reverse:
            childs = resource.back_refs
        else:
            childs = resource.refs
        if childs:
            childs = [c for c in childs if c.uuid not in visited]
            tree['childs'] = parallel_map(self._create_tree, childs,
                                          args=(reverse, parent, visited),
                                          workers=NB_WORKERS)
        return tree

    def __call__(self, paths=None, reverse=False, parent=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        trees = parallel_map(self._create_tree, resources,
                             args=(reverse, parent, []),
                             workers=NB_WORKERS)
        return '\n'.join([format_tree(tree) for tree in trees])
