import os
import sys
import argparse

from keystoneclient import session as ksession, auth
from keystoneclient.exceptions import ClientException, HttpError

from . import commands


def get_subcommand_kwargs(name, namespace):
    """Get subcommand options from global parsed
    arguments.
    """
    subcmd = commands.get_command(name)
    subcmd_kwargs = {}
    for action in subcmd.parser._actions:
        if (action.dest is not argparse.SUPPRESS and
                action.default is not argparse.SUPPRESS):
            subcmd_kwargs[action.dest] = getattr(namespace, action.dest)
    return (subcmd, subcmd_kwargs)


def main():
    argv = sys.argv[1:]

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
    ksession.Session.register_cli_options(parser)
    # Default auth plugin will be http unless OS_AUTH_PLUGIN envvar is set
    auth.register_argparse_arguments(parser, argv, default="http")

    # Register cmds for direct call
    subparsers = parser.add_subparsers(dest='subcmd')
    for cmd in commands.commands_list():
        cmd_parser = subparsers.add_parser(cmd.name, help=cmd.description)
        cmd.add_arguments_to_parser(cmd_parser)

    options = parser.parse_args()

    commands.make_api_session(options)
    try:
        subcmd, subcmd_kwargs = get_subcommand_kwargs(options.subcmd, options)
        result = subcmd(**subcmd_kwargs)
    except (HttpError, ClientException, commands.CommandError) as e:
        print(e)
    except KeyboardInterrupt:
        pass
    except EOFError:
        pass
    else:
        if result:
            print(result.strip())


if __name__ == "__main__":
    main()
