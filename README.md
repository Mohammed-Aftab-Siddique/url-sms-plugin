# url_sms_plugin extension

## Building and signing

* `dt-sdk build .`

## Running

1. Create and activate the Python 3.14 development environment: `python3.14 -m venv .venv314 && source .venv314/bin/activate`.
2. Install the project and development dependencies: `python -m pip install -e ".[dev]"`.
3. In the ignored `secrets.json`, define `smsApiPassword` and `smsApiCookieId` for the matching placeholders in `activation.json`. Do not commit real values.
4. Adjust the non-secret example values in `activation.json` as needed, then run `dt-sdk run`.

Run the stage 2 settings tests with `python -m unittest discover -s tests -v`. The extension manifest intentionally retains Python 3.10 as its minimum supported runtime.

The stage 2 implementation validates the local activation configuration and logs every configured URL. URL checks and SMS delivery are added in later stages.

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
