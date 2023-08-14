"""
highlight_renderer.py file. Part of the Contextualise project.

February 13, 2022
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

import mistune
from pygments import highlight
from pygments.formatters import html
from pygments.lexers import get_lexer_by_name


class HighlightRenderer(mistune.HTMLRenderer):
    def __init__(self, escape=True, allow_harmful_protocols=None):
        super().__init__(escape, allow_harmful_protocols)

    def block_code(self, code, **kwargs):
        language = kwargs.get("info")
        print("Language: ", language)
        if language:
            lexer = get_lexer_by_name(language, stripall=True)
            formatter = html.HtmlFormatter()
            return highlight(code, lexer, formatter)
        return "<pre><code>" + mistune.escape(code) + "</code></pre>"
