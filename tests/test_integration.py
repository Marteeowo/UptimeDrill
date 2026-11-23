"""Exercise real HTTP and monitor processes, optionally against Docker Compose."""

from datetime import datetime, timezone
from http.client import HTTPConnection
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
# On Windows a venv launcher can outlive or orphan the interpreter it starts.
PYTHON = getattr(sys, "_base_executable", sys.executable)


class CapturedProcess:
    def __init__(self, *arguments):
        self.process = subprocess.Popen(
            [PYTHON, "-u", *arguments], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.lines = []
        self.queue = Queue()
        self.reader = Thread(target=self.collect, daemon=True)
        self.reader.start()

    def collect(self):
        for line in self.process.stdout:
            self.lines.append(line.rstrip())
            self.queue.put(line.rstrip())

    def expect(self, pattern, timeout=12):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            try:
                line = self.queue.get(timeout=max(0.01, deadline - monotonic()))
            except Empty:
                break
            if re.search(pattern, line):
                print(line, flush=True)
                return line
        raise AssertionError(f"Missing {pattern!r}. Output: {self.lines[-20:]}")

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.join(timeout=5)
        self.process.stdout.close()


class OperationsDrill(unittest.TestCase):
    def setUp(self):
        self.docker = os.environ.get("CRED_TEST_DOCKER") == "1"
        if self.docker:
            self.project = os.environ.get("CRED_TEST_PROJECT", f"cred-test-{uuid4().hex[:12]}")
            if not re.fullmatch(r"cred-test-[a-z0-9-]+", self.project):
                raise ValueError("Test project must start with cred-test- and use lowercase letters/digits")
            print(f"Compose test project: {self.project}", flush=True)
            self.env = {**os.environ, "CRED_PORT": "0"}
            self.addCleanup(self.cleanup_compose)
            self.compose("build", timeout=240)
            self.compose("up", "-d", "--wait", "--wait-timeout", "30")
            address = self.compose("port", "app", "8080").strip()
            self.port = int(address.rsplit(":", 1)[1])
            self.assertTrue(address.startswith("127.0.0.1:"), address)
            self.assertNotEqual(self.compose("exec", "-T", "app", "id", "-u").strip(), "0")
            self.assertEqual(self.compose("exec", "-T", "app", "uname", "-s").strip(), "Linux")
        else:
            temporary = TemporaryDirectory(prefix="cred-test-")
            self.addCleanup(temporary.cleanup)
            self.message = Path(temporary.name) / "message.txt"
            self.message.write_text("Project Cred is ready\n", encoding="utf-8")
            self.app = CapturedProcess("app.py", "--port", "0", "--message-file", str(self.message))
            self.addCleanup(self.app.close)
            startup = self.app.expect(r"Listening on 127\.0\.0\.1:\d+")
            self.port = int(startup.rsplit(":", 1)[1])

    def compose(self, *arguments, timeout=60):
        result = subprocess.run(
            ["docker", "compose", "--project-name", self.project, *arguments],
            cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode:
            raise AssertionError(f"Compose {arguments} failed:\n{result.stdout}\n{result.stderr}")
        return result.stdout

    def cleanup_compose(self):
        try:
            print(self.compose("logs", "--no-color", "app"), flush=True)
        finally:
            self.compose("down", "--rmi", "local", "--timeout", "5", timeout=120)
            remaining = self.compose("ps", "--all", "--quiet").strip()
            self.assertEqual(remaining, "", "Test containers remain after cleanup")
            print(f"Cleanup verified for {self.project}", flush=True)

    def request(self, path, status, payload):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request("GET", path)
            with connection.getresponse() as response:
                self.assertEqual(response.status, status, path)
                self.assertEqual(json.load(response), payload, path)
        finally:
            connection.close()
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        print(f"{now} {path} HTTP {status}", flush=True)

    def rename(self, source, destination):
        if self.docker:
            self.compose("exec", "-T", "app", "python", "-c",
                         f"from pathlib import Path; Path('/data/{source}').rename('/data/{destination}')")
        else:
            self.message.with_name(source).rename(self.message.with_name(destination))

    def expect_health(self, expected):
        deadline = monotonic() + 15
        container = self.compose("ps", "--quiet", "app").strip()
        while monotonic() < deadline:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", container],
                capture_output=True, text=True, check=True, timeout=5,
            )
            if result.stdout.strip() == expected:
                print(f"Docker health: {expected}", flush=True)
                return
            sleep(0.2)
        self.fail(f"Docker health did not become {expected}")

    def test_failure_recovery_and_stopped_service(self):
        monitor = CapturedProcess("monitor.py", "--port", str(self.port), "--interval", "0.1")
        self.addCleanup(monitor.close)
        monitor.expect(r" UP HTTP 200 ")
        self.request("/", 200, {"message": "Project Cred is ready"})
        self.request("/livez", 200, {"status": "live"})
        self.request("/readyz", 200, {"status": "ready"})
        self.request("/readyz?probe=1", 200, {"status": "ready"})
        self.request("/missing", 404, {"status": "not_found"})
        self.check_once(0)
        if self.docker:
            self.expect_health("healthy")

        self.rename("message.txt", "message.offline")
        try:
            monitor.expect(r" DOWN CHANGE HTTP 503 ")
            self.request("/", 503, {"status": "unavailable"})
            self.request("/readyz", 503, {"status": "unavailable"})
            self.request("/livez", 200, {"status": "live"})
            self.check_once(1)
            if self.docker:
                self.expect_health("unhealthy")
                self.assertIn("FileNotFoundError", self.compose("logs", "--no-color", "app"))
            else:
                self.app.expect(r"message dependency unavailable \(FileNotFoundError\)")
        finally:
            self.rename("message.offline", "message.txt")

        monitor.expect(r" UP CHANGE HTTP 200 ")
        self.request("/", 200, {"message": "Project Cred is ready"})
        self.request("/readyz", 200, {"status": "ready"})
        if self.docker:
            self.expect_health("healthy")
            self.compose("stop", "--timeout", "5", "app")
        else:
            self.assertIsNone(self.app.process.poll(), "App exited before recovery")
            self.app.close()
        monitor.expect(r" DOWN CHANGE (ConnectionRefusedError|TimeoutError|ConnectionResetError|RemoteDisconnected) ")
        self.check_once(1)

    def check_once(self, expected):
        result = subprocess.run(
            [PYTHON, "monitor.py", "--port", str(self.port), "--once"],
            cwd=ROOT, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


class LocalEdgeCases(unittest.TestCase):
    def test_empty_and_invalid_dependency(self):
        from app import StatusService
        from monitor import check_readiness

        with TemporaryDirectory(prefix="cred-edge-") as folder:
            message = Path(folder) / "message.txt"
            message.write_text("  ", encoding="utf-8")
            with StatusService(0, message) as server:
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    self.assertEqual(check_readiness(server.server_port), (False, "HTTP 503"))
                    message.write_bytes(b"\xff")
                    self.assertEqual(check_readiness(server.server_port), (False, "HTTP 503"))
                    message.write_text("Tere, töötab", encoding="utf-8")
                    self.assertEqual(check_readiness(server.server_port), (True, "HTTP 200"))
                finally:
                    server.shutdown()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
