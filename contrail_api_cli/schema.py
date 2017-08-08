"""This module creates schema data structure by parsing Contrail
schema files.

>>> list_available_schema_version()
>>> schema = create_schema_from_version("2.21")
>>> schema.all_resources()
>>> schema.resource('virtual-network').children

"""

from os import listdir
from os.path import isfile, join
import logging
import functools
from pkg_resources import parse_version
import operator

from six import add_metaclass

import contrail_api_cli
from .utils import to_json, Singleton
from .resource import RootCollection
from .idl_parser import IDLParser
from .context import Context

logger = logging.getLogger(__name__)

default_schemas_directory_name = "schemas"
default_schemas_directory_path = join(contrail_api_cli.__path__[0],
                                      default_schemas_directory_name)


class SchemaError(Exception):
    pass


class SchemaVersionNotAvailable(SchemaError):
    def __init__(self, version):
        self.version = version
        msg = "Schema version %s is not available" % self.version
        Exception.__init__(self, msg)


class ResourceNotDefined(SchemaError):
    def __init__(self, resource_name):
        self.resource_name = resource_name
        msg = "Resource '%s' is not defined in the schema" % self.resource_name
        Exception.__init__(self, msg)


def get_last_schema_version():
    """Return the last available schema version. Version are
    lexicographically sorted. If no version is available, return None.

    :rtype: str or None
    """
    versions = list_available_schema_version()
    if len(versions) > 0:
        return sorted(versions)[-1]
    else:
        return None


def list_available_schema_version():
    """To discover available schema versions."""
    return listdir(default_schemas_directory_path)


def _get_schema_version_path(version):
    if version in list_available_schema_version():
        return join(default_schemas_directory_path, version)
    else:
        raise SchemaVersionNotAvailable(version)


def _get_xsd_from_directory(pathname):
    xsd_files = []
    for f in listdir(pathname):
        abspath = join(pathname, f)
        if isfile(abspath) and abspath.endswith(".xsd"):
            xsd_files.append(abspath)
    return xsd_files


def _parse_xsd_file(filename):
    with open(filename) as f:
        ifmap_statements = IDLParser().Parse(f)
        # idl parser should return empty dict
        if ifmap_statements is None:
            ifmap_statements = {}
        return ifmap_statements


def create_schema_from_version(version):
    """Provide a version of the schema to create it. Use
    list_available_schema_version to discover available versions.

    """
    schema_directory = _get_schema_version_path(version)
    return create_schema_from_xsd_directory(schema_directory, version)


def create_schema_from_xsd_directory(directory, version):
    """Create and fill the schema from a directory which contains xsd
    files. It calls fill_schema_from_xsd_file for each xsd file
    found.

    """
    schema = Schema(version)
    for f in _get_xsd_from_directory(directory):
        logger.info("Loading schema %s" % f)
        fill_schema_from_xsd_file(f, schema)
    return schema


def fill_schema_from_xsd_file(filename, schema):
    """From an xsd file, it fills the schema by creating needed
    Resource. The generateds idl_parser is used to parse ifmap
    statements in the xsd file.

    """
    ifmap_statements = _parse_xsd_file(filename)
    properties_all = []

    for v in ifmap_statements.values():
        if (isinstance(v[0], IDLParser.Link)):
            src_name = v[1]
            target_name = v[2]
            src = schema._get_or_add_resource(src_name)
            target = schema._get_or_add_resource(target_name)
            if "has" in v[3]:
                src.children.append(target_name)
                target.parent = src_name
            if "ref" in v[3]:
                src.refs.append(target_name)
                target.back_refs.append(src_name)
        elif isinstance(v[0], IDLParser.Property):
            target_name = v[1][0]
            prop = ResourceProperty(v[0].name, is_list=v[0].is_list, is_map=v[0].is_map)
            if target_name != 'all':
                target = schema._get_or_add_resource(target_name)
                target.properties.append(prop)
            else:
                properties_all.append(prop)

    for r in schema.all_resources():
        schema.resource(r).properties += properties_all


class Schema(object):
    def __init__(self, version):
        self._schema = {}
        self._version = version

    @property
    def version(self):
        return self._version

    def resource(self, resource_name):
        try:
            return self._schema[resource_name]
        except KeyError:
            raise ResourceNotDefined(resource_name)

    def all_resources(self):
        return self._schema.keys()

    def _get_or_add_resource(self, resource_name):
        if resource_name not in self._schema:
            self._schema[resource_name] = ResourceSchema()
        return self._schema[resource_name]


class ResourceProperty(object):

    def __init__(self, name, is_list=False, is_map=False):
        if is_list is True:
            self.default = []
        elif is_map is True:
            self.default = {}
        else:
            self.default = None
        self.name = name
        self.key = name.replace('-', '_')

    def __unicode__(self):
        return "%s" % self.name

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.key)


class ResourceSchema(object):

    def __init__(self):
        self.children = []
        self.parent = None
        self.refs = []
        self.back_refs = []
        self.properties = []

    def json(self):
        data = {'children': self.children,
                'parent': self.parent,
                'refs': self.refs,
                'back_refs': self.back_refs,
                'properties': self.properties}
        return to_json(data)


class DummySchema(object):

    def __init__(self):
        DummyResourceSchema()

    @property
    def version(self):
        return "dummy"

    def resource(self, resource_name):
        if resource_name not in self.all_resources():
            raise ResourceNotDefined(resource_name)
        return DummyResourceSchema()

    def all_resources(self):
        return DummyResourceSchema().children


@add_metaclass(Singleton)
class DummyResourceSchema(ResourceSchema):

    def __init__(self):
        ResourceSchema.__init__(self)
        # add all resource types to all link types
        # so that LinkedResources can find linked
        # resources in the json representation
        self.children = self.refs = self.back_refs = \
            [c.type for c in RootCollection(fetch=True)]


op_map = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '=': operator.eq
}


def require_schema(version=None):
    def decorated(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(Context().schema, DummySchema):
                raise SchemaError("Schema is required")
            current_version = parse_version(Context().schema.version)
            if version is not None:
                parts = version.split()
                if len(parts) == 2:
                    op = op_map[parts[0]]
                    vers = parse_version(parts[1])
                else:
                    op = operator.eq
                    vers = parse_version(parts[0])
                if not op(current_version, vers):
                    raise SchemaError("Schema version must be %s" % version)
            return func(*args, **kwargs)
        return wrapper
    return decorated
