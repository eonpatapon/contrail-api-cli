import pprint
import argparse

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

from pygments.token import Token

from contrail_api_cli.client import APIClient, APIError
from contrail_api_cli.style import PromptStyle
from contrail_api_cli import utils, commands

current_path = utils.Path()
history = InMemoryHistory()
completer = utils.PathCompleter(match_middle=True, current_path=current_path)
utils.PathCompletionFiller(completer).start()


def get_prompt_tokens(cli):
    return [
        (Token.Username, APIClient.USER),
        (Token.At, '@' if APIClient.USER else ''),
        (Token.Host, APIClient.HOST),
        (Token.Colon, ':'),
        (Token.Path, str(current_path)),
        (Token.Pound, '> ')
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost:8082',
                        help="host:port to connect to (default='%(default)s')")
    parser.add_argument('--ssl', action="store_true", default=False,
                        help="connect with SSL (default=%(default)s)")
    parser.add_argument('--user', default='',
                        help="authenticate with user (default='%(default)s')")
    parser.add_argument('--password', default='',
                        help="authenticate with password (default='%(default)s')")
    options = parser.parse_args()
    if options.ssl:
        APIClient.PROTOCOL = 'https'
    if options.host:
        APIClient.HOST = options.host
    if options.user and options.password:
        APIClient.USER = options.user
        APIClient.PASSWORD = options.password

    for p in APIClient().list(current_path):
        utils.COMPLETION_QUEUE.put(p)

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
            result = cmd(current_path, *args)
        except commands.CommandError as e:
            print(e)
            continue
        except APIError as e:
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
                    output_paths.append(str(p.relative(current_path)))
                    utils.COMPLETION_QUEUE.put(p)
                print("\n".join(output_paths))
            elif type(result) == dict:
                print(pprint.pformat(result, indent=2))
            else:
                print(result)

if __name__ == "__main__":
    main()
