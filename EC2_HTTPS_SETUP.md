# EC2 HTTPS Setup with Let's Encrypt

## Overview

This guide sets up free HTTPS on your EC2 backend using Let's Encrypt and Certbot with nginx.

**Domain:** `studio-sabin-jobs.click`
**EC2 IP:** `54.237.223.146`

---

## Prerequisites

✅ Domain is registered and pointing to EC2 IP (via Route 53 A record)
✅ EC2 security group allows ports 80 and 443 inbound
✅ nginx is already running on EC2

---

## Step 1: Verify Prerequisites

### 1A: Check EC2 Security Group

1. AWS Console → EC2 → Security Groups
2. Find the security group for your `jobtracker-ec2` instance
3. Verify **Inbound rules** include:
   ```
   Protocol: TCP, Port: 80, Source: 0.0.0.0/0 (HTTP)
   Protocol: TCP, Port: 443, Source: 0.0.0.0/0 (HTTPS)
   ```
4. If missing, add them

### 1B: Verify Domain Points to EC2

From your terminal:
```bash
nslookup studio-sabin-jobs.click
# Should return: 54.237.223.146
```

Wait for DNS propagation if needed (5-30 minutes after domain registration).

### 1C: SSH into EC2

```bash
ssh -i your-key-pair.pem ec2-user@54.237.223.146
```

---

## Step 2: Install Certbot

On the EC2 instance:

```bash
# Update package manager
sudo yum update -y

# Install certbot and nginx plugin
sudo yum install certbot python3-certbot-nginx -y
```

---

## Step 3: Get SSL Certificate from Let's Encrypt

Replace `studio-sabin-jobs.click` with your actual domain:

```bash
sudo certbot certonly --standalone \
  -d studio-sabin-jobs.click \
  --agree-tos \
  -m admin@studio-sabin-jobs.click
```

**What this does:**
- `--standalone`: Uses a temporary web server (doesn't interfere with nginx)
- `-d studio-sabin-jobs.click`: Domain to get certificate for
- `--agree-tos`: Automatically agree to Let's Encrypt terms
- `-m admin@studio-sabin-jobs.click`: Email for certificate renewal notifications

**Output will show:**
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/studio-sabin-jobs.click/fullchain.pem
Key is saved at: /etc/letsencrypt/live/studio-sabin-jobs.click/privkey.pem
```

---

## Step 4: Configure nginx to Use HTTPS

Edit your nginx config:

```bash
sudo nano /etc/nginx/nginx.conf
```

Replace the `server` block with this configuration:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name studio-sabin-jobs.click;
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name studio-sabin-jobs.click;

    # SSL certificates from Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/studio-sabin-jobs.click/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/studio-sabin-jobs.click/privkey.pem;

    # SSL configuration (recommended)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Proxy to FastAPI backend (localhost:8000)
    location /api {
        proxy_pass http://localhost:8000/api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Save and exit: `Ctrl+X` → `Y` → `Enter`

---

## Step 5: Restart nginx

```bash
sudo systemctl restart nginx
```

Verify it's running:
```bash
sudo systemctl status nginx
```

---

## Step 6: Verify HTTPS Works

From your terminal (off the EC2):

```bash
curl -v https://studio-sabin-jobs.click/api/dashboard/metrics?days=7
```

You should see:
```
< HTTP/2 200
< content-type: application/json
{
  "total_jobs_discovered": 0,
  ...
}
```

If you see certificate warnings, that means nginx is using the cert but curl isn't trusting it yet (this is normal during initial setup).

---

## Step 7: Set Up Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up automatic renewal:

```bash
# Test renewal (dry run)
sudo certbot renew --dry-run

# Enable auto-renewal
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer

# Verify it's running
sudo systemctl status certbot-renew.timer
```

---

## Step 8: Update Vercel Environment Variable

**Only do this AFTER you've verified HTTPS is working.**

1. Vercel Dashboard → JobApplicationTracker → Settings → Environment Variables
2. Update `BACKEND_API_URL`:
   ```
   OLD: http://54.237.223.146
   NEW: https://studio-sabin-jobs.click
   ```
3. Redeploy:
   ```bash
   git push origin master
   ```

---

## Troubleshooting

### Certificate Not Issued

If certbot fails, check:

```bash
# Verify domain resolves
nslookup studio-sabin-jobs.click

# Check nginx is not blocking port 80
sudo netstat -tlnp | grep :80

# Try with verbose output
sudo certbot certonly --standalone -d studio-sabin-jobs.click -v
```

### nginx Fails to Restart

```bash
# Check syntax
sudo nginx -t

# View logs
sudo journalctl -u nginx -n 50
```

### Can't Reach Backend via HTTPS

```bash
# Check nginx is listening on 443
sudo netstat -tlnp | grep :443

# Check FastAPI is still running on localhost:8000
curl http://localhost:8000/api/dashboard/metrics
```

---

## Summary

After completing these steps:

✅ Frontend (Vercel) calls HTTPS backend
✅ No more mixed-content warnings
✅ SSL/TLS encryption between Vercel and EC2
✅ Certificate auto-renews every 90 days
✅ Blank page issue is FIXED!

---

## Timeline

1. **Domain registration:** ~30 min (in progress)
2. **DNS propagation:** ~10 min
3. **HTTPS setup on EC2:** ~5 min
4. **Update Vercel env var:** ~2 min
5. **Redeploy frontend:** ~2 min

**Total time: ~50 minutes**
