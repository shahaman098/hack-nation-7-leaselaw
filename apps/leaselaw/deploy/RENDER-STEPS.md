# Durable deploy (laptop can be off)

The app ships with the RealPage starter pack under `deploy/starter-pack/` so **GitHub → Render** builds work without your local `briefs/` folder.

## One-time: Render (recommended, free tier)

1. Open https://dashboard.render.com and sign in (GitHub OAuth is fine).
2. **New → Blueprint** (or **New → Web Service** if Blueprint is unavailable).
3. Connect repo **`shahaman098/hack-nation-7-leaselaw`**, branch **`main`**.
4. Render reads **`render.yaml`** at repo root:
   - Service: `leaselaw-navigator`
   - Docker context: repo root
   - Health: `/health`
5. Click **Apply** / **Create**. First build ~3–5 min.
6. Copy the URL (`https://leaselaw-navigator.onrender.com` or similar).
7. Paste it into `docs/hn7-submission-pack/LIVE_URL.txt` and HackOS.

**Verify**

```bash
curl -sS "https://YOUR-SERVICE.onrender.com/health"
curl -sS "https://YOUR-SERVICE.onrender.com/api/eval" | head
```

Expect `"passed": 5` on `/api/eval`.

### Free tier behavior

- Service **spins down** after ~15 min idle; first request after sleep may take **30–60 s** (cold start). Still fine for judges if you warn them in the demo video.
- For always-warm, upgrade plan or use a uptime ping (optional).

## Local Docker smoke test

From repo root:

```bash
docker build -f apps/leaselaw/Dockerfile -t leaselaw .
docker run --rm -p 8012:8012 -e PORT=8012 leaselaw
curl -s http://127.0.0.1:8012/api/eval
```

## Do not use for submission

- `cloudflared tunnel --url http://127.0.0.1:8012` — dies when the laptop sleeps or the tunnel stops.
