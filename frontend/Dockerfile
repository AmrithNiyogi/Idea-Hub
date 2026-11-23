# syntax=docker/dockerfile:1
# Idea Hub frontend: Vite build served by nginx, which also proxies /api and
# /uploads to the backend so the browser sees a single origin. Build context: frontend/
#   docker build -t ideahub-web frontend/
#   docker run -p 8080:8080 -e API_UPSTREAM=https://<api-host> ideahub-web

FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Leave empty for same-origin /api/v1 (the nginx proxy handles it).
ARG VITE_API_BASE_URL=""
ARG VITE_MICROSOFT_AUTH_ENABLED=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_MICROSOFT_AUTH_ENABLED=$VITE_MICROSOFT_AUTH_ENABLED

RUN npm run build


FROM nginx:alpine AS runtime

# The official nginx image renders *.template files in this directory with
# envsubst at startup, writing the result to /etc/nginx/conf.d/.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# Defaults for local use. On Cloud Run, PORT is injected and API_UPSTREAM is set on the service.
ENV PORT=8080 \
    API_UPSTREAM=http://host.docker.internal:8000

EXPOSE 8080
