# Incident 002 · Container dependency outage drill

## Verification status

Verified on 24 November 2026 locally, with UTC samples falling on 23 November. **The Linux container incident passed end-to-end.** Docker Desktop started through `docker desktop start --detach`; the existing `desktop-linux` engine became available without configuration changes. Docker reported Engine 29.8.0, Linux, x86_64. The Docker-enabled suite passed two tests in 29.970 seconds, including image build, Compose startup, incident recovery, log inspection and cleanup.

## Environment and failure

The image was built from `python:3.13-slim-bookworm` and started with Compose. The Docker test asserted `uname -s` returned `Linux` and `id -u` was nonzero. The Dockerfile selects UID/GID 10001. The test used an automatically assigned localhost port forwarding to port 8080. `/data/message.txt` was a fixture in the container's writable layer. Docker probed readiness through `monitor.py --once`.

The test renamed `/data/message.txt` to `/data/message.offline` inside the app container. `/` and `/readyz` returned HTTP 503 while `/livez` remained HTTP 200. The app logged `message dependency unavailable (FileNotFoundError)`. Repeated readiness failures changed Docker health to unhealthy.

The root cause was the intentionally absent content dependency. Restoring the original filename recovered application and readiness responses to HTTP 200. The host monitor reported recovery and Docker returned to healthy. Recovery required no application restart. The [README](README.md#container-incident-exercise) gives the reproduction commands.

## Observed container evidence

The host monitor recorded these samples against the containerized service.

```text
2026-11-23T22:35:23.869+00:00 UP HTTP 200 3.5 ms
2026-11-23T22:35:24.295+00:00 DOWN CHANGE HTTP 503 1.6 ms
2026-11-23T22:35:28.114+00:00 UP CHANGE HTTP 200 1.6 ms
2026-11-23T22:35:35.046+00:00 DOWN CHANGE RemoteDisconnected 1.0 ms
```

The last transition followed the deliberate Compose service stop after recovery. One-shot probes also returned the expected healthy/failing exit codes. The test printed Docker health in this order, awaiting each state before proceeding.

```text
Docker health: healthy
Docker health: unhealthy
Docker health: healthy
```

Selected application log lines captured through `docker compose logs` show startup and the cause of failure.

```text
app-1  | 2026-11-23 22:35:20,588 INFO Listening on 0.0.0.0:8080
app-1  | 2026-11-23 22:35:24,293 WARNING message dependency unavailable (FileNotFoundError)
```

The test additionally asserted healthy application/liveness/readiness, application/readiness failure with continued liveness, restored application/readiness, HTTP 404 for an unknown route and query-string handling. Probe times are individual samples using a 0.1-second host test interval. They do not establish exact outage boundaries or general performance.

## Cleanup verification

The test used project `cred-test-31f562db8040`. Its scoped Compose teardown removed the app container, project network and project-tagged image, then confirmed no test containers remained. Independent checks found no project network or project-tagged image. Container, network and volume ID inventories before and after the run matched exactly, with zero containers, three pre-existing networks and zero volumes. No global cleanup command ran. Docker build cache may remain, and Docker Desktop remains running.

## Earlier local baseline from Milestone 2

The automated Python drill exercised the same app and monitor on Windows with a temporary message file and an automatically assigned loopback port. The following output came from the passing test run. UTC samples fall on 23 November, corresponding to 24 November locally.

```text
2026-11-23T22:27:12.783+00:00 UP HTTP 200 6.3 ms
2026-11-23T22:27:12.889+00:00 DOWN CHANGE HTTP 503 0.9 ms
2026-11-23T22:27:12.995+00:00 UP CHANGE HTTP 200 0.9 ms
2026-11-23T22:27:14.107+00:00 DOWN CHANGE TimeoutError 1005.9 ms
```

The app log identified `FileNotFoundError`. The test asserted healthy application, liveness and readiness responses; failing application/readiness with healthy liveness; restored application/readiness; and an unknown route returning 404. Restoring the fixture recovered the running process. Stopping that process then produced the final DOWN transition. These are individual probe measurements using a 0.1-second test interval. They do not establish exact outage duration or container performance.

## GitHub verification

After publication, [GitHub Actions run 45284589940](https://github.com/Marteeowo/UptimeDrill/actions/runs/45284589940) verified the same drill on Ubuntu 26.04.1 with CPython 3.13.18. Both the local and Docker-enabled suites passed, along with syntax/configuration validation and final container cleanup. The Docker-enabled suite completed two tests in 23.079 seconds. The original local evidence above remains the incident baseline.

The Ubuntu container monitor recorded `DOWN CHANGE HTTP 503` at `2026-11-23T22:58:22.746+00:00`, recovery at `22:58:26.808+00:00`, and `DOWN CHANGE ConnectionRefusedError` after the deliberate stop at `22:58:33.914+00:00`. Docker health changed healthy -> unhealthy -> healthy, and the test reported `Cleanup verified for cred-test-45284589940-1`.

## Comparison with Incident 001

Incident 001 recorded a local Python drill using a transient test harness. This incident now verifies the same failure mechanism inside a Linux container, using the saved test suite and Docker health checks. Both drills demonstrate recovery after restoring the message file; this run also verifies container lifecycle and cleanup.
