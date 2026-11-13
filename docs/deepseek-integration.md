# DeepSeek integration (first provider)

This adapter connects the plugin's sales-analysis workflow to DeepSeek through its official Chat Completions API and function calling.

## Requirements

- Python 3.10+
- A DeepSeek API key created by the account owner
- Network access to the DeepSeek API
- Never paste an API key into source files, GitHub issues, screenshots, or this public repository

## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[deepseek,dev]"
```

## Configure (Windows PowerShell)

Set the key only in your local terminal session:

```powershell
$env:DEEPSEEK_API_KEY = "YOUR_REAL_API_KEY"
$env:DEEPSEEK_MODEL = "deepseek-flash"
```

Do not commit a populated `.env` file. The adapter reads `DEEPSEEK_API_KEY` from the environment. The model defaults to `deepseek-flash`; it can be overridden with `DEEPSEEK_MODEL` if the provider account supports another current model ID.

## Run a first analysis

Create a local Python file (do not put customer data in this public repository):

```python
from rongwei_plugin.providers.deepseek import analyze_case

case = {
    "language": "en",
    "source": {
        "advertisement_id": "ad-demo-001",
        "source_confidence": "confirmed"
    },
    "conversation": [
        {"speaker": "buyer", "text": "I need two SUVs for Kenya this month."},
        {"speaker": "seller", "text": "Which configuration and destination port do you need?"},
        {"speaker": "buyer", "text": "I need to confirm the right-hand-drive option and export documents."}
    ],
    "vehicles": [
        {
            "vehicle_id": "ad-demo-001",
            "make": "User supplied make",
            "model": "User supplied model",
            "verification_status": "user_provided"
        }
    ],
    "buyer_requirements": {
        "destination_country": "Kenya",
        "quantity": 2,
        "purchase_timeline": "This month"
    }
}

result = analyze_case(case)
print(result["analysis"])
print("Validation:", result["validation"])
```

Use only information that is accurate for the real case. The sample is synthetic and is not a real vehicle offer.

## What the adapter does

1. Calls DeepSeek Chat Completions using the official API base URL.
2. Exposes the plugin's `prepare_sales_analysis` function as a model-callable function tool.
3. Validates tool arguments before dispatching them to plugin code.
4. Returns the normalized conversation, vehicle/ad context, evidence rules, and sales playbook to the model.
5. Requests a JSON analysis and validates critical output invariants.
6. Returns validation errors rather than silently treating an invalid result as accepted.

The adapter does not send messages to customers and does not connect to WhatsApp, Facebook, Instagram, Telegram, or website chat.

## Run local tests

```powershell
pytest -q
```

These tests do not consume DeepSeek tokens. They test local plugin logic and tool dispatch only.

## Live acceptance still required

A live test requires the account owner's API key and a real network request. Until that test is run, this adapter is **implemented but not yet live-verified**.

The live acceptance must confirm:
- Authentication and model availability.
- Function-call request and response round trip.
- Final JSON parsing and result validation.
- Long-input behavior and truncation handling.
- No fabricated price/specification claims in the synthetic acceptance suite.
- Usage/token reporting and graceful API error handling.
