# LoggiFly Phase 1 - Testing & Tuning Guide

## Deployment Status: LIVE

**Start Date:** 2025-12-18 09:30 UTC
**Services Monitored:** Sonarr, Radarr, Prowlarr (3 services)
**Notification Channel:** Discord #media-logs
**Testing Duration:** 48 hours (until 2025-12-20 09:30 UTC)

---

## Current Architecture

```
Sonarr/Radarr/Prowlarr Logs
         ↓
    LoggiFly (pattern matching)
         ↓
  Apprise API (tag routing)
         ↓
Discord Webhooks
         ↓
   #media-logs channel
```

**Key Services:**
- **LoggiFly** (ghcr.io/clemcer/loggifly:latest): Real-time log pattern matching
- **docker-socket-proxy** (tecnativa/docker-socket-proxy): Secure Docker API access
- **Apprise** (lscr.io/linuxserver/apprise-api): Notification routing with tag support

---

## What to Monitor During Phase 1

### 1. Alert Volume (Target: 5-10 alerts/day)

**Track in Discord #media-logs:**
- Total alerts per day
- Alerts per service (Sonarr/Radarr/Prowlarr breakdown)
- Alert types (what patterns are firing)

**Recording:**
Document a brief summary each morning:
- Day 1 (2025-12-18): X total alerts (S: Y, R: Z, P: W)
- Day 2 (2025-12-19): X total alerts (S: Y, R: Z, P: W)

**Success Criteria:**
- ✅ 5-10 total alerts per day is healthy
- ⚠️ >20 alerts/day indicates false positives (needs tuning)
- ⚠️ 0 alerts for 12+ hours might indicate detection gap

### 2. Alert Quality (Verify Relevance)

**For each alert received:**
1. Check if it's a real error in the service logs
2. Determine if it's actionable or expected
3. Note the pattern that triggered it

**Pattern Assessment Checklist:**

| Pattern | Sample Error | False Positive? | Keep? |
|---------|--------------|-----------------|-------|
| Stale file handle | NFS mount issue | No - real error | ✅ |
| "Couldn't import episode" | Duplicate detected | Maybe - check if expected | ❓ |
| Exception/traceback | Real crash | No - keep | ✅ |

### 3. Service Health

**Daily Verification:**
```bash
# Check all 3 services are healthy
docker compose ps sonarr radarr prowlarr

# No more than 1-2 restarts per day (indicates stability)
docker compose logs --tail=1 sonarr | grep "Started"
```

**Expected Status:**
- All 3 services running and healthy
- No excessive container restarts
- Normal log flow (not stuck or silent)

### 4. LoggiFly System Health

**Check container status:**
```bash
docker compose ps loggifly docker-socket-proxy apprise
```

**Expected Results:**
- loggifly: healthy (or starting)
- docker-socket-proxy: healthy
- apprise: healthy

**Monitor resource usage:**
```bash
docker stats loggifly --no-stream
```

**Expected:** <100MB RAM, <5% CPU

---

## Configuration Fine-Tuning During Phase 1

### Excluding False Positives

If a pattern generates too many false positives, add an `exclude_regex` to filter them:

**Example: Sonarr "Couldn't import episode" is too noisy**

Edit `/opt/mediaserver/loggifly/config/config.yaml`:

```yaml
containers:
  sonarr:
    keywords:
      # ... existing patterns ...
      - regex: "Couldn't import episode"
        description: "Episode import failed"
        # NEW: Exclude known benign cases
        exclude_regex: "(already exists|duplicate|malformed)"
```

Save the file - LoggiFly auto-reloads (no restart needed).

### Adding Patterns

If you notice errors in the Discord channel that LoggiFly missed, add new patterns:

```yaml
containers:
  sonarr:
    keywords:
      # NEW: Catch API rate limiting
      - regex: "(?i)rate.*limit"
        description: "API rate limiting detected"
```

### Disabling Patterns

Comment out patterns that are generating too much noise:

```yaml
containers:
  sonarr:
    keywords:
      # - regex: "\\|Warn\\|.*(?:indexer|prowlarr)"
      #   description: "Indexer communication issues"  # Disabled - too noisy
```

---

## Common Issues & Troubleshooting

### Issue 1: No Alerts Appearing

**Symptom:** Discord #media-logs is silent for 12+ hours

**Root Causes:**
1. Services aren't logging errors (healthy state - good!)
2. LoggiFly didn't start properly
3. Apprise webhook is broken

**Diagnosis:**
```bash
# Check LoggiFly logs for errors
docker compose logs loggifly --tail=30 | grep -i "error\|exception"

# Check if LoggiFly is reading container logs
docker compose logs loggifly --tail=50 | grep "found in"

# Verify Apprise is receiving notifications
docker compose logs apprise --tail=20 | grep "POST /notify"
```

**Fix:**
- If LoggiFly shows errors, check config.yaml YAML syntax
- If no "found in" messages, verify excluded_containers list
- If Apprise logs are empty, notifications aren't being sent

### Issue 2: Too Many Alerts (>20/day)

**Symptom:** Discord #media-logs flooded with repetitive alerts

**Root Causes:**
1. Pattern too broad (catches expected warnings)
2. Deduplication not working
3. Rate limiting needs adjustment

**Diagnosis:**
```bash
# Check what pattern is firing most
docker compose logs loggifly --tail=100 | grep "following keywords" | tail -20
```

**Fix:**
1. Add `exclude_regex` to filter out benign variations
2. Increase deduplication window:
   ```yaml
   deduplication:
     enabled: true
     window_seconds: 1800  # Increase from 600 to 1800 (30 min)
   ```

### Issue 3: Service Appears in Logs but Alert Not Sent

**Symptom:** Error visible in Sonarr/Radarr/Prowlarr logs but no Discord alert

**Root Causes:**
1. Pattern doesn't match the actual error text
2. Error is in an excluded_container
3. Rate limiting suppressed the alert

**Diagnosis:**
```bash
# Check if service is in excluded list
grep -A 20 "excluded_containers:" /opt/mediaserver/loggifly/config/config.yaml

# Check actual error text in logs
docker compose logs sonarr --tail=50 | grep -i "error\|fail"

# Compare with pattern in config
grep -B2 -A2 "Stale file handle" /opt/mediaserver/loggifly/config/config.yaml
```

**Fix:**
1. Verify pattern regex matches actual error text (use regex tester)
2. Ensure service isn't in excluded_containers
3. Check rate_limit settings

---

## Phase 1 -> Phase 2 Decision Criteria

**Proceed to Phase 2 if:**
- ✅ Consistent 5-15 alerts/day (pattern is stable)
- ✅ Real errors detected within 1-5 minutes of occurrence
- ✅ Zero false positives after 48 hours (or excluded appropriately)
- ✅ LoggiFly/Apprise running stably (no crashes/restarts)
- ✅ Configuration tuned to acceptable noise level

**Hold/Troubleshoot if:**
- ⚠️ >20 alerts/day (too noisy for Phase 2)
- ⚠️ <2 alerts/day (might be missing real errors)
- ⚠️ Container crashes/high resource usage
- ⚠️ No alerts despite visible errors in logs

---

## Phase 1 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Alert volume | 5-15/day | Monitoring |
| False positive rate | <20% | Monitoring |
| Detection time | <5 min | Monitoring |
| System stability | No crashes | Monitoring |
| Config reload time | <10 sec | Monitoring |

---

## Phase 2 Preview

**When Phase 1 is successful, Phase 2 adds:**
- SABnzbd (download failures, repair issues)
- Overseerr (request processing failures)
- Bazarr (subtitle provider errors)

**Update config.yaml to enable Phase 2:**
```yaml
excluded_containers:
  # Remove these to enable monitoring:
  # - "sabnzbd"
  # - "overseerr"
  # - "bazarr"

  # Keep excluded:
  - "tautulli"
  - "homepage"
  - "caddy"
  - "plex"
  # ... rest of excluded services
```

---

## Quick Reference

### Configuration File
- **Location:** `/opt/mediaserver/loggifly/config/config.yaml`
- **Auto-reload:** Yes (no restart needed)
- **Validation:** Visible in LoggiFly logs

### Log Monitoring
```bash
# Real-time LoggiFly logs
docker compose logs -f loggifly

# Check for specific keyword patterns
docker compose logs loggifly | grep "following keywords"

# Check Apprise notifications sent
docker compose logs apprise | grep "POST /notify"
```

### Discord Channel
- **Channel:** #media-logs
- **Webhook URL:** Stored in apprise.yml (tag: logs)
- **Message Format:** [container] Log Alert with error context

### Testing Endpoints
- **Apprise Web UI:** http://localhost:8338/
- **Docker Socket Proxy:** tcp://docker-socket-proxy:2375
- **LoggiFly Config:** /config/config.yaml (hot-reloadable)

---

## Status Updates

**2025-12-18 09:45 UTC - Phase 1 Live**
- ✅ LoggiFly container: healthy
- ✅ docker-socket-proxy: healthy
- ✅ Apprise: healthy
- ✅ Sonarr: actively being monitored (Stale file handle errors detected)
- ✅ Radarr: actively being monitored
- ✅ Prowlarr: actively being monitored
- ✅ Notification pipeline: working (Apprise receiving POST requests)

**Next Review:** 2025-12-19 09:30 UTC (24-hour checkpoint)
**Final Assessment:** 2025-12-20 09:30 UTC (48-hour decision point)

---

Generated: 2025-12-18 09:45 UTC
Plan: LoggiFly Integration - Phase 1 Deployment
Phase Status: ACTIVE
