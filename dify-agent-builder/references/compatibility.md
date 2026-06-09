# Dify compatibility notes

Checked against official Dify docs on 2026-06-09.

## App DSL

This skill emits Dify Chatflow YAML with `version: "0.3.0"` because that is the currently verified
target for the local generator and internal CSG provider wiring. Dify's current app-management docs
also describe a newer YAML DSL standard (`v0.6+`). If a target Dify instance warns that the imported
DSL is older, import it, review each node, then re-export from that Dify instance to migrate the DSL
shape before sharing broadly.

Official reference: https://docs.dify.ai/en/use-dify/workspace/app-management

## Plugin package shape

Official plugin docs still require a root `manifest.yaml`, `type: plugin`, `plugins.tools` pointing
to a provider YAML, and Python runner `3.12`. Text file paths such as provider/tool Python sources
should be package-relative paths like `provider/my_provider.py`; media assets such as icons belong
under `_assets`.

Official references:

- https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest
- https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/general-specifications

## Author and SDK version

Dify's plugin FAQ says `author` in `manifest.yaml` and `provider/*.yaml` must match. The scaffold
script writes both from the same `--author` value to avoid this class of install failure.

For private/offline installs, keep using the dependency set verified on the target server. For Dify
Marketplace submission, check the latest Marketplace rules; current FAQ notes that SDK pins below
`0.5.0` may be rejected by automated checks.

Official reference: https://docs.dify.ai/en/develop-plugin/publishing/faq/faq
