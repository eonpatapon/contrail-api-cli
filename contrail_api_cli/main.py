from __future__ import unicode_literals
import os
import sys
import argparse
import logging
import logging.config
from six import text_type

from keystoneauth1.loading import cli
from keystoneauth1.exceptions.http import HttpError, HTTPClientError

from .manager import CommandManager
from .exceptions import CommandError, NotFound, Exists
from .utils import CONFIG_DIR, printo
from .schema import create_schema_from_version, list_available_schema_version, DummySchema, SchemaError
from .context import Context
from . import client


logger = logging.getLogger(__name__)


def get_subcommand_kwargs(mgr, name, namespace):
    """Get subcommand options from global parsed
    arguments.
    """
    subcmd = mgr.get(name)
    subcmd_kwargs = {}
    for opt in list(subcmd.args.values()) + list(subcmd.options.values()):
        if hasattr(namespace, opt.dest):
            subcmd_kwargs[opt.dest] = getattr(namespace, opt.dest)
    return (subcmd, subcmd_kwargs)


def main():
    argv = sys.argv[1:]

    # early setup for logging
    if '-d' in argv or '--debug' in argv:
        logging.basicConfig(level=logging.DEBUG)
    if '--logging-conf' in argv:
        try:
            path = argv[argv.index('--logging-conf') + 1]
            logging.config.fileConfig(path)
        except IndexError:
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d',
                        action="store_true", default=False)
    parser.add_argument('--schema-version',
                        default=os.environ.get('CONTRAIL_API_VERSION', None),
                        choices=list_available_schema_version(),
                        help="schema version used by contrail-api server (default=%(default)s)")
    parser.add_argument('--logging-conf',
                        help="python logging configuration file")
    parser.add_argument('--config-dir',
                        help="path of configuration directory (default=%(default)s)",
                        default=os.environ.get('CONTRAIL_API_CLI_CONFIG_DIR', CONFIG_DIR))

    # contrail api session options
    client.register_argparse_arguments(parser)
    # Default auth plugin will be http unless OS_AUTH_PLUGIN envvar is set
    cli.register_argparse_arguments(parser, argv, default="http")
    # Add commands to the parser given the namespaces list
    mgr = CommandManager.register_argparse_commands(parser, argv)

    options = parser.parse_args()

    if not os.path.exists(options.config_dir):
        os.makedirs(options.config_dir)

    Context().session = client.load_from_argparse_arguments(options)

    if options.schema_version:
        Context().schema = create_schema_from_version(options.schema_version)
    else:
        Context().schema = DummySchema()

    try:
        subcmd, subcmd_kwargs = get_subcommand_kwargs(mgr, options.subcmd, options)
        logger.debug('Calling %s with %s' % (subcmd, subcmd_kwargs))
        result = subcmd(**subcmd_kwargs)
    except (HTTPClientError, HttpError, CommandError, SchemaError, Exists, NotFound) as e:
        printo(text_type(e), std_type='stderr')
        exit(1)
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass
    else:
        if result:
            printo(result)


if __name__ == "__main__":
    main()
