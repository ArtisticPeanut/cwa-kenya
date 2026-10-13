import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Development runner. Debug follows the config (on for DevelopmentConfig,
    # off in production). For production, serve wsgi:app with a real server.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port)
