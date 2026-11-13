# Rongwei local-first customer data architecture

## User decision

Customer information is stored locally on the user's own computer or privately controlled device. The public project does not receive, host, or centrally aggregate customer records.

## Product boundary

- No Rongwei-operated customer cloud database.
- No cross-company data sharing or central customer directory.
- Each local workspace uses its own database and workspace identifier.
- AI providers receive only the context explicitly selected for a model request. Local storage does not make model-provider processing local.
- The user remains responsible for the AI provider's data terms and for choosing whether to send identifiable customer information to that provider.

## Local vault implementation (initial)

`src/rongwei_plugin/storage/local_vault.py` provides an encrypted SQLite record vault:
- AES-256-GCM authenticated encryption for each record.
- scrypt-derived key from a user passphrase (minimum 12 characters).
- Random salt and nonce; passphrase is not stored.
- Workspace identifier is authenticated as associated data.
- Customer fields and message text are encrypted together, not indexed as plaintext.
- CRUD primitives for records; schema-neutral JSON allows customer, conversation, vehicle, follow-up, and payment records.

Install the optional dependency with:

```powershell
pip install -e ".[secure-storage,dev]"
```

The vault is a storage primitive, not yet a complete end-user account or desktop application. A future UI must obtain the passphrase securely, never log it, avoid command-line arguments, and provide lock/unlock and explicit backup/export flows.

## Important security limitations

1. Local encryption does not protect data while the vault is unlocked and the application process can read it.
2. Anyone with access to the unlocked user session or process may be able to access decrypted records.
3. Backups, exports, temporary files, screenshots, swap/page files, and OS malware require separate controls.
4. Losing the passphrase means the encrypted records cannot be recovered. Provide an explicit user-controlled recovery/export process before production.
5. SQLite WAL/journal files also contain encrypted record payloads, but should be included in backup/restore procedures and protected by OS file permissions.
6. No absolute “zero leak” guarantee is possible. Do not send customer data to an AI provider without user action and provider-policy review.

## Planned next layers

- Versioned record schemas and migrations.
- Customer, conversation, vehicle/ad attribution, follow-up, and payment domain repositories.
- Search that decrypts records locally in memory without creating plaintext indexes by default.
- Explicit retention, deletion, encrypted backup, and restore.
- Host adapters (MCP, OpenAPI, Harness native) that call the same local domain services.
- Provider data minimization/redaction options and a clear per-request disclosure of what leaves the device.
- Desktop host integration: confirm the target Harness runtime's supported local-storage and filesystem APIs before claiming the Harness plugin can access this vault.

## Acceptance gates

- Database file contains no plaintext customer names, phone numbers, or message text.
- Wrong passphrase and workspace mismatch are rejected.
- Record tampering is detected by AES-GCM authentication.
- No customer data is transmitted by storage operations.
- Backup/restore and data deletion are tested before production release.
