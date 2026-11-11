# Web image: build the Vite bundle with Node, serve it with nginx (which also proxies /api).
FROM node:22-slim AS build
WORKDIR /web
COPY package.json package-lock.json ./
# Optional corporate-proxy CA, as in docker/api.Dockerfile.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci
COPY . .
# Typecheck + bundle. The API types are generated from api/openapi.json and committed.
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
