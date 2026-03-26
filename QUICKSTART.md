# Devos Draw Two — Quick Start

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Run the project

```bash
# 1. Build all containers (first time only, takes a few minutes)
make build

# 2. Start everything
make dev
```

## First-time setup

After `make dev` is running, open a second terminal in this folder and create a superuser account:

```bash
make reset-db-with-superuser
```

## Open in your browser

| Service       | URL                          |
|---------------|------------------------------|
| Game frontend | http://localhost:3000        |
| Backend API   | http://localhost:8002        |
| Django Admin  | http://localhost:8002/admin/ |

## Stop the project

```bash
make down
```

## Head-to-Head Feature

On the Games page, each game row against a human opponent shows an **H2H** button.
Click it to see your all-time wins, losses, and draws against that player.
