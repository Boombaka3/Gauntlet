# Deployment Guide

---

## Railway deployment (fast path -- 30 min)

### Prerequisites
- Docker image builds locally (`docker build .` succeeds)
- All env vars from `.railway.env.example` are ready to fill in

### Steps

1. Install Railway CLI:
   ```
   npm install -g @railway/cli
   ```

2. Authenticate:
   ```
   railway login
   ```

3. Initialize a new Railway project from the repo root:
   ```
   railway init
   ```

4. In the Railway dashboard, add a **PostgreSQL** plugin to the project.
   Railway auto-injects `DATABASE_URL` into your service.

5. In the Railway dashboard, add a **Redis** plugin to the project.
   Railway auto-injects `REDIS_URL` into your service.

6. Set all remaining env vars from `.railway.env.example` in the Railway
   dashboard under **Variables**. Fill in every blank value. Do not set
   `DATABASE_URL` or `REDIS_URL` manually -- Railway manages those.

7. Deploy:
   ```
   railway up
   ```
   Railway builds the Dockerfile, runs `docker-entrypoint.sh` (migrate +
   collectstatic + create_admin), and starts gunicorn. The health check at
   `/api/health/` must return 200 before traffic is routed.

8. After the first successful deploy, seed the admin user and print the
   API key:
   ```
   railway run python scripts/create_admin.py
   ```
   Copy the printed API key -- this is your `X-API-Key` for all protected
   endpoints.

9. Note your deployed URL (e.g. `https://your-app.up.railway.app`).

10. Register the tenant domain so the multi-tenant middleware resolves
    requests correctly:
    ```
    railway run python manage.py shell
    ```
    Then in the shell:
    ```python
    from apps.core.models import Tenant, Domain
    tenant = Tenant.objects.get(schema_name="demo")
    Domain.objects.get_or_create(
        domain="demo.your-app.up.railway.app",
        tenant=tenant,
        defaults={"is_primary": True},
    )
    ```

---

## AWS production architecture

### Local to AWS mapping

| Local component          | AWS equivalent                                              |
|--------------------------|-------------------------------------------------------------|
| PostgreSQL container     | RDS PostgreSQL 16 (db.t3.micro, free tier 12 months)        |
| Redis container          | ElastiCache Redis 7 (cache.t3.micro)                        |
| MinIO                    | S3 native (update MINIO_ENDPOINT to s3.amazonaws.com)       |
| Django app container     | ECS Fargate app task                                        |
| Celery container         | ECS Fargate worker task                                     |
| docker-compose.yml       | ECS Task Definitions                                        |
| .env file                | AWS Secrets Manager                                         |
| Port 8000                | ALB -> HTTPS -> ECS                                         |

### Deployment steps (overview)

1. Push the Docker image to ECR.
2. Create an ECS cluster and two task definitions: one for the Django app
   (runs docker-entrypoint.sh + gunicorn), one for the Celery worker
   (runs `celery -A config worker --pool=solo`).
3. Create an RDS PostgreSQL 16 instance. Note the connection string.
4. Create an ElastiCache Redis 7 cluster. Note the endpoint.
5. Create an S3 bucket. Update `MINIO_ENDPOINT` to `s3.amazonaws.com` and
   set `MINIO_BUCKET` to the bucket name. AWS SDK uses the same boto3 client.
6. Store all secrets in AWS Secrets Manager and inject them as environment
   variables into the ECS task definitions.
7. Create an Application Load Balancer with an HTTPS listener (ACM cert).
   Target group points to the app ECS service on port 8000.
8. Set `DJANGO_ALLOWED_HOSTS` to the ALB domain and any custom domain.

### Estimated monthly cost

| Service              | Size               | Cost                        |
|----------------------|--------------------|------------------------------|
| RDS PostgreSQL       | db.t3.micro        | Free 12 mo then ~$15/mo      |
| ElastiCache          | cache.t3.micro     | ~$12/mo                      |
| ECS Fargate app      | 0.25 vCPU 512 MB   | ~$8/mo                       |
| ECS Fargate worker   | 0.25 vCPU 512 MB   | ~$8/mo                       |
| ALB                  | -                  | ~$16/mo                      |
| S3                   | 5 GB               | <$1/mo                       |
| **Total**            |                    | **~$60/mo (free first year)**|

### Shut down instructions

**Railway:**
```
railway down
```

**AWS:**
1. Stop or delete the ECS services (set desired count to 0).
2. Stop the RDS instance (or create a final snapshot and delete it).
3. Delete the ElastiCache cluster.
4. Remove the ALB and target group.
5. Deregister task definitions (optional -- no charge when not running).
