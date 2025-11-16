# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker Compose-based media server setup that orchestrates multiple services for managing, requesting, and streaming media content. The architecture is entirely containerized, with services communicating via a shared Docker network (`media_net`).

**Key Services:**
- **Media Servers**: Jellyfin (preferred), Plex (legacy support)
- **Dashboard**: Homepage (unified dashboard with service monitoring)
- **Indexers/Downloaders**: Prowlarr (indexer), SABnzbd (usenet downloader), Radarr/Sonarr (movie/TV managers)
- **Utilities**: Bazarr (subtitles), Tautulli (Plex analytics), Recyclarr (quality profile management), JellyPlex-Watched (sync watched status)
- **Request Management**: Overseerr (Plex requests), Jellyseerr (Jellyfin requests)
- **Infrastructure**: Watchtower (auto-updates), Fail2ban (brute-force protection), Pi-hole (DNS filtering), Borgmatic (backups)

## Common Commands

### Docker Compose Basics
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View running services
docker compose ps

# Restart a specific service
docker compose restart <service_name>

# View logs for a service (follow mode)
docker compose logs -f <service_name>

# View recent logs (last 100 lines)
docker compose logs --tail=100 <service_name>

# Rebuild and restart a service after config changes
docker compose up -d --no-deps --build <service_name>
```

### Service-Specific Commands

**Recyclarr** (run on-demand to sync quality profiles):
```bash
docker compose run --rm recyclarr sync
```

**Backup Services**:
```bash
# Run borgmatic backup immediately (normally scheduled at 4 AM)
docker compose exec backup borgmatic --override create

# View backup status
docker compose exec backup borgmatic info
```

**Container Shell Access**:
```bash
# SSH into a running container
docker compose exec <service_name> sh

# For Plex (uses bash)
docker compose exec plex bash

# For Recyclarr
docker compose exec recyclarr sh
```

**Caddy** (reverse proxy - planned deployment):
```bash
# Generate basic auth password hash for admin tools
docker run --rm caddy:latest caddy hash-password

# Validate Caddyfile syntax
docker compose exec caddy caddy validate

# Check certificate status
docker compose exec caddy caddy list-certificates

# View Caddy configuration
docker compose exec caddy caddy config show

# Reload Caddyfile without downtime
docker compose exec caddy caddy reload
```

## Architecture & File Structure

### Directory Organization

Each service has a dedicated directory at `/opt/mediaserver/<service_name>/` containing:
- **config/**: Primary configuration files and databases
- **logs/**: Application logs
- **cache/**: Temporary/cache data

**Special Directories:**
- `/mnt/storage/data/`: NFS mount containing actual media files (not Docker-local)
  - `/mnt/storage/data/media/`: Media library accessed by all services
  - `/mnt/storage/data/`: Full data mount (used by downloaders/managers)
- `/mnt/backup/`: Backup destination (used by Borgmatic and rclone)

### Service Dependencies

**Download → Manage → Stream Flow:**
1. Prowlarr: Indexes available torrents/releases
2. SABnzbd: Downloads from Usenet
3. Sonarr/Radarr: Monitors for releases, triggers downloads, organizes media
4. Jellyfin/Plex: Streams organized media to clients

**Watch Sync:**
- JellyPlex-Watched: Syncs watched status between Plex and Jellyfin (runs every 5 minutes)

**Request Management:**
- Overseerr (for Plex) / Jellyseerr (for Jellyfin): Users submit requests
- Requests feed into Radarr/Sonarr for automated downloading

**Monitoring:**
- Tautulli: Tracks Plex playback and usage
- Watchtower: Auto-updates container images on schedule

## Configuration Management

### Environment Variables

All services use environment variables from `.env` file (loaded by Docker Compose):
- `PUID`/`PGID`: User ID/Group ID for consistent file permissions
- `TZ`: Timezone
- `HOST_LAN`: LAN IP address for service communication
- `HOMEPAGE_VAR_*`: Homepage dashboard widget URLs and API keys
- `BORG_PASSPHRASE`: Backup encryption passphrase
- Service tokens (Plex, Jellyfin, Radarr, Sonarr, etc.)

**Important:** Sensitive values (API keys, tokens) should be in `.env`, not in code.

### Database Locations

- **Sonarr**: `/opt/mediaserver/sonarr/sonarr.db` (SQLite)
- **Radarr**: `/opt/mediaserver/radarr/radarr.db` (SQLite)
- **Prowlarr**: `/opt/mediaserver/prowlarr/prowlarr.db` (SQLite)
- **Jellyseerr**: `/opt/mediaserver/jellyseerr/db/` (SQLite)
- **Tautulli**: `/opt/mediaserver/tautulli/tautulli.db` (SQLite)

These are typically not directly edited; use the Web UI instead.

### Health Checks

Most services include Docker health checks that verify connectivity every 30 seconds. These are defined in `docker-compose.yml` and check service endpoints:
- Jellyfin: `http://localhost:8096/health`
- Plex: `http://127.0.0.1:32400/identity`
- Radarr/Sonarr: API endpoints with API key
- SABnzbd: `http://localhost:8080/api?mode=version`

Unhealthy containers can be identified with `docker compose ps`.

## Key Ports & Endpoints

### Direct Access (Current)
| Service | Port | Container | Use |
|---------|------|-----------|-----|
| **Homepage** | **3001** | **3000** | **Dashboard (all services in one place)** |
| Jellyfin | 8096 | 8096 | Media streaming (default) |
| Plex | host network | 32400 | Media streaming (legacy) |
| Overseerr | 5155 | 5055 | Request UI (Plex) |
| Jellyseerr | 5055 | 5055 | Request UI (Jellyfin) |
| SABnzbd | 8080 | 8080 | Downloader UI |
| Prowlarr | 9696 | 9696 | Indexer UI |
| Sonarr | 8989 | 8989 | TV series manager UI |
| Radarr | 7878 | 7878 | Movie manager UI |
| Bazarr | 6767 | 6767 | Subtitle manager UI |
| Tautulli | 8181 | 8181 | Plex analytics UI |
| Pi-hole | 8088 | 80 | DNS admin UI |

### With Caddy Reverse Proxy (Planned)
| Service | HTTPS Domain | Use |
|---------|--------------|-----|
| **Homepage** | **homepage.w0lverine.uk** | **Dashboard (public access, no auth)** |
| Jellyfin | jellyfin.w0lverine.uk | Media streaming via HTTPS |
| Plex | plex.w0lverine.uk | Media streaming via HTTPS |
| Overseerr | overseerr.w0lverine.uk | Request UI (Plex) via HTTPS |
| Jellyseerr | jellyseerr.w0lverine.uk | Request UI (Jellyfin) via HTTPS |
| Sonarr | sonarr.w0lverine.uk | TV manager (basic auth + LAN) |
| Radarr | radarr.w0lverine.uk | Movie manager (basic auth + LAN) |
| Prowlarr | prowlarr.w0lverine.uk | Indexer (basic auth + LAN) |
| SABnzbd | sabnzbd.w0lverine.uk | Downloader (basic auth + LAN) |
| Bazarr | bazarr.w0lverine.uk | Subtitles (basic auth + LAN) |
| Tautulli | tautulli.w0lverine.uk | Analytics (basic auth + LAN) |
| Caddy | 80, 443 | Reverse proxy & HTTPS termination |

Plex uses host networking to avoid port conflicts; all others use bridge networking on `media_net`.

## Homepage Dashboard

**Homepage** is a unified dashboard that provides one-stop access to all media server services with real-time monitoring and statistics.

### Quick Access
- **URL**: http://10.0.0.74:3001
- **Image**: `ghcr.io/gethomepage/homepage:v0.9.13`
- **Container Name**: homepage
- **Port Mapping**: `3001:3000` (host:container)

### Configuration Files

All configuration is YAML-based and located at `/opt/mediaserver/homepage/config/`:
- **settings.yaml** - Dashboard theme, layout, and title settings
- **services.yaml** - Service definitions with widgets and API integrations
- **widgets.yaml** - System resource monitors and search functionality
- **docker.yaml** - Docker socket integration for container monitoring

### Dashboard Layout

The dashboard is organized into 4 main groups:

**Media Group** (with live widgets):
- Jellyfin: Primary media server with library stats and active streams
- Plex: Legacy media server with Tautulli playback analytics

**Management Group** (with queue/calendar widgets):
- Sonarr: TV series with calendar and queue monitoring
- Radarr: Movies with calendar and queue monitoring
- Prowlarr: Indexer status
- Bazarr: Subtitle manager status

**Downloads Group**:
- SABnzbd: Usenet downloader with speed and queue widget
- Overseerr: Plex request manager
- Jellyseerr: Jellyfin request manager

**System Group**:
- Watchtower: Auto-update service status
- Pi-hole: DNS filtering status

### Widgets & Features

**System Monitoring:**
- CPU usage (real-time bar chart)
- Memory usage (real-time bar chart)
- Disk space usage
- Date and time display

**Service Integration Widgets:**
- Jellyfin: Shows active streams, library statistics
- Tautulli: Shows active Plex streams with user info and transcode status
- Sonarr: Upcoming episodes calendar, queue status
- Radarr: Upcoming releases calendar, queue status
- SABnzbd: Current download speed, queue depth, time remaining
- Docker: Container status (running/stopped) and resource usage

**Search Bar:**
- Google search integration (configurable provider)

### API Key Requirements

The following API keys from `.env` are used by Homepage widgets:
- `HOMEPAGE_VAR_SONARR_API_KEY` - Sonarr queue and calendar
- `HOMEPAGE_VAR_RADARR_API_KEY` - Radarr queue and calendar
- `HOMEPAGE_VAR_SAB_API_KEY` - SABnzbd download stats
- `HOMEPAGE_VAR_TAUTULLI_API_KEY` - Plex playback monitoring
- `JELLYFIN_TOKEN` - Jellyfin library and stream stats

### Host Validation

**Important:** Homepage performs port-aware host validation. The `HOMEPAGE_ALLOWED_HOSTS` environment variable must include the port number:
```yaml
- HOMEPAGE_ALLOWED_HOSTS=10.0.0.74:3001
```

This is required because the browser sends the full `Host: 10.0.0.74:3001` header, and Homepage validates both hostname AND port. If you add additional access methods (reverse proxy, Tailscale, etc.), update this variable:
```yaml
- HOMEPAGE_ALLOWED_HOSTS=10.0.0.74:3001,localhost:3001,192.168.1.x:3001
```

### Service Connectivity

Homepage can reach all services via the `media_net` Docker network:
- Internal service names (e.g., `http://sonarr:8989`) are used in widget configurations
- Host IP (`10.0.0.74`) is used in service link `href` fields for browser navigation
- Tautulli is used as an intermediary for Plex since Plex uses host networking

### Caddy Integration (Planned)

When Caddy reverse proxy is deployed, update Homepage configuration:
1. Add subdomain to Caddyfile: `homepage.w0lverine.uk`
2. Update `HOMEPAGE_ALLOWED_HOSTS` to: `homepage.w0lverine.uk`
3. Update service `href` values to use HTTPS URLs (e.g., `https://jellyfin.w0lverine.uk`)
4. Keep widget `url` fields as internal container names (no change needed)
5. Homepage itself needs no auth (or add auth in Caddyfile if desired)

### Health Check

```bash
# Check Homepage health
docker compose exec homepage wget -q -O - http://localhost:3000/ > /dev/null && echo "Homepage is healthy"

# View logs
docker compose logs homepage --tail=20

# Restart if needed
docker compose restart homepage
```

### Updating Homepage

To update Homepage to a newer version:
```bash
# Update to a specific version (recommended to test in staging first)
# Edit docker-compose.yml and change the image tag, then:
docker compose up -d --no-deps --build homepage
```

Note: Homepage is pinned to `v0.9.13` (stable) to avoid breaking changes in newer versions. Monitor releases at https://github.com/gethomepage/homepage/releases before upgrading.

## Networking

- **Docker Network**: `media_net` (external network, must exist before `docker compose up`)
- **Service Discovery**: Services reference each other by container name (e.g., `http://sonarr:8989`)
- **Host Access**: LAN IP (`HOST_LAN`) used for communication with host-based services
- **Extra Hosts**: JellyPlex-Watched includes DNS entries for Plex/Jellyfin external URLs to override internal discovery

### Network Setup

```bash
# Create the shared network (one-time setup)
docker network create media_net
```

### Reverse Proxy & HTTPS (Planned: Caddy Integration)

Caddy will be deployed as a reverse proxy to provide HTTPS termination and a cleaner access pattern:

**Architecture:**
- Caddy listens on ports 80/443 and proxies to internal services
- Automatic HTTPS certificates via Cloudflare DNS-01
- Wildcard domain support: `*.w0lverine.uk`
- Admin tools protected with basic auth + LAN IP restrictions
- Public streaming services (Plex, Jellyfin) accessible via subdomains with no additional auth

**Directory Structure:**
```
/opt/mediaserver/caddy/
├── config/Caddyfile          # Reverse proxy configuration
├── data/                      # Certificate storage
└── logs/                      # Caddy access/error logs
```

**Key Configuration Details:**
- Internal services remain on HTTP (Caddy handles HTTPS termination)
- Services communicate using container names (e.g., http://sonarr:8989)
- Plex special case: Uses `host.docker.internal:32400` due to host networking
- JellyPlex-Watched updated to use HTTPS domain URLs

**For Implementation Details:** See `caddy_plan.md` for complete integration plan including phased deployment steps, testing checklist, and rollback procedures.

## Security & Access Control

- **Fail2ban**: Protects against brute-force attacks (reads Plex logs)
- **Pi-hole**: DNS filtering (blocks malware/ads at DNS level)
- **Caddy** (Planned): Reverse proxy with HTTPS termination via Cloudflare DNS-01 for automatic certificate management
  - Public services (Plex, Jellyfin, Overseerr, Jellyseerr) accessible via clean HTTPS subdomains
  - Admin tools (Sonarr, Radarr, Prowlarr, SABnzbd, Bazarr, Tautulli) protected with basic auth + LAN IP restrictions
  - See `caddy_plan.md` for detailed implementation plan
- **API Keys**: Required for programmatic access to Radarr, Sonarr, Prowlarr, SABnzbd, Jellyfin, etc.
- **File Permissions**: `PUID:PGID` and `UMASK` ensure consistent access across containers

## Updating & Maintenance

### Auto-Updates

Watchtower runs nightly at 4 AM UTC to:
1. Check for new image versions
2. Roll-restart services with updates (minimal downtime)
3. Send Discord notifications with update summary

Services marked with `com.centurylinklabs.watchtower.enable=true` are auto-updated.

### Manual Updates

```bash
# Pull latest image without auto-restart (safer for testing)
docker pull lscr.io/linuxserver/sonarr:latest

# Apply the new image and restart
docker compose up -d --no-deps sonarr
```

### Backups

**Borgmatic** (full config backup):
- Runs daily at 4 AM UTC
- Backs up entire `/opt/mediaserver/` directory
- Stores in `/mnt/backup/mediaserver/`
- Uses encrypted repository (passphrase in `.env`)

**Rclone** (cloud sync):
- Backs up `/mnt/backup/mediaserver/` to cloud storage
- Configured in `/opt/mediaserver/backup/rclone/rclone.conf`
- Runs on cron schedule defined in `/opt/mediaserver/backup/rclone/crontab.txt`

## Troubleshooting Tips

**Service won't start:**
```bash
docker compose logs <service_name> | tail -50
# Check for permission errors, missing volumes, or configuration issues
```

**Database corruption:**
- SQLite databases can get locked; restart the service to clear locks
- Backup exists at `<service>.db.fresh` timestamp files (manual restore needed)

**Networking issues between containers:**
```bash
# Verify network connectivity
docker exec <service1> ping <service2>
docker exec <service1> curl http://<service2>:<port>/
```

**Permissions denied on media files:**
- Verify `PUID`/`PGID` in `.env` match the file owner on host
- Check `UMASK` setting (002 is typical)

**API timeouts/slow responses:**
- Check if service is healthy: `docker compose ps`
- Review service logs for warnings or errors
- Restart the service if unhealthy

## Development Notes

- **No native source code**: This is a Docker composition repo, not a source project. All services are pre-built images from Docker Hub/GitHub Container Registry.
- **Config-driven**: Changes are made via environment variables, volume mounts, and configuration files—not code modifications.
- **Declarative**: The entire system state is described in `docker-compose.yml` and `.env`.
- **IaC Philosophy**: Treat the compose file as infrastructure-as-code; version control both `docker-compose.yml` and configuration files.
