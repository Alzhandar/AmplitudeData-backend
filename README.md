# AmplitudeData

## Stack

- Django + PostgreSQL
- Celery + Redis
- Docker Compose

## Environment

Copy `.env.example` to `.env` and set:

- `AMPLITUDE_API_KEY`
- `AMPLITUDE_SECRET_KEY`
- `AMPLITUDE_EXPORT_URL` (default: `https://amplitude.com/api/2/export`)
- `AMPLITUDE_MOBILE_EVENT_TYPES` (optional CSV filter by event names)

## Run

```bash
docker compose up --build
```

## Production (Existing Nginx on Server)

### 1) Prepare env

Use `.env` (or copy from `.env.example`) and set at minimum:

- `DEBUG=False`
- `ALLOWED_HOSTS=your-domain.com`
- `CSRF_TRUSTED_ORIGINS=https://your-domain.com`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_HSTS_SECONDS=31536000`

### 2) Start production stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

`web` will be exposed only on `127.0.0.1:8001` to avoid conflicts with other projects.

### 3) Configure your existing nginx reverse proxy

Example server block:

```nginx
server {
	listen 80;
	server_name your-domain.com;
	return 301 https://$host$request_uri;
}

server {
	listen 443 ssl http2;
	server_name your-domain.com;

	ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
	ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

	location / {
		proxy_pass http://127.0.0.1:8001;
		proxy_set_header Host $host;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto https;
	}
}
```

### 4) Reload host nginx

```bash
nginx -t && systemctl reload nginx
```

Notes:

- `web` runs with `gunicorn` in production mode (`entrypoint.sh web-prod`).
- Static files are served by Django via WhiteNoise.

## Amplitude sync

- Celery scheduler task: `amplitude.tasks.run_scheduled_sync`
- Time is configured in Django admin: `Amplitude Sync Schedules` (`run_at`, `enabled`)
- Beat checks schedule every minute and runs sync once per day at configured time

## API

- `GET /api/amplitude/today-mobile-activity/`
- Implemented with DRF ViewSet (supports optional `?date=YYYY-MM-DD`)

Returns aggregated records for the current day:

- `device_id`
- `phone_number`
- list of visit times (`visit_times`)
- `first_seen`, `last_seen`, `visits_count`

## Frontend (Next.js)

- See frontend integration documentation: `docs/FRONTEND_NEXTJS.md`
