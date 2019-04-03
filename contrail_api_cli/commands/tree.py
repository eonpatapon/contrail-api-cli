# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..resource import Resource
from ..utils import format_tree, parallel_map, Path
from ..exceptions import ResourceMissing


class Tree(Command):
    """Show tree of references of a resource.

    .. code-block:: bash

        # tree of back / childs references
        localhost:/> tree service-instance/f8e191c5-83fa-47f1-a242-e8ad7cab46c0
        service-instance/f8e191c5-83fa-47f1-a242-e8ad7cab46c0                     default-domain:project:a2fb6399-18ce-44ec-839d-d373221a6a8f
        ├── loadbalancer/a2fb6399-18ce-44ec-839d-d373221a6a8f                     default-domain:project:lbv2
        │   └── loadbalancer-listener/434b7b92-b68a-41f6-8321-8e7e2519d483        default-domain:project:lbv2_listener
        │       └── loadbalancer-pool/82cce54d-b13a-427c-bac6-fb7e976bcf5f        default-domain:project:lbv2_pool
        │           ├── loadbalancer-member/cc6e4c32-92c1-4668-879d-d6802f8ad3de  default-domain:project:lbv2_pool:cc6e4c32-92c1-4668-879d-d6802f8ad3de
        │           └── loadbalancer-member/fb30633f-407b-461d-bf20-3ac9f0cbe504  default-domain:project:lbv2_pool:fb30633f-407b-461d-bf20-3ac9f0cbe504
        ├── virtual-machine/68243a56-298d-4354-a077-b41b6bb55b7c                  default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f__1
        │   └── virtual-machine-interface/4a0bf808-19d7-48e9-b076-54064bebaf2e    default-domain:project:default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f__1__right__1
        │       └── instance-ip/44a9dc2a-446f-4d34-9148-4a2cc1f9a6f7              default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f-right
        └── virtual-machine/114be9ed-ac45-4dc8-9f45-559470037cfd                  default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f__2
            └── virtual-machine-interface/43afc4fe-8a84-47ba-96d9-73a8dd1d6b63    default-domain:project:default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f__2__right__1
                └── instance-ip/44a9dc2a-446f-4d34-9148-4a2cc1f9a6f7              default-domain__project__a2fb6399-18ce-44ec-839d-d373221a6a8f-right

        # tree of parents / references
        admin@localhost:/> tree -r routing-instance/f792b52d-ff69-487e-b2a5-c13060e3ce77
        routing-instance/f792b52d-ff69-487e-b2a5-c13060e3ce77        default-domain:project:test1:test1
        ├── route-target/7454c39a-b3c7-4d42-b766-bd276710d0b1        target:64518:8000133
        └── virtual-network/ce88182e-4e6e-4c61-9df1-7ffb24543578     default-domain:project:test1
            ├── network-ipam/d6bdafea-58d2-4240-8c65-2acf837d6750    default-domain:default-project:default-network-ipam
            │   └── project/acb58362-0272-4d27-97a1-da4ac1e2c5e3     default-domain:default-project
            │       └── domain/ff62f8f7-cccd-4a30-ba32-2ee3764fac79  default-domain
            └── project/0ed483e0-83ef-4f70-8250-1fcfa5d98c0e         default-domain:project
                └── domain/ff62f8f7-cccd-4a30-ba32-2ee3764fac79      default-domain
    """
    description = "Tree of resource references"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path', complete='resources::path')
    reverse = Option('-r',
                     help="Show tree of refs / parents",
                     action="store_true", default=False)

    def _create_tree(self, resource, parent_path):
        if resource.uuid not in self._cache:
            self._cache[resource.uuid] = resource.fetch()
        else:
            resource = self._cache[resource.uuid]
        tree = {
            'node': [str(self.current_path(resource)),
                     str(resource.fq_name)],
            'childs': []
        }
        if not self.reverse:
            childs = list(resource.back_refs) + list(resource.children)
        else:
            try:
                parents = [resource.parent]
            except ResourceMissing:
                parents = []
            childs = list(resource.refs) + parents
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

    def __call__(self, paths=None, reverse=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        self._cache = {}
        self.reverse = reverse
        trees = parallel_map(self._create_tree,
                             resources,
                             args=(Path('/'),),
                             workers=50)
        return '\n'.join([format_tree(tree) for tree in trees])
