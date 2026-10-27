# Security policy

## Report a vulnerability
Please don't open a public issue for a security problem.

Report it privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability**.
Include what you found, how to reproduce it, and what an attacker could do with it.

You'll get an answer within 7 days. Once a fix is ready, it's released and the report is credited to you unless you
prefer otherwise.

## Supported versions
DubEval is in beta. Security fixes go into the latest release (the desktop app updates itself) and `main`.

## Scope
Especially relevant:
- the REST API (`qa.py serve`): authentication with `DUBEVAL_API_TOKEN`, and the rule that without a token it
  listens only on 127.0.0.1;
- handling of API keys (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`): they must never be logged, printed, written to
  reports or sent anywhere but their own provider;
- files and links from users: paths, downloads and job ids;
- the desktop app: its local web page (one random token per launch) and its updates, which come only from this
  repository's Releases (the installer isn't code-signed yet).
