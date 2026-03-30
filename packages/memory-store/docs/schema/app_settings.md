# app_settings

Status: Implemented.

## Purpose

Store application-wide settings blobs that are not tied to a single conversation.
The first production use is model/provider selection plus API key placeholder references.

## Columns

- `setting_key` (`TEXT PRIMARY KEY`): Stable key name (for now: `model_provider_settings_v1`).
- `setting_value` (`TEXT NOT NULL`): JSON payload for the setting.
- `updated_at` (`TEXT NOT NULL`): ISO-8601 timestamp of last update.

## Relationships

- None.

## Index notes

- `idx_app_settings_updated_at` supports "recently touched settings" diagnostics.
