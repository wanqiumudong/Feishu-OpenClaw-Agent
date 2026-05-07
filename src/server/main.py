import argparse

import uvicorn

from config import Settings
from server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="meetingflow-server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    uvicorn.run(create_app(Settings.default()), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
