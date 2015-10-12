from prompt_toolkit.styles import DefaultStyle

from pygments.style import Style
from pygments.token import Token


class PromptStyle(Style):
    styles = DefaultStyle.styles.copy()
    styles.update({
        Token.Path: 'bold #009AC7',
        Token.Pound: 'bold #FFFFFF',
        Token.At: 'bold #dadada',
        Token.Host: '#ffaf00',
        Token.Username: '#ffaf00',

        Token.Menu.Completions.Completion: 'bg:#74B3CC #204a87',
        Token.Menu.Completions.Completion.Current: 'bold bg:#274B7A #ffffff',
        Token.Menu.Completions.Meta: 'bg:#2C568C #eeeeee',
        # Token.Menu.Completions.Meta.Current: 'bold bg:#74B3CC #204a87',
        Token.Menu.Completions.Meta.Current: 'bold bg:#274B7A #ffffff',
        Token.Menu.Completions.MultiColumnMeta: 'bg:#aaaaaa #000000',
        Token.Menu.Completions.ProgressBar: 'bg:#74B3CC',
        Token.Menu.Completions.ProgressButton: 'bg:#274B7A',
    })
