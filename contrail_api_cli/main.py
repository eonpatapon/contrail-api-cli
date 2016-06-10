from __future__ import unicode_literals
import os
import sys
import argparse
import logging
from six import text_type

from keystoneclient import session as ksession, auth
from keystoneclient.exceptions import ClientException, HttpError

from .manager import CommandManager
from .exceptions import CommandError, NotFound, Exists
from .utils import CONFIG_DIR, printo
from . import command


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

    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    command.make_api_session(options)
    try:
        subcmd, subcmd_kwargs = get_subcommand_kwargs(mgr, options.subcmd, options)
        logger.debug('Calling %s with %s' % (subcmd, subcmd_kwargs))
        result = subcmd(**subcmd_kwargs)
    except (HttpError, ClientException, CommandError, Exists, NotFound) as e:
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
