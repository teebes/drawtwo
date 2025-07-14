# Production Deployment Guide


## Build

In the repo, build each project:

```
docker build -t teebes/drawtwo-backend:latest ./backend
docker build -t teebes/drawtwo-frontend:latest -f frontend/Dockerfile.production ./frontend

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
