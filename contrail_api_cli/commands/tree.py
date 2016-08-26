# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..resource import Resource
from ..utils import format_tree, parallel_map, Path
from ..exceptions import ResourceMissing


class Tree(Command):
    """Show tree of references of a resource.

    .. code-block:: bash

        # tree of references
        admin@localhost:/> tree logical-router/dd954810-d614-4892-9ec6-9a9595cc64ff
        /logical-router/dd954810-d614-4892-9ec6-9a9595cc64ff                 default-domain:admin:router1
        ├── /virtual-machine-interface/18b02f01-4300-427f-a646-0a44351034a6  default-domain:admin:18b02f01-4300-427f-a646-0a44351034a6
        │   ├── /routing-instance/2f6907e9-20e7-415a-9969-bb5af375574d       default-domain:admin:net2:net2
        │   │   ├── /route-target/721618d4-0861-4bda-8a33-bb116584d4bb       target:64512:8000005
        │   │   ├── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053       target:64512:8000003
        │   │   └── /route-target/ecd725e8-6523-428b-9811-00828926f91b       target:64512:8000002
        │   ├── /virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413        default-domain:admin:net2
        │   │   └── /network-ipam/0edc36a1-c802-47be-b230-4b462d905b93       default-domain:default-project:default-network-ipam
        │   └── /security-group/8282a986-b9fd-4be1-96bd-ab100bd2bb8e         default-domain:admin:default
        ├── /virtual-machine-interface/6d9637e5-99ae-4d09-950e-50353b29411c  default-domain:admin:6d9637e5-99ae-4d09-950e-50353b29411c
        │   ├── /routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55       default-domain:admin:net1:net1
        │   │   ├── /route-target/79b5278c-a846-49f4-82ab-f1b8c05aff67       target:64512:8000001
        │   │   └── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053       target:64512:8000003
        │   ├── /virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70        default-domain:admin:net1
        │   │   └── /network-ipam/0edc36a1-c802-47be-b230-4b462d905b93       default-domain:default-project:default-network-ipam
        │   └── /security-group/8282a986-b9fd-4be1-96bd-ab100bd2bb8e         default-domain:admin:default
        └── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053               target:64512:8000003

        # tree of parents
        admin@localhost:/> tree -p routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55
        /routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55     default-domain:admin:net1:net1
        └── /virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
            └── /project/d0afbb0b-dd83-4a33-a673-9cb2b244e804      default-domain:admin
                └── /domain/cbc6051f-fd47-4a26-82ee-cb3482926e17   default-domain
    """
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

    def __call__(self, paths=None, reverse=False, parent=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        self.reverse = reverse
        self.parent = parent
        trees = parallel_map(self._create_tree,
                             resources,
                             args=(Path('/'),),
                             workers=50)
        return '\n'.join([format_tree(tree) for tree in trees])
