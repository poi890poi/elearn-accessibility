# HRD E-Learning Accessibility Tool

The  software helps those have motor or attention dysfunctions to complete E-Learning of HRD by automating complex GUI operations.

## Dependencies

### Python

[Python](https://www.python.org/) >= 3.9 is recommended.

### Selenium

[Selenium](https://www.selenium.dev/) is required as the browser automation engine and can be installed with [pip](https://pypi.org/project/pip/).

```
pip install pip --upgrade
pip install selenium
```

### Google Generative AI (optional)

[Google AI Python SDK for the Gemini API](https://github.com/google-gemini/generative-ai-python) provides AI examiner functionality.

```
pip install -U google-generativeai
```

### WebDriver

Visit [Selenium downloads section](https://www.selenium.dev/downloads/) for more information.
If you are using [Google Chrome](https://www.google.com/chrome/), it should be fine with your usual installation.
If you want to use Microsoft Edge, you need to download from [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/) and install.

## Usage

### Configuration

Rename `config_template.py` to `config.py`. Open it with a text editor and modify the following variables:
- **USERNAME**: Your account name to sign into HRD E-Learning.
- **PASSWORD**: Your password to sign into HRD E-Learning.
- **DOMAIN**: Domain name of HRD E-Learning.

### Run

```
python run.py
```
