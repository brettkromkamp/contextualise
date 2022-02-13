"""
wsgi.py file. Part of the Contextualise project.

November 10, 2019
Brett Alistair Kromkamp (brettkromkamp@gmail.com)
"""

from contextualise import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        use_debugger=False,
        use_reloader=False,
        host="0.0.0.0",
    )
