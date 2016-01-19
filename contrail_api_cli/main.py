from __future__ import unicode_literals
import os
import sys
import argparse
import logging
from six import text_type

from keystoneclient import session as ksession, auth
from keystoneclient.exceptions import ClientException, HttpError

from .manager import CommandManager
from .exceptions import CommandError, ResourceNotFound, NoResourceFound, BadPath
from .utils import printo
from . import commands


logger = logging.getLogger(__name__)


def get_subcommand_kwargs(mgr, name, namespace):
    """Get subcommand options from global parsed
    arguments.
    """
    subcmd = mgr.get(name)
    subcmd_kwargs = {}
    for action in subcmd.parser._actions:
        if (action.dest is not argparse.SUPPRESS and
                action.default is not argparse.SUPPRESS):
            subcmd_kwargs[action.dest] = getattr(namespace, action.dest)
    return (subcmd, subcmd_kwargs)


def main():
    argv = sys.argv[1:]

    # early setup for logging
    if '-d' in argv or '--debug' in argv:
        logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', '-H',
                        default=os.environ.get('CONTRAIL_API_HOST', 'localhost'),
                        type=str,
                        help="host to connect to (default='%(default)s')")
    parser.add_argument('--port', '-p',
                        default=os.environ.get('CONTRAIL_API_PORT', 8082),
                        type=int,
                        help="port to connect to (default='%(default)s')")
    parser.add_argument('--protocol',
                        type=str,
                        default=os.environ.get('CONTRAIL_API_PROTOCOL', 'http'),
                        help="protocol used (default=%(default)s)")
    parser.add_argument('--debug', '-d',
                        action="store_true", default=False)
    ksession.Session.register_cli_options(parser)
    # Default auth plugin will be http unless OS_AUTH_PLUGIN envvar is set
    auth.register_argparse_arguments(parser, argv, default="http")
    # Add commands to the parser given the namespaces list
    mgr = CommandManager.register_argparse_commands(parser, argv)

    options = parser.parse_args()

    commands.make_api_session(options)
    try:
        subcmd, subcmd_kwargs = get_subcommand_kwargs(mgr, options.subcmd, options)
        logger.debug('Calling %s with %s' % (subcmd, subcmd_kwargs))
        result = subcmd(**subcmd_kwargs)
    except (HttpError, ClientException, CommandError,
            ResourceNotFound, NoResourceFound, BadPath) as e:
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
