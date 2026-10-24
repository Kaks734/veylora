# Public source privacy

The clean upload package contains source, synthetic tests, static UI and documentation only. The author's intentional name, Denis Kiriaku, is retained for attribution and copyright.

## Never add to the public repository
- Router login passwords or other account credentials.
- Cookies, session/security tokens, authenticated request exports or HAR files.
- Real device names, MAC addresses, user-specific device lists or router backups.
- Screenshots containing private network data or credentials.
- Your local application-data folder, labels.json, monitor.json or environment files.
- Private keys, signing certificates or local logs.

The application asks each user for their own runtime values; these fields and protocol field names in source are not embedded credentials. Test values and localhost URLs are intentionally public examples.

The clean source package does not erase copies or captures elsewhere on your computer, rotate previous session tokens or rewrite any Git history. Review any files you add later. Use `git diff --cached` before the first commit. `.gitignore` does not remove files already tracked by Git.
