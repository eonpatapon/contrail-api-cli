import sys
import pprint
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
completer = utils.PathCompleter(match_middle=True)
utils.PathCompletionFiller(completer).start()


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

    auth_plugin = auth.load_from_argparse_arguments(options)
    APIClient.SESSION = session.Session.load_from_cli_options(options, auth=auth_plugin)

    try:
        for p in APIClient().list(ShellContext.current_path):
            ShellContext.completion_queue.put(p)
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
            elif type(result) == list:
                output_paths = []
                for p in result:
                    output_paths.append(str(p.relative_to(ShellContext.current_path)))
                    ShellContext.completion_queue.put(p)
                print("\n".join(output_paths))
            elif type(result) == dict:
                print(pprint.pformat(result, indent=2))
            else:
                print(result)

if __name__ == "__main__":
    main()
