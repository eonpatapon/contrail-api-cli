from six import add_metaclass

from stevedore import extension

from .exceptions import CommandNotFound
from .utils import Singleton


@add_metaclass(Singleton)
class CommandManager(object):

    def __init__(self, namespace='contrail_api_cli.command'):
        """Load commands from namespace
        """
        self.mgr = extension.ExtensionManager(namespace=namespace,
                                              verify_requirements=True,
                                              on_load_failure_callback=self._on_failure,
                                              invoke_on_load=True)

    def _on_failure(self, mgr, entrypoint, exc):
        print('Cannot load command %s: %s' % (entrypoint.name,
                                              exc))

    def get(self, name):
        """Return command instance of loaded
        commands by name

        @param name: name of the command
        @type name: str
        """
        for ext in self.mgr.extensions:
            cmd = ext.obj
            if name in [cmd.name] + cmd.aliases:
                return cmd
        raise CommandNotFound('Command %s not found. Type help for all commands' % name)

    @property
    def list(self):
        """Generator of command instances
        """
        for ext in self.mgr.extensions:
            yield ext.obj
