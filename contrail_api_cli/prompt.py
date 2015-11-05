import sys
import argparse

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

from pygments.token import Token

from keystoneclient import session, auth
from keystoneclient.exceptions import ClientException, HttpError

from contrail_api_cli.client import APIClient
from contrail_api_cli.style import PromptStyle
from contrail_api_cli import utils, commands
from contrail_api_cli.utils import ShellContext

history = InMemoryHistory()
completer = utils.ResourceCompleter()
utils.ResourceCompletionFiller(completer).start()


def get_prompt_tokens(cli):
    return [
        (Token.Username, APIClient.user or ''),
        (Token.At, '@' if APIClient.user else ''),
        (Token.Host, APIClient.HOST),
        (Token.Colon, ':'),
        (Token.Path, str(ShellContext.current_path)),
        (Token.Pound, '> ')
    ]


def main():
    argv = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost:8082',
                        help="host:port to connect to (default='%(default)s')")
    parser.add_argument('--ssl', action="store_true", default=False,
                        help="connect with SSL (default=%(default)s)")
    session.Session.register_cli_options(parser)
    # Default auth plugin will be http unless OS_AUTH_PLUGIN envvar is set
    auth.register_argparse_arguments(parser, argv, default="http")
    options = parser.parse_args()

    if options.ssl:
        APIClient.PROTOCOL = 'https'
    if options.host:
        APIClient.HOST = options.host

    APIClient.make_session(options.os_auth_plugin, **vars(options))

    # load home resources
    try:
        utils.Collection(path=ShellContext.current_path)
    except ClientException as e:
        print(e)
        sys.exit(1)

    while True:
        try:
            action = prompt(get_prompt_tokens=get_prompt_tokens,
                            history=history,
                            completer=completer,
                            style=PromptStyle)
        except (EOFError, KeyboardInterrupt):
            break
        try:
            action_list = action.split()
            cmd = getattr(commands, action_list[0])
            args = action_list[1:]
        except IndexError:
            continue
        except AttributeError:
            print("Command not found. Type help for all commands.")
            continue

        try:
            result = cmd.parse_and_call(*args)
        except (HttpError, ClientException, commands.CommandError) as e:
            print(e)
            continue
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            if result is None:
                continue
            print(result)

if __name__ == "__main__":
    main()
