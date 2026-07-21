# Security

This project is designed for **local-first** use.

- Default policy blocks non-local LLM endpoints (`allow_cloud: false`).
- Filesystem access is limited to `allowed_roots`.
- Create `.kill_switch` in the working directory to halt agent runs immediately.

Do not set `allow_cloud: true` or broaden `allowed_roots` unless you accept the risk.

Report issues via your fork's issue tracker.
