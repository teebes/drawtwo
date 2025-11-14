# Production Deployment Guide


## Build

The frontend bundle needs the public Google client ID at build time (Vite inlines
`VITE_GOOGLE_CLIENT_ID`). Export it in your shell before kicking off the build:

```bash
export VITE_GOOGLE_CLIENT_ID="1234567890-abcdef.apps.googleusercontent.com"
make build-prod
```

If you prefer to run the `docker build` commands manually, pass the build arg:

```bash
docker build -t teebes/drawtwo-backend:latest ./backend
docker build -t teebes/drawtwo-frontend:latest \
  -f frontend/Dockerfile.production \
  --build-arg VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
  ./frontend

docker push teebes/drawtwo-backend:latest
docker push teebes/drawtwo-frontend:latest
```

## Bring up everything

```
docker compose -f docker-compose.production.yml --env-file production.env up -d
```


## Refresh Frontend

```
dc pull frontend
dc up -d frontend
```


## Stop

```
docker compose -f docker-compose.production.yml --env-file production.env down -d
```

## Get a backend bash

```
docker compose -f docker-compose.production.yml --env-file production.env exec backend bash
```

## Refresh frontend

```
docker compose -f docker-compose.production.yml --env-file production.env pull frontend
docker compose -f docker-compose.production.yml --env-file production.env up -d frontend
```

## Migrate / CollectStatic

```
docker-compose -f docker-compose.production.yml --env-file production.env exec backend python manage.py migrate

docker-compose -f docker-compose.production.yml --env-file production.env exec backend python manage.py collectstatic --noinput
```
