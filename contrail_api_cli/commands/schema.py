from ..command import Command, Arg, CommandError
from ..schema import create_schema_from_version, list_available_schema_version, SchemaVersionNotAvailable, ResourceNotDefined

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter


class Schema(Command):
    description = "Explore schema resources"
    schema_version = Arg('-v', '--schema-version',
                         type=str,
                         default='2.21',
                         help="schema version to use (default='%(default)s')")
    list_version = Arg('-l', '--list-version',
                       action="store_true",
                       help="list available schema versions")
    resource_name = Arg(nargs="?", help="Schema resource name",
                        metavar='resource_name')

    # Could be provided by command module
    def colorize(self, json_data):
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

    def _list_resources(self, schema):
        return "\n".join(schema.all_resources())

    def _show_resource(self, schema, resource_name):
        try:
            json_data = schema.resource(resource_name).json()
            return self.colorize(json_data)
        except ResourceNotDefined as e:
            raise CommandError(str(e))

    def __call__(self, schema_version=None,
                 list_version=False, resource_name=None):

        if list_version:
            versions = " ".join(list_available_schema_version())
            return "Available schema versions are: %s" % versions

        else:
            try:
                schema = create_schema_from_version(schema_version)
            except SchemaVersionNotAvailable as e:
                raise CommandError(str(e))

            if resource_name is None:
                return self._list_resources(schema)
            else:
                return self._show_resource(schema, resource_name)
