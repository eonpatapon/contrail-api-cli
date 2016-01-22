from __future__ import unicode_literals
import json
from uuid import UUID
from six import string_types
try:
    from UserDict import UserDict
    from UserList import UserList
except ImportError:
    from collections import UserDict, UserList

from keystoneclient.exceptions import HTTPError

from .utils import FQName, Path, Observable, to_json
from .exceptions import ResourceNotFound, ResourceMissing


class ResourceEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, FQName):
            return obj._data
        if isinstance(obj, Resource):
            return obj.data
        if isinstance(obj, Collection):
            return obj.data
        return super(ResourceEncoder, self).default(obj)


class ResourceBase(Observable):
    session = None

    def __new__(cls, *args, **kwargs):
        if cls.session is None:
            raise ValueError("ContrailAPISession must be initialized first")
        return super(ResourceBase, cls).__new__(cls, *args, **kwargs)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, str(self.path))

    def __hash__(self):
        if self.uuid:
            ident = (self.type, self.uuid)
        else:
            ident = (self.type,)
        return hash(ident)

    @property
    def uuid(self):
        return ''

    @property
    def fq_name(self):
        return FQName()

    @property
    def path(self):
        """Return Path of the resource

        :rtype: Path
        """
        return Path("/") / self.type / self.uuid

    @property
    def href(self):
        """Return URL of the resource

        :rtype: str
        """
        url = self.session.base_url + str(self.path)
        if self.path.is_collection and not self.path.is_root:
            return url + 's'
        return url


class Collection(ResourceBase, UserList):
    """Class for interacting with an API collection

    >>> from contrail_api_cli.resource import Collection
    >>> c = Collection('virtual-network', fetch=True)
    >>> # iterate over the resources
    >>> for r in c:
    >>>     print(r.path)
    >>> # filter support
    >>> c.filter("router_external", False)
    >>> c.fetch()
    >>> assert all([r.get('router_external') for r in c]) == False

    :param type: name of the collection
    :type type: str
    :param fetch: immediately fetch collection from the server
    :type fetch: bool
    :param recursive: level of recursion
    :type recursive: int
    :param fields: list of field names to fetch
    :type fields: [str]
    :param filters: list of filters
    :type filters: [(name, value), ...]
    :param parent_uuid: filter by parent_uuid
    :type parent_uuid: v4UUID str or list of v4UUID str
    """

    def __init__(self, type, fetch=False, recursive=1,
                 fields=None, filters=None, parent_uuid=None,
                 **kwargs):
        UserList.__init__(self)
        self.type = type
        self.fields = fields or []
        self.filters = filters or []
        self.parent_uuid = list(self._sanitize_parent_uuid(parent_uuid))
        self.meta = dict(kwargs)
        if fetch:
            self.fetch(recursive=recursive)
        self.emit('created', self)

    def __len__(self):
        """Return the number of items of the collection

        :rtype: int
        """
        if not self.data:
            res = self.session.get_json(self.href, count=True)
            return res[self._contrail_name]['count']
        return super(Collection, self).__len__()

    @property
    def _contrail_name(self):
        if self.type:
            return self.type + 's'
        return self.type

    def _sanitize_parent_uuid(self, parent_uuid):
        if parent_uuid is None:
            raise StopIteration
        if isinstance(parent_uuid, string_types):
            parent_uuid = [parent_uuid]
        for p in parent_uuid:
            try:
                UUID(p, version=4)
            except ValueError:
                continue
            yield p

    def filter(self, field_name, field_value):
        """Add permanent filter on the collection

        :param field_name: name of the field to filter on
        :type field_name: str
        :param field_value: value to filter on
        """
        self.filters.append((field_name, field_value))

    def _format_fetch_params(self, fields, filters, parent_uuid):
        params = {}
        fields_str = ",".join(self._fetch_fields(fields))
        filters_str = ",".join(['%s==%s' % (f, json.dumps(v))
                                for f, v in self._fetch_filters(filters)])
        parent_uuid_str = ",".join(self._fetch_parent_uuid(parent_uuid))
        if fields_str:
            params['fields'] = fields_str
        if filters_str:
            params['filters'] = filters_str
        if parent_uuid_str:
            params['parent_id'] = parent_uuid_str

        return params

    def _fetch_parent_uuid(self, parent_uuid=None):
        return self.parent_uuid + list(self._sanitize_parent_uuid(parent_uuid))

    def _fetch_filters(self, filters=None):
        return self.filters + (filters or [])

    def _fetch_fields(self, fields=None):
        return self.fields + (fields or [])

    def fetch(self, recursive=1, fields=None, filters=None, parent_uuid=None):
        """
        Fetch collection from API server

        :param recursive: level of recursion
        :type recursive: int
        :param fields: list of field names to fetch
        :type fields: [str]
        :param filters: list of filters
        :type filters: [(name, value), ...]
        :param parent_uuid: filter by parent_uuid
        :type parent_uuid: v4UUID str or list of v4UUID str
        """

        params = self._format_fetch_params(fields, filters, parent_uuid)
        data = self.session.get_json(self.href, **params)

        if not self.type:
            self.data = [Collection(col["link"]["name"],
                                    fetch=recursive - 1 > 0,
                                    recursive=recursive - 1,
                                    fields=self._fetch_fields(fields),
                                    filters=self._fetch_filters(filters),
                                    parent_uuid=self._fetch_parent_uuid(parent_uuid),
                                    **col["link"])
                         for col in data['links']
                         if col["link"]["rel"] == "collection"]
        else:
            self.data = [Resource(self.type,
                                  fetch=recursive - 1 > 0,
                                  recursive=recursive - 1,
                                  **res)
                         for res_type, res_list in data.items()
                         for res in res_list]


class RootCollection(Collection):

    def __init__(self, **kwargs):
        return super(RootCollection, self).__init__('', **kwargs)


class Resource(ResourceBase, UserDict):
    """Class for interacting with an API resource

    >>> from contrail_api_cli.resource import Resource
    >>> r = Resource('virtual-network',
                     uuid='4c45e89b-7780-4b78-8508-314fe04a7cbd',
                     fetch=True)
    >>> r['display_name'] = 'foo'
    >>> r.save()

    >>> p = Resource('project', fq_name='default-domain:admin')
    >>> r = Resource('virtual-network', fq_name='default-domain:admin:net1',
                     parent=p)
    >>> r.save()

    :param type: type of the resource
    :type type: str
    :param fetch: immediately fetch resource from the server
    :type fetch: bool
    :param uuid: uuid of the resource
    :type uuid: v4UUID str
    :param fq_name: fq name of the resource
    :type fq_name: str (domain:project:identifier)
                   or list ['domain', 'project', 'identifier']
    :param check: check that the resource exists
    :type check: bool
    :param parent: parent resource
    :type parent: Resource
    :param recursive: level of recursion
    :type recursive: int

    :raises ResourceNotFound: bad uuid or fq_name is given
    :raises HttpError: when save(), fetch() or delete() fail

    .. note::

        Either fq_name or uuid must be provided.
    """

    def __init__(self, type, fetch=False, check=False,
                 parent=None, recursive=1, **kwargs):
        assert('fq_name' in kwargs or 'uuid' in kwargs or 'to' in kwargs)
        self.type = type

        for key in ('fq_name', 'to'):
            if key in kwargs:
                kwargs[key] = FQName(kwargs[key])

        UserDict.__init__(self, **kwargs)

        if parent:
            self.parent = parent

        if check:
            self.check()

        if fetch:
            self.fetch(recursive=recursive)

        self.emit('created', self)

    def check(self):
        """Check that the resource exists.

        :raises ResourceNotFound: if the resource doesn't exists
        """
        if self.fq_name:
            self['uuid'] = self._check_fq_name(self.fq_name)
        elif self.uuid:
            self['fq_name'] = self._check_uuid(self.uuid)
        return True

    def _check_uuid(self, uuid):
        try:
            fq_name = self.session.id_to_fqname(uuid)
        except HTTPError:
            raise ResourceNotFound(uuid=uuid)
        return fq_name

    def _check_fq_name(self, fq_name):
        try:
            uuid = self.session.fqname_to_id(self.type, fq_name)
        except HTTPError:
            raise ResourceNotFound(fq_name=fq_name)
        return uuid

    @property
    def exists(self):
        """Returns True if the resource exists on the API server,
        or returns False.

        :rtype: bool
        """
        try:
            self.check()
        except ResourceNotFound:
            return False
        return True

    @property
    def uuid(self):
        """Return UUID of the resource

        :rtype: str
        """
        return self.get('uuid', super(Resource, self).uuid)

    @property
    def fq_name(self):
        """Return FQDN of the resource

        :rtype: FQName
        """
        return self.get('fq_name', self.get('to', super(Resource, self).fq_name))

    @property
    def parent(self):
        """Return parent resource

        :rtype: Resource
        :raises ResourceNotFound: parent resource doesn't exists
        :raises ResourceMissing: parent resource is not defined
        """
        try:
            return Resource(self['parent_type'], uuid=self['parent_uuid'], check=True)
        except KeyError:
            raise ResourceMissing('%s has no parent resource' % self)

    @parent.setter
    def parent(self, resource):
        """Set parent resource

        :param resource: parent resource
        :type resource: Resource

        :raises ResourceNotFound: resource not found on the API
        """
        resource.check()
        self['parent_type'] = resource.type
        self['parent_uuid'] = resource.uuid

    def save(self):
        """Save the resource to the API server

        If the resource doesn't have a uuid the resource will be created.
        If uuid is present the resource is updated.
        """
        if self.path.is_collection:
            data = self.session.post_json(self.href,
                                          {self.type: dict(self.data)},
                                          cls=ResourceEncoder)
        else:
            data = self.session.put_json(self.href,
                                         {self.type: dict(self.data)},
                                         cls=ResourceEncoder)
        self.from_dict(data[self.type])
        self.fetch(exclude_children=True, exclude_back_refs=True)

    def delete(self):
        """Delete resource from the API server
        """
        res = self.session.delete(self.href)
        if res:
            self.emit('deleted', self)
        return res

    def fetch(self, recursive=1, exclude_children=False, exclude_back_refs=False):
        """Fetch resource from the API server

        :param recursive: level of recursion for fetching resources
        :type recursive: int
        :param exclude_children: don't get children references
        :type exclude_children: bool
        :param exclude_back_refs: don't get back_refs references
        :type exclude_back_refs: bool
        """
        if not self.path.is_resource:
            self.check()
        params = {}
        # even if the param is False the API will exclude resources
        if exclude_children:
            params['exclude_children'] = True
        if exclude_back_refs:
            params['exclude_back_refs'] = True
        data = self.session.get_json(self.href, **params)[self.type]
        self.from_dict(data)

    def from_dict(self, data, recursive=1):
        """Populate the resource from a python dict

        :param recursive: level of recursion for fetching resources
        :type recursive: int
        """
        # Find other linked resources
        data = self._encode_resource(data, recursive=recursive)
        self.data.update(data)

    def _encode_resource(self, data, recursive=1):
        for attr, value in list(data.items()):
            if attr == 'fq_name':
                data[attr] = FQName(value)
            if attr.endswith('refs'):
                ref_type = "-".join([c for c in attr.split('_')
                                     if c not in ('back', 'refs')])
                for idx, r in enumerate(data[attr]):
                    data[attr][idx] = Resource(ref_type,
                                               fetch=recursive - 1 > 0,
                                               recursive=recursive - 1,
                                               **data[attr][idx])
        return data

    @property
    def back_refs(self):
        """Return back_refs resources of the resource

        :rtype: Resource generator
        """
        for attr, value in self.data.items():
            if attr.endswith(('back_refs', 'loadbalancer_members')):
                for back_ref in value:
                    yield back_ref

    @property
    def refs(self):
        """Return refs resources of the resource

        :rtype: Resource generator
        """
        for attr, value in self.data.items():
            if attr.endswith('refs') and not attr.endswith('back_refs'):
                for ref in value:
                    yield ref

    def json(self):
        """Return JSON representation of the resource
        """
        return to_json(self.data, cls=ResourceEncoder)

    def __str__(self):
        if hasattr(self, 'data'):
            return str(self.data)
        return str({})
