# url_sms_plugin extension

## Building and signing

* `dt-sdk build .`

## Running

1. Create and activate the Python 3.14 development environment:
   `python3.14 -m venv .venv314 && source .venv314/bin/activate`.
2. Install the project and development dependencies: `python -m pip install -e ".[dev]"`.
3. In the ignored `secrets.json`, define `smsApiPassword` and
   `smsApiCookieId` for the matching placeholders in `activation.json`. Do
   not commit real values.
4. Adjust the non-secret example values in `activation.json` as needed, then run `dt-sdk run`.

Run the Stage 3 unit tests with `python -m unittest discover -s tests -v`.
The extension manifest intentionally retains Python 3.10 as its minimum
supported runtime.

The Stage 4 implementation validates local activation configuration, checks
every configured URL, and publishes `custom.url.availability.status` for each
final result. Its dimensions are `Host` (the OneAgent host) and `URL`; its value
is the HTTP status or a normalized negative transport status. It retries
non-200 and transport failures up to five times within a 30-second window.
The Stage 5 implementation also stores activation-isolated failure state using
atomic cache writes. It produces one L1 failure decision, then only new L2/L3
escalation decisions as thresholds are crossed, followed by one recovery
decision. A decision is marked delivered only after the SMS transport confirms
it; until then, it remains pending. SMS delivery is added in the next stage.

## Developing

1. Clone this repository
2. Install dependencies with `pip install .`
3. Increase the version under `extension/extension.yaml` after modifications
4. Run `dt-sdk build`

## Structure

### url_sms_plugin folder

Contains the python code for the extension

### extension folder

Contains the yaml and activation definitions for the framework v2 extension

### setup.py

Contains dependency and other python metadata

### activation.json

Used during simulation only, contains the activation definition for the extension
