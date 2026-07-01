# AFDAS Deployment Guide — Vercel + Render (Free Tier)

## Architecture

```
Users → Vercel (React frontend) → Render (FastAPI backend) → Render PostgreSQL + Redis
```

---

## Step 1: Deploy Backend on Render

### Option A: One-Click Blueprint (Recommended)

1. Go to https://render.com/deploy
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repo: `b24es1012-alt/afdas`
4. Select branch: `feat/afdas-backend`
5. Render reads `render.yaml` and creates all services automatically:
   - Web Service (FastAPI)
   - PostgreSQL database
   - Redis cache

### Option B: Manual Setup

#### 1.1 Create PostgreSQL Database

1. Render Dashboard → **New** → **PostgreSQL**
2. Settings:
   - Name: `afdas-db`
   - Database: `afdas`
   - User: `afdas_user`
   - Plan: **Free**
   - Region: Oregon (closest to India traffic)
3. Click **Create Database**
4. Copy the **Internal Connection String** (you'll need it)

> **Note**: Render free PostgreSQL does NOT include PostGIS extension.
> You need to run: `CREATE EXTENSION postgis;` after creation.
> If PostGIS is unavailable on free tier, flood polygon spatial queries will fail.
> Alternative: Use Supabase (free PostGIS) or Neon.

#### 1.2 Create Redis

1. Render Dashboard → **New** → **Redis**
2. Settings:
   - Name: `afdas-redis`
   - Plan: **Free** (25MB)
   - Eviction Policy: `allkeys-lru`
3. Click **Create Redis**
4. Copy the **Internal Redis URL**

#### 1.3 Create Web Service (Backend)

1. Render Dashboard → **New** → **Web Service**
2. Connect GitHub repo: `b24es1012-alt/afdas`
3. Settings:
   - Name: `afdas-backend`
   - Branch: `feat/afdas-backend`
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: **Free**
4. Environment Variables:

```
AFDAS_ENV=production
DEBUG=false
DB_HOST=<from postgres internal hostname>
DB_PORT=5432
DB_NAME=afdas
DB_USER=afdas_user
DB_PASSWORD=<from postgres password>
REDIS_HOST=<from redis internal hostname>
REDIS_PORT=6379
GROQ_API_KEY=gsk_your_groq_api_key_here
JWT_SECRET_KEY=<generate: openssl rand -hex 32>
COPERNICUS_AUTO_IMPORT=true
COPERNICUS_WATCH_COUNTRIES=India
CORS_ORIGINS=https://your-app.vercel.app
```

5. Click **Create Web Service**

#### 1.4 Initialize Database Schema

After the database is created, connect and run the schema:

```bash
# Connect to Render PostgreSQL (use External Connection String)
psql "your-external-connection-string"

# Enable PostGIS (if available)
CREATE EXTENSION IF NOT EXISTS postgis;

# Run init.sql
\i database/init.sql
```

Or use the Render Shell:
1. Go to your Web Service → **Shell**
2. Run:
```bash
python -c "
import asyncio
from database.connection import DatabaseManager
asyncio.run(DatabaseManager.initialize())
print('DB initialized')
"
```

---

## Step 2: Deploy Frontend on Vercel

#### 2.1 Prepare Frontend

The frontend needs to know the backend URL. Create/update the `.env.production`:

```bash
VITE_API_BASE_URL=https://afdas-backend.onrender.com/api/v1
```

#### 2.2 Deploy to Vercel

1. Go to https://vercel.com/new
2. Import GitHub repo: `b24es1012-alt/afdas`
3. Settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `.` (or `./` — the frontend is the root on `feat/afdas-frontend` branch)
   - **Branch**: `feat/afdas-frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Environment Variables:
   ```
   VITE_API_BASE_URL=https://afdas-backend.onrender.com/api/v1
   ```
5. Click **Deploy**

#### 2.3 Update CORS on Backend

After Vercel gives you your domain (e.g., `afdas-frontend.vercel.app`):

1. Go to Render → afdas-backend → Environment
2. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://afdas-frontend.vercel.app,https://your-custom-domain.com
   ```
3. The service will auto-redeploy

---

## Step 3: Post-Deployment Setup

### 3.1 Create Admin User

1. Register normally on the website
2. Connect to database and promote:
```sql
UPDATE users SET role = 'admin' WHERE email = 'your-email@example.com';
```

### 3.2 Initialize Database Schema

Run the `init.sql` to create all tables:

```sql
-- Connect to your Render PostgreSQL (external URL) and run:
-- Copy contents of database/init.sql
```

### 3.3 Import Test Flood Data (Optional)

Via the admin panel or API:
```bash
curl -X POST https://afdas-backend.onrender.com/api/v1/flood/download \
  -H "Authorization: Bearer <your-admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"activation_id": "EMSR838", "event_name": "Test Flood", "country": "India", "region": "Delhi"}'
```

---

## Free Tier Limitations & Workarounds

| Issue | Impact | Workaround |
|-------|--------|------------|
| Render sleeps after 15min | First request slow (~30s cold start) | Use a cron job to ping /health every 14min |
| Render PostgreSQL: 90-day limit | Database deleted after 90 days | Backup regularly, or use Supabase/Neon |
| Render Redis: 25MB, 30-day limit | Cache gets deleted | App works without cache (just slower) |
| No PostGIS on Render free PG | Spatial queries fail | Use Supabase (has PostGIS free) |
| 512MB RAM on Render free | Large graph downloads may OOM | Limit cities, use smaller OSMnx queries |

### Recommended: Use Supabase for PostgreSQL

Render's free PostgreSQL doesn't include PostGIS. **Supabase** (free tier) includes PostGIS:

1. Create account at https://supabase.com
2. New Project → get connection string
3. Run `database/init.sql` in Supabase SQL Editor
4. Update Render env vars with Supabase connection details

---

## Keep Backend Awake (Prevent Sleep)

Use a free cron service to ping your backend every 14 minutes:

### Option 1: cron-job.org (free)
1. Go to https://cron-job.org
2. Create job: `GET https://afdas-backend.onrender.com/health`
3. Schedule: Every 14 minutes

### Option 2: UptimeRobot (free)
1. Go to https://uptimerobot.com
2. Add monitor: HTTP(s)
3. URL: `https://afdas-backend.onrender.com/health`
4. Interval: 5 minutes

---

## Custom Domain (Optional)

### Vercel (Frontend)
1. Vercel Dashboard → Project → Settings → Domains
2. Add your domain (e.g., `afdas.app`)
3. Update DNS records as Vercel shows

### Render (Backend)
1. Render Dashboard → Web Service → Settings → Custom Domains
2. Add `api.afdas.app`
3. Update DNS CNAME record

Then update:
- Frontend `.env`: `VITE_API_BASE_URL=https://api.afdas.app/api/v1`
- Backend `CORS_ORIGINS`: `https://afdas.app`

---

## Environment Variables Summary

### Backend (Render)

| Variable | Value | Required |
|----------|-------|----------|
| `AFDAS_ENV` | `production` | Yes |
| `DEBUG` | `false` | Yes |
| `DB_HOST` | From Render PostgreSQL | Yes |
| `DB_PORT` | `5432` | Yes |
| `DB_NAME` | `afdas` | Yes |
| `DB_USER` | `afdas_user` | Yes |
| `DB_PASSWORD` | From Render PostgreSQL | Yes |
| `REDIS_HOST` | From Render Redis | Yes |
| `REDIS_PORT` | `6379` | Yes |
| `GROQ_API_KEY` | From https://console.groq.com | Yes |
| `JWT_SECRET_KEY` | Random 64-char string | Yes |
| `CORS_ORIGINS` | Your Vercel URL | Yes |
| `COPERNICUS_AUTO_IMPORT` | `true` | No |
| `COPERNICUS_WATCH_COUNTRIES` | `India` | No |

### Frontend (Vercel)

| Variable | Value | Required |
|----------|-------|----------|
| `VITE_API_BASE_URL` | `https://afdas-backend.onrender.com/api/v1` | Yes |

---

## Troubleshooting Deployment

### Backend not starting
- Check Render logs for import errors
- Common: missing `libgdal-dev` → use Dockerfile instead of native Python
- If geospatial deps fail, try Docker deployment on Render

### Frontend 404 on refresh
- Add `vercel.json` with rewrites (see below)
- This is needed for React Router (SPA routing)

### CORS errors
- Make sure `CORS_ORIGINS` exactly matches your Vercel URL (with https, no trailing slash)
- Check browser console for the exact origin being blocked

### PostGIS not available
- Render free PG doesn't have PostGIS
- Use Supabase (free PostGIS) or upgrade Render PG

---

## Files Created for Deployment

| File | Purpose |
|------|---------|
| `render.yaml` | Render Blueprint (auto-creates all services) |
| `Dockerfile` | Docker build for Render (handles geospatial deps) |
| `DEPLOYMENT.md` | This guide |
