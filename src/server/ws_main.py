from config import Settings
from server.ws_client import start_ws_client


def main() -> None:
    start_ws_client(Settings.default())


if __name__ == "__main__":
    main()
