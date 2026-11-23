# Incident 001 · Missing message file

This was a controlled, Codex-run drill on 12 November 2026 using Python 3.11.11 on Windows. The app and monitor ran as separate processes over loopback. The test used a temporary directory and an automatically assigned port.

## Impact and diagnosis

The drill renamed the lab message file. The application endpoint `/` and readiness endpoint `/readyz` returned HTTP 503. Liveness at `/livez` still returned HTTP 200, which showed that the process could answer requests while the application could no longer serve its content. The service log reported `message dependency unavailable (FileNotFoundError)`.

## Recovery and evidence

Restoring the original filename recovered the same running process. The monitor returned to HTTP 200 and `/` again returned `{"message": "Project Cred is ready"}`.

```text
2026-11-12T00:10:32.430+00:00 UP HTTP 200 3.2 ms
2026-11-12T00:10:34.431+00:00 DOWN CHANGE HTTP 503 1.0 ms
2026-11-12T00:10:36.437+00:00 UP CHANGE HTTP 200 0.9 ms
```

These are individual probe times. The monitor samples about every two seconds, so the samples bound when the transitions were observed and cannot establish the exact outage duration.

The integration check also confirmed that an unknown route returned HTTP 404 and that stopping the app after recovery produced `DOWN CHANGE TimeoutError`. See the [runbook](README.md) to repeat the dependency drill.
