import curses
from pygments.token import Token

try:
    # prompt_toolkit >= 0.55
    from prompt_toolkit.styles import style_from_dict
except ImportError:
    # prompt_toolkit <= 0.54
    from prompt_toolkit.styles import default_style_extensions
    from pygments.style import Style
    from pygments.styles.default import DefaultStyle

    def style_from_dict(d):
        styles = default_style_extensions.copy()
        styles.update(DefaultStyle.styles)
        styles.update(d)
        PromptStyle = type('PromptStyle', (Style,), {'styles': styles})
        return PromptStyle

try:
    curses.setupterm()
    nb_colors = curses.tigetnum("colors")
except:
    nb_colors = 256

if nb_colors == 8:
    default = style_from_dict({
        Token.Path: 'bold #00ff00',
        Token.Pound: 'bold',
        Token.At: 'bold',
        Token.Host: '#0000ff',
        Token.Username: '#0000ff',

        Token.Menu.Completions.Completion: 'bg:#ffffff #000000',
        Token.Menu.Completions.Completion.Current: 'bold bg:#000000 #ffffff',
        Token.Menu.Completions.Meta: 'bg:#ffffff #000000',
        Token.Menu.Completions.Meta.Current: 'bold bg:#000000 #ffffff',
        Token.Menu.Completions.MultiColumnMeta: 'bg:#000000 #ffffff',
        Token.Menu.Completions.ProgressBar: 'bg:#ffffff',
        Token.Menu.Completions.ProgressButton: 'bg:#000000',
    })
else:
    default = style_from_dict({
        Token.Path: 'bold #009AC7',
        Token.Pound: 'bold #FFFFFF',
        Token.At: 'bold #dadada',
        Token.Host: '#ffaf00',
        Token.Username: '#ffaf00',

        Token.Menu.Completions.Completion: 'bg:#74B3CC #204a87',
        Token.Menu.Completions.Completion.Current: 'bold bg:#274B7A #ffffff',
        Token.Menu.Completions.Meta: 'bg:#2C568C #eeeeee',
        Token.Menu.Completions.Meta.Current: 'bold bg:#274B7A #ffffff',
        Token.Menu.Completions.MultiColumnMeta: 'bg:#aaaaaa #000000',
        Token.Menu.Completions.ProgressBar: 'bg:#74B3CC',
        Token.Menu.Completions.ProgressButton: 'bg:#274B7A',
    })

# print default.styles
