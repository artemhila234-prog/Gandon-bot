# WhiteGrief Control Panel — backend

FastAPI backend for the dashboard. Discord OAuth2 login is implemented, with server-side membership and role verification against the configured WhiteGrief Discord server.

## Local setup

1. Create a Discord application in the Discord Developer Portal.
2. In OAuth2 settings, add the exact redirect URL: `http://localhost:8000/auth/callback`.
3. Invite the existing WhiteGrief bot to the server if it is not already there. It must be able to view server members. Enable the Server Members Intent for the bot in the Developer Portal if required by your bot configuration.
4. Copy `.env.example` to `.env` and fill in the OAuth client ID, client secret, bot token, and a long random session secret.
5. Install and run:

```bash
cd dashboard/backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open `http://localhost:8000`.

## Access classes

- `owner`: user ID listed in `OWNER_USER_IDS`.
- `admin`, `manager`, `media`, `viewer`: assigned through `ROLE_ACCESS_MAP`.
- `none`: the user is in the server but no configured access class is assigned.

The highest matching class is used. Role IDs are intentionally left unconfigured until the server owner supplies the correct IDs.

## Media role check

Set `MEDIA_ROLE_ID` to the exact Discord role ID for the Media team. Until then, the API returns `is_media: null` (not configured), rather than incorrectly saying a user does or does not have the role.

## Security notes

- Never put the Discord bot token, OAuth client secret, or session secret in frontend files.
- Keep `.env` out of Git.
- Use HTTPS in production and keep `COOKIE_HTTPS_ONLY=true`.
- Configure a strong, unique `SESSION_SECRET`.
- The site must be hosted on a trusted server. Do not expose the backend debug mode.
- This stage only authenticates and calculates access. Sensitive management endpoints will be added with explicit permission checks in the next stages.
