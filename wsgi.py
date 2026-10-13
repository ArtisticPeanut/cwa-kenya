"""Production WSGI entrypoint.

Serve this with a real WSGI server, e.g.:

    gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app      # Linux
    waitress-serve --listen=0.0.0.0:8000 wsgi:app          # Windows

Always uses the production config (which requires a strong SECRET_KEY), so a
FLASK_ENV=development left in .env cannot accidentally serve with debug on.
Override deliberately with CWA_CONFIG if you really need another config.
"""

import os

from app import create_app

app = create_app(os.environ.get("CWA_CONFIG", "production"))
