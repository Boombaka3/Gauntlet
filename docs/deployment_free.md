# Free Tier Deployment

## Services and costs

| Service | Provider | Cost | Link |
|---|---|---|---|
| Django web | Render | Free (sleeps after 15min) | render.com |
| PostgreSQL | Neon | Free (0.5 GB) | neon.tech |
| File storage | Cloudflare R2 | Free (10 GB) | cloudflare.com/r2 |
| LLM inference | Groq | Free (1000 req/day) | console.groq.com |
| Redis | Not needed for demo | -- | -- |
| Celery worker | Not needed for demo | -- | -- |

Total: $0/month for portfolio demo.

## Groq setup (5 min)
1. Create account: https://console.groq.com
2. Create API key in Settings -> API Keys
3. Set in Render env vars: OPENAI_API_KEY=your_groq_key
4. Model: llama-3.3-70b-versatile

## Neon PostgreSQL setup (5 min)
1. Create account: https://neon.tech
2. Create project: evidencetrace
3. Copy connection string -> DATABASE_URL in Render

## Cloudflare R2 setup (10 min)
1. Create account: https://cloudflare.com
2. R2 -> Create bucket: evidencetrace-prod
3. Settings -> API tokens -> Create R2 token
4. Set MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY in Render
   (R2 is S3-compatible, same boto3 code works)

## Render deployment (10 min)
1. Create account: https://render.com
2. New -> Web Service -> Connect GitHub repo
3. Root directory: llm_eval_harness
4. Environment: Docker
5. Set environment variables from above
6. Deploy

## After first deploy (in Render shell)
python manage.py migrate_schemas
python scripts/create_admin.py

Note the API key printed by create_admin.py.
Add tenant domain:
python manage.py shell
from apps.core.models import Tenant, Domain
t = Tenant.objects.get(schema_name="demo")
Domain.objects.get_or_create(
  domain="your-app.onrender.com",
  tenant=t,
  defaults={"is_primary": False}
)

## Limitations of free tier
- Render free: spins down after 15 minutes of inactivity
  First request after sleep takes 30-60 seconds to wake
  Acceptable for portfolio demo
- Groq free: 1000 requests/day
  225 LLM calls per 2-paper job = ~4 jobs/day on free tier
  Use sync dispatch (/dispatch-sync/) for demo -- fewer LLM calls
- Neon free: 0.5 GB storage
  Enough for hundreds of analysis jobs
