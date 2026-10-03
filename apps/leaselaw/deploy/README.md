# Deploy (ZCode-owned)

Local API must stay on **8012**. Public URL must serve `/`, `/health`, `/api/*`.

## Option A — Cloudflare quick tunnel (current)

```bash
npx cloudflared tunnel --url http://127.0.0.1:8012
# write URL to ../../docs/hn7-submission-pack/LIVE_URL.txt
```

## Option B — Docker (any host)

```bash
cd ..
docker build -t leaselaw .
docker run -p 8012:8012 \
  -v "$PWD/../../briefs/hack-nation-7-realpage-starter/participant-final-no-hour16 3":/data/starter:ro \
  -e LEASELAW_STARTER=/data/starter \
  leaselaw
```

## Option C — Wrangler (account authed)

FastAPI is not a Worker. Prefer Containers / external VM + named tunnel.  
`wrangler whoami` works on this machine (workers write scope).

After deploy: append advice to `docs/AGENT_ADVICE_LOG.md` and update `WIN_BOARD.md`.
