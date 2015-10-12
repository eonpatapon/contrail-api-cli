import pprint

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory

from pygments.token import Token

from contrail_api_cli.client import APIClient, APIError, BASE_URL
from contrail_api_cli.style import PromptStyle
from contrail_api_cli import utils, commands

current_path = utils.Path()
history = InMemoryHistory()
completer = utils.PathCompleter(match_middle=True, current_path=current_path)
utils.PathCompletionFiller(completer).start()


def get_bottom_toolbar_tokens(cli):
    return [(Token.Toolbar, ' ' + BASE_URL)]


def get_prompt_tokens(cli):
    return [
        (Token.Path, str(current_path)),
        (Token.Pound, '> ')
    ]


def main():
    for p in APIClient().list(current_path):
        utils.COMPLETION_QUEUE.put(p)

    while True:
        try:
            action = prompt(get_prompt_tokens=get_prompt_tokens,
                            get_bottom_toolbar_tokens=get_bottom_toolbar_tokens,
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
            print ("Command not found. Type help for all commands.")
            continue

        try:
            result = cmd(current_path, *args)
        except commands.CommandError:
            continue
        except APIError as e:
            print (e)
            continue
        else:
            if result is None:
                continue
            elif type(result) == list:
                output_paths = []
                for p in result:
                    output_paths.append(str(p.relative(current_path)))
                    utils.COMPLETION_QUEUE.put(p)
                print "\n".join(output_paths)
            elif type(result) == dict:
                print(pprint.pformat(result, indent=2))
            else:
                print(result)

if __name__ == "__main__":
    main()
