# EC2 Deployment Setup

Replaces ECS Fargate. Simpler: pushes to master auto-deploy via SSH.

## Step 1 — Launch the EC2 Instance (AWS Console)

1. Go to **EC2 → Launch Instance**
2. Configure:
   - **Name**: `jobtracker-api`
   - **AMI**: Amazon Linux 2023 (free-tier eligible)
   - **Instance type**: `t3.small` (2 vCPU, 2 GB RAM — within $20 credit)
   - **Key pair**: Create new → name it `jobtracker-ec2` → download `.pem` file → **keep this safe**
   - **Security group** (create new `jobtracker-ec2-sg`):
     | Type | Port | Source |
     |------|------|--------|
     | SSH  | 22   | My IP  |
     | HTTP | 80   | Anywhere (0.0.0.0/0) |
     | HTTPS | 443 | Anywhere (0.0.0.0/0) |
   - **Storage**: 20 GB gp3 (default is fine)
3. Click **Launch Instance**
4. Note the **Public IPv4 address** once it starts

## Step 2 — SSH In and Run Setup Script

```bash
# From your local machine (where you downloaded the .pem file)
chmod 400 ~/Downloads/jobtracker-ec2.pem

ssh -i ~/Downloads/jobtracker-ec2.pem ec2-user@<YOUR-EC2-IP>

# On the EC2 instance:
curl -fsSL https://raw.githubusercontent.com/sabinMas/JobApplicationTracker/master/infra/scripts/setup-ec2.sh | bash
```

## Step 3 — Configure .env

```bash
nano /opt/jobtracker/backend/.env
```

Fill in these values (copy from your local `backend/.env`):

```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@your-rds-endpoint:5432/jobtracker
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=jobtracker-documents-245091941294
ALLOWED_ORIGINS=https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app,https://frontend-six-flame-47.vercel.app
BEDROCK_FAST_MODEL=qwen.qwen3-coder-next
BEDROCK_SMART_MODEL=qwen.qwen3-coder-30b-a3b-v1:0
```

## Step 4 — Start the API

```bash
sudo systemctl start jobtracker
sudo systemctl status jobtracker

# Verify it's running:
curl http://localhost:8000/health
```

## Step 5 — Allow RDS Access

The EC2 instance needs to reach RDS. In AWS Console:

1. Go to **RDS → your database → Security groups**
2. Edit inbound rules → Add rule:
   - Type: PostgreSQL (5432)
   - Source: the EC2 security group (`jobtracker-ec2-sg`)

## Step 6 — Update Frontend API URL

In **Vercel Dashboard → Project → Settings → Environment Variables**:

```
VITE_API_URL = https://<YOUR-EC2-PUBLIC-IP>
```

Note: use `https://` with **no port** — nginx handles SSL on port 443.

Redeploy the frontend from the Vercel dashboard after saving.

## Step 7 — Wire Up GitHub Actions CD

Add these secrets in **GitHub → Settings → Secrets → Actions**:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Your EC2 public IP (e.g. `54.123.45.67`) |
| `EC2_SSH_KEY` | Contents of the `.pem` file (the whole thing including `-----BEGIN...`) |
| `VITE_API_URL` | `https://<YOUR-EC2-PUBLIC-IP>` (used by CI frontend build) |

From now on, every push to `master` that passes CI will automatically SSH into EC2 and deploy.

## Day-to-Day Operations

```bash
# SSH into server
ssh -i ~/Downloads/jobtracker-ec2.pem ec2-user@<YOUR-EC2-IP>

# View live logs
sudo journalctl -u jobtracker -f

# Manual deploy (same as what CI does)
deploy-jobtracker

# Restart service
sudo systemctl restart jobtracker

# Check status
sudo systemctl status jobtracker
```

## Why EC2 over ECS

| | ECS Fargate | EC2 |
|--|--|--|
| Deploy | Build Docker → push ECR → update service (~5 min) | `git pull && restart` (~15 sec) |
| Cost | ~$15–30/mo for t3.small equivalent | ~$15/mo (within $20 credit) |
| Debugging | Pull CloudWatch logs | `journalctl -f` on the box |
| Startup | Cold start on each new task | Always-on process |
| State | Lost on task restart | Persists (scheduler stays initialized) |
