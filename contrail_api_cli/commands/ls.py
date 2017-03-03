# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from ..command import Command, Arg, Option, expand_paths
from ..resource import Collection, Resource
from ..exceptions import CommandError
from ..utils import format_table


class Ls(Command):
    """List resources and collections.

    .. code-block:: bash

        # list API collections
        admin@localhost:/> ls
        domain
        global-vrouter-config
        instance-ip
        network-policy
        virtual-DNS-record
        route-target
        loadbalancer-listener
        floating-ip
        floating-ip-pool
        physical-router
        [...]

        # list collection
        admin@localhost:/> ls global-system-config
        global-system-config/d6820999-c8fe-45ae-acb2-48aebddb3b7d

        # long format
        admin@localhost:/> ls -l virtual-network
        virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413  default-domain:admin:net2
        virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
        virtual-network/e3148147-164e-4194-8507-a58eefe072bd  default-domain:default-project:default-virtual-network
        virtual-network/ba2170ce-741c-4361-ad88-f2d97162faf2  default-domain:default-project:ip-fabric
        virtual-network/e82ae164-f78a-4766-8ba2-7cb68dacaecb  default-domain:default-project:__link_local__

        # parametrized output format
        admin@localhost:/> ls -l -c instance_ip_address instance-ip
        instance-ip/f9d25887-2765-4ba0-bf45-54b9dbc5874a  192.168.20.1
        instance-ip/deb82100-00bb-4b5c-8495-4bbe34b5fab8  192.168.21.1
        instance-ip/2f5c047d-0a9c-4709-bcfa-d710ac68cc22  192.168.10.3
        instance-ip/04cb356a-fb1f-44fa-bb2f-d0f0dd4eedfd  192.168.20.3

        # filter by parent_uuid
        admin@localhost:/> ls -l -p d0afbb0b-dd83-4a33-a673-9cb2b244e804 virtual-network
        virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
        virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413  default-domain:admin:net2

        # filter by attribute
        admin@localhost:/> ls -l -f instance_ip_address=192.168.20.1 instance-ip
        instance-ip/f9d25887-2765-4ba0-bf45-54b9dbc5874a  f9d25887-2765-4ba0-bf45-54b9dbc5874a
    """
    description = "List resource objects"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path',
                complete='collections::path')
    long = Option('-l',
                  default=False, action="store_true",
                  help="use a long listing format")
    column = Option('-c', action="append",
                    help="fields to show in long mode",
                    default=[], dest="fields",
                    metavar="field_name")
    filter = Option('-f', action="append",
                    help="filter predicate",
                    default=[], dest='filters',
                    metavar='field_name=field_value')
    parent_uuid = Option('-P', help="filter by parent uuid",
                         complete="resources::uuid")
    # fields to show in -l mode when no
    # column is specified
    default_fields = [u'fq_name']
    aliases = ['ll = ls -l']

    def _field_val_to_str(self, fval, fkey=None):
        if fkey in ('fq_name', 'to'):
            return ":".join(fval)
        elif isinstance(fval, list) or isinstance(fval, Collection):
            return ",".join([self._field_val_to_str(i) for i in fval])
        elif isinstance(fval, dict) or isinstance(fval, Resource):
            return "|".join(["%s=%s" % (k, self._field_val_to_str(v, k))
                             for k, v in fval.items()])
        return text_type(fval)

    def _get_field(self, resource, field):
        # elif field.startswith('.'):
            # value = jq(field).transform(resource.json())
        value = '_'
        if field == 'path':
            value = self.current_path(resource)
        elif hasattr(resource, field):
            value = getattr(resource, field)
        elif isinstance(resource, Resource):
            value = resource.get(field, '_')
        return self._field_val_to_str(value)

    def _get_filter(self, predicate):
        # parse input predicate
        try:
            name, value = predicate.split('=')
        except ValueError:
            raise CommandError('Invalid filter predicate %s. '
                               'Use name=value format.' % predicate)
        if value == 'False':
            value = False
        elif value == 'True':
            value = True
        elif value == 'None':
            value = None
        else:
            try:
                value = int(value)
            except ValueError:
                value = text_type(value)
        return (name, value)

    def __call__(self, paths=None, long=False, fields=None,
                 filters=None, parent_uuid=None):
        if not long:
            fields = []
        elif not fields:
            fields = self.default_fields
        if filters:
            filters = [self._get_filter(p) for p in filters]
        resources = expand_paths(paths, filters=filters,
                                 parent_uuid=parent_uuid)
        result = []
        for r in resources:
            if isinstance(r, Collection):
                r.fetch(fields=fields)
                result += r.data
            elif isinstance(r, Resource):
                # need to fetch the resource to get needed fields
                if len(fields) > 1 or 'fq_name' not in fields:
                    r.fetch()
                result.append(r)
            else:
                raise CommandError('Not a resource or collection')
        # retrieve asked fields for each resource
        fields = ['path'] + fields
        result = [[self._get_field(r, f) for f in fields] for r in result]
        return format_table(result)
