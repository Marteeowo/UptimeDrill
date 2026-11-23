"""Poll the local service's readiness and print health transitions."""

import argparse
import sys
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPException
from time import perf_counter, sleep


def check_readiness(port):
    connection = HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/readyz")
        with connection.getresponse() as response:
            response.read()
            return response.status == 200, f"HTTP {response.status}"
    except (OSError, HTTPException) as error:
        return False, type(error).__name__
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--once", action="store_true", help="exit 0 when ready, otherwise 1")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    previous_health = None
    try:
        while True:
            started = perf_counter()
            healthy, result = check_readiness(args.port)
            elapsed_ms = (perf_counter() - started) * 1000
            timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            state = "UP" if healthy else "DOWN"
            changed = previous_health is not None and healthy != previous_health
            transition = " CHANGE" if changed else ""
            print(f"{timestamp} {state}{transition} {result} {elapsed_ms:.1f} ms", flush=True)
            if args.once:
                return 0 if healthy else 1
            previous_health = healthy
            sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
