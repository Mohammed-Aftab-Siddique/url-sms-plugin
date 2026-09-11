# URL SMS Plugin

The URL SMS Plugin is a local Dynatrace OneAgent extension that monitors a
configured list of HTTP(S) URLs. It publishes the final availability result for
every URL and uses time-based escalation to determine when an unavailable URL
requires notification. A URL is healthy only when its final HTTP status is
`200`.

## Architecture

```text
Configured URLs
    -> URL availability client
    -> HTTP status metric (Host IP, URL)
    -> alert-state engine and durable cache
    -> SMS formatter and gateway client
    -> configured recipients
```

The extension runs where OneAgent runs. It is not a remote ActiveGate
extension.

## Prerequisites

- Dynatrace OneAgent with support for Python extensions.
- Python 3.10 or later in the extension runtime.
- Network access from the OneAgent host to monitored URLs and the SMS gateway.
- An SMS gateway URL, username, password, and JSESSIONID value.

## Configuration

Configure the extension through local activation configuration. Keep the
password and JSESSIONID in Dynatrace secret fields; do not commit real values.

| Setting | Description |
| --- | --- |
| URLs to Monitor | One or more unique plain HTTP(S) URLs. |
| L1, L2, L3 Recipients | Recipient numbers for initial and escalating alerts. |
| L2/L3 Criticality Delay | Continuous-failure minutes before L2/L3 applies. L3 must exceed L2. |
| Polling Interval | Intended URL-check interval in seconds. |
| Maximum Redirects | Maximum redirects followed during one URL check. |
| Cache Retention | Minutes to retain recovered or removed-URL alert state. |
| SMS API URL / Username | SMS gateway endpoint and user name. |
| SMS API Password / JSESSIONID | Gateway secrets. |
| Dry Run | Logs notification delivery rather than sending it. |

## URL checks and metric

Each URL is checked up to five times within a 30-second retry window. The final
result is reported as the gauge metric:

```text
custom.url.availability.status
```

Dimensions are `Host` (the active IPv4 address of the OneAgent host) and `URL`
(the configured URL). The metric value is the final HTTP status or a normalized
transport status:

| Value | Meaning |
| --- | --- |
| `-1` | TLS/certificate failure |
| `-2` | Timeout |
| `-3` | Connection failure |
| `-4` | Redirect limit or loop |
| `-5` | Other request failure |

## Alert lifecycle

A continuous non-`200` result creates an L1 alert action, then L2 and L3
actions only when their configured delays are reached. Alerts are not repeated
at the same level. A later `200` result creates one issue-resolution action for
every escalation level reached.

State is isolated per activation, written atomically, and retained according to
the configured retention period. Failure, escalation, and recovery timestamps
use Indian Standard Time (`Asia/Kolkata`, IST); escalation delays use elapsed
time.

## SMS gateway contract

The SMS transport will submit a form-encoded `POST` request with:

- `Content-Type: application/x-www-form-urlencoded`
- `Cookie: JSESSIONID=<configured cookie ID>`
- `auth`: JSON containing configured username/password and `appName: Ecamptest`
- `jsonString`: JSON containing campaign `AppDynamics` and the recipient number

The message payload is:

```text
Incident: <failure, escalation, or resolution>
URL: <configured URL>
Status: <HTTP or normalized status>
Time: <IST timestamp>
DT
```

The URL checks, metric, durable alert state, and alert decisions are available.
SMS transport is the remaining capability to connect to the gateway.

## Security

- Treat password and JSESSIONID values as secrets.
- Never log gateway credentials, cookies, or authorization payloads.
- Use dummy credentials only with the local mock gateway.
