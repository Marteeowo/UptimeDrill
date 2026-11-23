# UptimeDrill verification

Checked on 24 November 2026. UTC incident samples fall on 23 November. The table records the original container verification and the subsequent GitHub run. A release-preparation recheck is recorded below. The Docker engine was initially stopped and was started for the original container run.

| Check | Result |
| --- | --- |
| Existing files and incident record | Inspected; Incident 001 preserved |
| Existing test files | Milestone 2's saved integration suite inspected and executed; Milestone 1 had used a transient harness |
| Python runtime | Python 3.11.11 on Windows |
| `python -m compileall -q app.py monitor.py tests` | Passed |
| `python -m unittest discover -s tests -v` | Passed, 2 tests in 3.082 seconds |
| Ten requested HTTP/monitor behaviors | Asserted by the operations drill, passed |
| Empty file, invalid UTF-8 and Unicode recovery | Passed |
| One-shot probe exit codes | Asserted healthy, dependency failure and stopped service, passed |
| `docker compose config --quiet` | Passed with Docker Compose v5.5.1 |
| Compose resolved configuration | Confirmed localhost-only publication, capability drop and no-new-privileges |
| Default and ephemeral Compose ports | Parsed both port 8080 and port 0; localhost binding confirmed |
| Workflow structure | YAML parsed; triggers, read-only token, action commit pins and final cleanup checked |
| Documentation links and whitespace | Local links resolved; per-file `git diff --no-index --check` passed |
| Docker Desktop startup | `docker desktop start --detach` succeeded without engine configuration changes |
| Docker Engine | Engine 29.8.0, Linux x86_64, `desktop-linux` context |
| Docker-enabled suite | `CRED_TEST_DOCKER=1 python -m unittest discover -s tests -v` passed, 2 tests in 29.970 seconds |
| Docker image build and Compose startup | Passed through the suite's scoped `compose build` and `compose up -d --wait` |
| Linux/non-root/host binding | Linux and nonzero UID asserted; localhost-only automatically assigned port asserted |
| Container incident and recovery | HTTP 200 -> 503 -> 200, continued liveness, missing-file log and host-monitor transitions passed |
| Docker health transitions | Healthy -> unhealthy -> healthy asserted and observed |
| Stopped service | Host monitor detected `DOWN CHANGE RemoteDisconnected`; one-shot probe returned failure |
| Container cleanup | Test confirmed no remaining containers; independent checks found no project network or project-tagged image |
| Unrelated resources | Before/after container, network and volume IDs matched exactly; 0 containers, 3 pre-existing networks, 0 volumes |
| Ubuntu GitHub runner execution | Passed on Ubuntu 26.04.1 with CPython 3.13.18 |
| GitHub Actions run | [45284589940](https://github.com/Marteeowo/UptimeDrill/actions/runs/45284589940), success |
| Publication review | Reviewed 13 source/configuration/documentation files; no hardcoded machine paths or credential patterns found |
| Dependencies | App and tests use the Python standard library; no runtime dependency installation added |

The local suite uses an isolated temporary directory, a free port and subprocess cleanup. Container project `cred-test-31f562db8040` was created and removed by the integration suite. Its resource teardown used the exact project name and removed only that project's containers, network and locally named image. No global prune command ran. An additional workflow cleanup step is configured for CI failures.

The app, monitor, tests, image and Compose configuration required no fixes during verification. Incident 001 remains intact. A review of the source, configuration and documentation found no hardcoded machine paths or credential patterns. The app and tests use the Python standard library.

See [Incident 002](INCIDENT-002.md) for actual HTTP/monitor samples and selected container logs. A Docker build cache can remain after cleanup. Docker Desktop remains running.

## Release-preparation recheck

On 24 November 2026, after updating the public name and documentation, syntax validation passed and the unchanged Python suite passed again with two tests in 3.056 seconds. The Docker-enabled suite passed two tests in 21.844 seconds, including build, startup, incident injection, health transitions, recovery, stopped-service detection and cleanup. Its project was `cred-test-8f69f2ad1cf8`.

After this recheck, containers and volumes were empty and only Docker's three built-in networks remained. The host/none network IDs were unchanged. The built-in bridge had a new ID with creation time `2026-11-23T22:49:03.219886399Z`, preceding the test network's creation at `22:49:05 UTC`. Recorded network events show creation, connection, disconnection and destruction of the test network. The cause of the built-in bridge replacement was not established. The test cleanup commands target only the named Compose project.

The current source, tests, fixture and incident records were preserved during naming and documentation preparation. The workflow display name changed to UptimeDrill checks. `.gitattributes` specifies LF line endings for text files. The README retains local/container runbooks and the hands-on incident exercise.

## GitHub Actions verification

The first public push of commit `f3a69ece1005bedc772e0a9f0b5141f9f6fd0204` triggered [run 45284589940](https://github.com/Marteeowo/UptimeDrill/actions/runs/45284589940). Its verification job ran from `2026-11-23T22:58:07Z` to `22:58:36Z` and completed successfully on Ubuntu 26.04.1 with CPython 3.13.18.

Syntax validation, local integration tests, Compose configuration validation, the Linux image build, container incident drill and final cleanup all passed. The local suite passed two tests in 0.506 seconds. The Docker-enabled suite passed two tests in 23.079 seconds. Logs recorded healthy -> unhealthy -> healthy, HTTP 503 during the dependency failure, recovery to HTTP 200, detection of the stopped service and `Cleanup verified for cred-test-45284589940-1`. No CI fixes were required.

## Verification limits

Verification covers the recorded local Windows/Docker Desktop runs and the GitHub Ubuntu run linked above. Results apply to those checks and revisions. Individual probe durations do not establish exact outage boundaries or performance guarantees.

These checks were executed automatically with Codex. The image version tag can change upstream, and the lab uses a development HTTP server with the limitations documented in the README.
