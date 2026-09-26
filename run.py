import os
from app import create_app
from app.config import config

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", config["server"].get("host", "0.0.0.0"))
    port = int(os.environ.get("PORT", config["server"].get("port", 5000)))
    debug = config["server"].get("debug", False)

    print(f"==================================================")
    print(f" Raspberry Pi Control Center starting...")
    print(f" URL: http://{host}:{port}/")
    print(f" Environment: {'Debug' if debug else 'Production'}")
    print(f"==================================================")

    app.run(host=host, port=port, debug=debug)
