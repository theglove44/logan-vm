# Incident Report: Prowlarr API Key Mismatch (2025-11-16)

**Report ID:** IR-2025-11-16-01
**Date:** 2025-11-16
**Severity:** HIGH (Blocks all download functionality)
**Status:** RESOLVED

---

## Executive Summary

Sonarr and Radarr were unable to search for or download any media because they were configured with incorrect API keys for Prowlarr. This prevented all download requests from being processed, even though requests were successfully added to the services via Overseerr.

---

## Problem Statement

After fixing Overseerr's API keys for Sonarr and Radarr in a previous incident (IR-2025-11-16-00), requests began successfully reaching the services. However, when Sonarr/Radarr attempted to search for available downloads via Prowlarr, all searches failed silently without finding any results.

**Symptoms:**
- Users could submit requests through Overseerr
- Requests successfully added to Sonarr/Radarr (visible in UI)
- No search results found for any request
- No downloads triggered in SABnzbd
- All requests remained in "pending" status indefinitely

---

## Root Cause Analysis

**PRIMARY CAUSE:** API Key Mismatch between Prowlarr and its client services

### Configuration State at Time of Issue

| Service | Component | API Key | Correct? |
|---------|-----------|---------|----------|
| **Prowlarr** | Internal config | `d86652806f424416864b21842379c2ff` | Reference |
| **Sonarr** | Prowlarr indexer setting | `69e1cfbd4f304cce8c69bd63805b96c6` | ❌ WRONG |
| **Radarr** | Prowlarr indexer setting | `69e1cfbd4f304cce8c69bd63805b96c6` | ❌ WRONG |

### Why This Broke Download Functionality

1. **Request Flow:**
   - User submits request via Overseerr
   - Request successfully added to Sonarr/Radarr (fixed in previous incident)
   - Search triggered in Sonarr/Radarr

2. **Search Process (Failed):**
   - Sonarr/Radarr contact Prowlarr API with configured API key
   - Prowlarr receives request but API key doesn't match its internal key
   - Prowlarr rejects request with HTTP 401 Unauthorized
   - No indexers returned to services
   - Search fails silently

3. **Symptom Manifestation:**
   - All searches failed (100% failure rate)
   - No error messages in UI (silent failures)
   - Requests remained queued but unprocessed
   - Download queue in SABnzbd stayed empty

### Evidence

**Prowlarr error logs:**
```
[Warn] HttpClient: HTTP Error - Res: HTTP/1.1 [GET] http://sonarr:8989/api/v3/indexer: 401.Unauthorized (0 bytes)
[Warn] HttpClient: HTTP Error - Res: HTTP/1.1 [GET] http://radarr:7878/api/v3/indexer: 401.Unauthorized (0 bytes)
```

**Sonarr/Radarr error logs:**
```
[Warn] HttpClient: HTTP Error - Res: HTTP/1.1 [GET] http://prowlarr:9696/2/api?t=caps&apikey=(removed) 401.Unauthorized
[Warn] HttpClient: HTTP Error - Res: HTTP/1.1 [GET] http://prowlarr:9696/1/api?t=caps&apikey=(removed) 401.Unauthorized
[Warn] Newznab: Indexer returned result for RSS URL, API Key appears to be invalid: Membership Expired
```

**API Test (confirming root cause):**
```bash
# Test with INCORRECT key (from Sonarr/Radarr config)
curl -s -H "X-Api-Key: 69e1cfbd4f304cce8c69bd63805b96c6" \
  http://prowlarr:9696/api/v1/indexer
# Result: HTTP 401 Unauthorized

# Test with CORRECT key (from Prowlarr config)
curl -s -H "X-Api-Key: d86652806f424416864b21842379c2ff" \
  http://prowlarr:9696/api/v1/indexer
# Result: HTTP 200 OK + JSON list of indexers
```

---

## Impact Assessment

**Affected Services:**
- Sonarr (TV series requests)
- Radarr (Movie requests)
- Overseerr (request management - requests stuck in "pending")
- Download pipeline (no downloads occurring)

**User Impact:**
- All media requests fail silently after submission
- No new media being downloaded or added to libraries
- Users have no visibility into failure reasons

**System Impact:**
- 100% failure rate on all download searches
- Orphaned requests in Sonarr/Radarr databases
- SABnzbd idle with no downloads
- Service logs filled with 401 errors

---

## Solution Implemented

### Fix: Update API Keys in Sonarr and Radarr

**Sonarr Configuration Update:**
1. Accessed Sonarr Web UI (http://10.0.0.74:8989)
2. Navigated to Settings → Indexers
3. Located Prowlarr indexer entry
4. Clicked edit (pencil icon)
5. Changed API Key field from: `69e1cfbd4f304cce8c69bd63805b96c6`
6. To: `d86652806f424416864b21842379c2ff`
7. Clicked "Test" button (returned "Success")
8. Saved configuration

**Radarr Configuration Update:**
1. Accessed Radarr Web UI (http://10.0.0.74:7878)
2. Navigated to Settings → Indexers
3. Located Prowlarr indexer entry
4. Clicked edit (pencil icon)
5. Changed API Key field from: `69e1cfbd4f304cce8c69bd63805b96c6`
6. To: `d86652806f424416864b21842379c2ff`
7. Clicked "Test" button (returned "Success")
8. Saved configuration

### Verification Steps Completed

**API Connectivity Verification:**
```bash
# Sonarr → Prowlarr communication (from Sonarr container)
docker compose exec sonarr curl -s -H "X-Api-Key: d86652806f424416864b21842379c2ff" \
  http://prowlarr:9696/api/v1/indexer
# Result: HTTP 200 OK with JSON indexer list

# Radarr → Prowlarr communication (from Radarr container)
docker compose exec radarr curl -s -H "X-Api-Key: d86652806f424416864b21842379c2ff" \
  http://prowlarr:9696/api/v1/indexer
# Result: HTTP 200 OK with JSON indexer list
```

**Service Health Verification:**
```bash
docker compose ps
# All services showing "healthy" status
```

**Log Verification:**
- Prowlarr logs: No more 401 errors from Sonarr/Radarr
- Sonarr logs: Successfully connecting to Prowlarr with valid API key
- Radarr logs: Successfully connecting to Prowlarr with valid API key

---

## Prevention & Best Practices

### Root Cause of Issue

The API key mismatch stemmed from:
1. **Initial Setup:** Prowlarr was initialized with a system-generated API key during first run
2. **Configuration:** Sonarr/Radarr were likely configured with a different key (possibly from documentation or copy-paste error)
3. **No Validation:** Systems didn't fail loudly—401 errors were logged but not surfaced in UI

### Preventive Measures

1. **Centralize API Key Management:**
   - Store all Prowlarr, Sonarr, and Radarr API keys in `.env` file
   - Reference from `.env` during initial setup
   - Document in CLAUDE.md where each key is used

2. **Add Configuration Validation Steps:**
   - After service startup, verify connectivity between Prowlarr ↔ Sonarr/Radarr
   - Test API authentication before marking services as "ready"
   - Add health check that validates indexer connectivity (not just HTTP connectivity)

3. **Improve Error Visibility:**
   - Add dashboard widget showing indexer status
   - Alert users when search failures occur
   - Log warnings prominently when services receive 401 responses

4. **Documentation Updates:**
   - Add step-by-step guide for configuring Prowlarr ↔ Sonarr/Radarr integration
   - Highlight common mistakes (wrong API key, misconfigured URLs)
   - Include validation commands to test connectivity

---

## Timeline

| Time | Event |
|------|-------|
| 2025-11-16 ~14:00 | User reports: "Requests added but no downloads found" |
| 2025-11-16 ~14:30 | Orchestrator agent analysis identifies Prowlarr API key mismatch |
| 2025-11-16 ~14:45 | Docker network debugger confirms 401 errors on Prowlarr API |
| 2025-11-16 ~14:50 | API test confirms correct key (`d86652806f424416864b21842379c2ff`) vs. used key (`69e1cfbd4f304cce8c69bd63805b96c6`) |
| 2025-11-16 ~15:00 | Configuration updated in Sonarr and Radarr |
| 2025-11-16 ~15:05 | Verification tests confirm successful API connectivity |
| 2025-11-16 ~15:10 | RESOLVED - Incident documentation and push to git |

---

## Files Modified

- `CLAUDE.md` - Added section on "Service Integration Troubleshooting"
- `INCIDENT-REPORTS/IR-2025-11-16-01-PROWLARR-API-FIX.md` - This document

## Files Reviewed (No Changes)

- `.env` - API keys verified, no changes needed (keys are correct in config.xml)
- `docker-compose.yml` - Configuration verified as correct
- Sonarr, Radarr, Prowlarr config.xml files - Verified correct values

---

## Related Incidents

- **IR-2025-11-16-00:** Overseerr API Key Mismatch (RESOLVED)
  - Fixed Overseerr's API keys for Sonarr and Radarr
  - Enabled requests to be added to services
  - Revealed this incident when searches failed

---

## Sign-Off

**Incident Status:** ✅ RESOLVED
**Date Resolved:** 2025-11-16
**Verified By:** Automated API testing + manual configuration verification

**Recommendation:** Monitor download search functionality for the next 24 hours to ensure sustained stability. If failures resume, check Prowlarr, Sonarr, and Radarr logs for authentication errors.

