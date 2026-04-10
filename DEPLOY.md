# Deployment guide

Temporary deployment of the wedding uploader on a Debian VM, exposed via Cloudflare Tunnel.
Intended to be stood up for an event and torn down cleanly afterwards.

## Prerequisites

- Debian VM with Docker + `docker compose` installed
- A domain managed by Cloudflare (free plan is fine)
- `cloudflared` installed on the VM

## Setup

### 1. Clone and configure the app

```bash
git clone <repo-url> wedding-photo-uploader
cd wedding-photo-uploader
cp .env.example .env
nano .env   # set UPLOAD_PIN, ADMIN_PIN, SESSION_SECRET
```

### 2. Start the container

```bash
docker compose up -d --build
curl -I http://localhost:8000   # should return 200/302
```

Uploads and the SQLite DB live in the mounted `./data` directory — back this up after the event.

### 3. Create the Cloudflare tunnel

```bash
cloudflared tunnel login                                  # opens browser, pick your zone
cloudflared tunnel create wedding                         # note the tunnel ID
cloudflared tunnel route dns wedding photos.example.com   # creates the CNAME automatically
```

### 4. Write the tunnel config

`~/.cloudflared/config.yaml`:

```yaml
tunnel: <tunnel-id>
credentials-file: /home/<user>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: photos.example.com
    service: http://localhost:8000
    originRequest:
      connectTimeout: 30s
  - service: http_status:404
```

### 5. Install as a systemd service

`sudo` resets `$HOME` to `/root`, so you must point it at your config explicitly:

```bash
sudo cloudflared --config ~/.cloudflared/config.yaml service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

### 6. Verify Cloudflare dashboard settings

For the hostname `photos.example.com`:

- **DNS** → CNAME exists, proxy status = proxied (orange cloud)
- **SSL/TLS → Overview** → Full (not Flexible)
- **Caching → Cache Rules** → Bypass cache for this hostname
- **Speed → Optimization** → Rocket Loader Off (via Configuration Rule) for this hostname
- **Security → Settings** → Security Level Medium or Low

### 7. Smoke test

From **mobile data** (not your home wifi — that would go direct, bypassing the tunnel):

1. Open `https://photos.example.com`
2. Log in with `UPLOAD_PIN`
3. Upload a large (500 MB+) video, kill wifi mid-upload, reconnect → tus should resume
4. Log in as admin with `ADMIN_PIN`, try the "Download all as ZIP" button

Print a QR code pointing at the URL and you're done.

## Teardown

Goal: stop exposing the homelab to the internet, keep `cloudflared` installed for next time,
and preserve uploaded photos.

### 1. Back up the data first

```bash
cd ~/wedding-photo-uploader
tar czf ~/wedding-backup-$(date +%F).tar.gz data/
# copy off the VM to somewhere safe before proceeding
```

### 2. Stop and disable the tunnel service

```bash
sudo systemctl disable --now cloudflared
sudo systemctl status cloudflared   # should be inactive + disabled
sudo cloudflared service uninstall   # removes the systemd unit, keeps the binary
```

At this point the tunnel is no longer running — the public URL will return a Cloudflare error.
This is the critical step for closing the exposure.

### 3. Delete the tunnel from Cloudflare

```bash
cloudflared tunnel delete wedding
```

If it complains about active connections, wait ~30s for Cloudflare's edge to notice the tunnel
is gone, or pass `-f`.

### 4. Remove the DNS record

The `tunnel route dns` command created a CNAME that is now orphaned. Delete it:

- Cloudflare dashboard → your domain → **DNS** → delete the `photos` CNAME
- Also remove any Configuration/Cache Rules you added for that hostname

### 5. Stop and remove the app container

```bash
cd ~/wedding-photo-uploader
docker compose down
# Optional — wipes the image too:
docker compose down --rmi local
```

### 6. (Optional) Clean up local config

```bash
rm ~/.cloudflared/config.yaml
rm ~/.cloudflared/<tunnel-id>.json
# keep cert.pem — it's your Cloudflare origin cert, reusable for the next tunnel
```

### 7. Verify nothing is still exposed

```bash
sudo systemctl status cloudflared     # inactive
sudo ss -tlnp | grep -E '8000|cloudflared'   # only the local docker bind should remain, if any
curl -I https://photos.example.com    # should fail / 530 / NXDOMAIN
```

If all three look clean, the homelab is no longer reachable from the internet.
