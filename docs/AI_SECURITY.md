# AI Security in the Metadata Harmonisation Tool

This document maps each AI-related safeguard in the Metadata Harmonisation Tool to the specific problem it prevents.

For a quick mnemonic version, see the **AI Security at a Glance** section in the main [`README.md`](../README.md).

---

## 1. API keys kept in memory only

**Prevents:** Key leakage via backups, screenshots, log files, or accidental commits.

**Real risk:** If your OpenAI key is saved to a file or log, anyone who gains access to your machine, GitHub repo, or cloud backup can run AI calls on your account.

**Safeguard:** The tool reads keys into session state and never writes them to `results/`, `logs/`, or `.env` from the UI.

---

## 2. API key format validation

**Prevents:** Sending garbage or wrong keys to the provider.

**Real risk:** A malformed key triggers an API error that could expose internal stack traces, or a user might paste a different secret (e.g., an SSH key) into the wrong field.

**Safeguard:** Regex checks for OpenAI, Anthropic, and Azure key patterns before any network call.

---

## 3. Rate limiting (60 requests per minute)

**Prevents:** Accidental quota burn and provider throttling/bans.

**Real risk:** A bug, a stuck button, or a loop could fire hundreds of AI requests in seconds, costing money or getting your API key suspended.

**Safeguard:** The wrapper tracks timestamps and raises an error if the cap is exceeded.

---

## 4. Request timeouts (30 seconds)

**Prevents:** Hung processes and resource exhaustion.

**Real risk:** A slow provider or dead network connection could leave the app waiting indefinitely, blocking the UI and wasting server threads.

**Safeguard:** Each call runs in a thread pool with a hard timeout.

---

## 5. Retry with exponential backoff

**Prevents:** Provider throttling and transient failures from causing data loss.

**Real risk:** Immediately retrying over and over can trigger anti-abuse limits or bury real errors.

**Safeguard:** Up to 3 retries with increasing delays (`1s`, `2s`, `4s`).

---

## 6. Sanitized error messages

**Prevents:** Information disclosure to end users.

**Real risk:** A raw error might reveal file paths, internal URLs, model names, or fragments of your API key.

**Safeguard:** Full errors go to the backend log; the UI shows a generic message.

---

## 7. Audit trail without secrets

**Prevents:** Sensitive data leakage through logs and supports compliance.

**Real risk:** An audit log is useful for accountability, but if it stores API keys or raw transformation instructions with PII, it becomes a liability.

**Safeguard:** The log records operator, timestamp, provider name, and mapping values — never the API key. Transformation instructions are stored as a SHA-256 hash.

---

## 8. File locking on results writes

**Prevents:** Data corruption from concurrent saves.

**Real risk:** If two users or two browser tabs save a mapping at the same time, one write can overwrite or corrupt the CSV.

**Safeguard:** `fcntl` exclusive locks are used on Unix/Linux.

---

## 9. Transformation expression sandboxing

**Prevents:** Code injection / remote code execution.

**Real risk:** A transformation formula is evaluated by the app. If arbitrary Python is allowed, someone could run `__import__('os').system('rm -rf /')` or read local files.

**Safeguard:** Only the variable `x` and the operators `+`, `-`, `*`, `/` are permitted.

---

## 10. Length limits on parsed strings

**Prevents:** Denial-of-service (DoS) via oversized input.

**Real risk:** A malformed or huge value in a CSV could crash the parser or consume excessive memory.

**Safeguard:** String deserialization is capped at 10,000 characters.

---

## 11. Environment variable guard

**Prevents:** `.env` file corruption and injection.

**Real risk:** A bug or malicious input could rewrite your `.env`, inject new keys, or delete critical settings.

**Safeguard:** `modify_env()` validates key names and uses exact-match replacement.

---

## Bottom line

| If you are worried about... | The relevant safeguard is... |
|----------------------------|------------------------------|
| Someone stealing your API key | Memory-only keys + no secrets in logs |
| Accidental huge AI bill | Rate limiting + timeouts + retries |
| Malicious user input | Expression sandbox + length limits + `.env` guard |
| Losing track of who changed what | Append-only audit trail |
| Data corruption | File locking on writes |
| Leaking internal details | Sanitized error messages |

These are mostly **defensive** measures: they reduce the damage from mistakes, bugs, and casual misuse rather than stopping determined attackers.
