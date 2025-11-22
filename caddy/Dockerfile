FROM golang:1.25-alpine as builder

RUN apk add --no-cache git

RUN go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest && \
    /go/bin/xcaddy build \
      --with github.com/caddy-dns/cloudflare

FROM caddy:latest

COPY --from=builder /xcaddy /usr/bin/caddy
