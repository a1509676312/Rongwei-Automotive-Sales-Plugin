# Rongwei Automotive Sales — DeepSeek Harness bundle

This directory contains the native DeepSeek Harness integration. It is separate from the Python provider adapter.

## What this integration does

- Registers `rongwei_sales_analyze` in the Harness tool registry.
- Accepts buyer/seller conversation text plus optional advertisement, vehicle, requirement, and follow-up context.
- Returns a structured evidence brief and automotive-export sales playbook to the active Harness model.
- The Harness model performs the semantic reasoning and writes the user-facing analysis.

The plugin does not call the DeepSeek API itself, does not require a second API key, and does not send customer messages. The active Harness model is the reasoning model. The Python adapter in `src/rongwei_plugin/providers/deepseek.py` remains a separate integration path for external Python callers and other host platforms.

## Package

- `package.json`: DSH bundle manifest.
- `cordis.patch.yml`: mounts the plugin into a Harness profile.
- `index.js`: registers the native model-callable tool.

## Local installation

The exact command depends on the user's installed Harness CLI and profile name. Follow the official Harness package-and-install guide. For a local checkout, the expected shape is:

```powershell
dsh plugin --profile <profile-name> add .\harness
dsh --profile <profile-name> --dump-config
```

Do not run this until the Harness CLI/profile has been identified and the package has been tested against that runtime.

## Safety and acceptance

The tool returns a brief; it does not claim that the analysis has been independently verified. Before release, test:
- plugin loading and tool registration in a disposable Harness profile;
- model tool invocation from the Harness UI;
- all six synthetic sales cases;
- missing/conflicting vehicle and advertisement information;
- no fabricated price, specifications, stock, logistics, payment, or delivery claims;
- natural buyer-language reply drafts with Chinese explanations;
- no automatic message sending.

The plugin runs as trusted Harness host code. Review source before installation and pin a reviewed version/commit when distributing it.
