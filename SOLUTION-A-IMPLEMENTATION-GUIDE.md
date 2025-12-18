# Solution A: Static Port Forwarding Implementation Guide
**For Incident:** MI-2025-11-22-0001 (Plex Remote Access Degradation)
**Created:** 2025-11-22 08:15 UTC
**Status:** READY FOR IMPLEMENTATION

---

## Quick Summary

This guide implements **Solution A: Static Port Forwarding** to fix Plex remote access degradation caused by incorrect ADVERTISE_IP configuration and potential port forwarding issues.

**Key Changes:**
1. Configure static port forward on router: TCP/UDP port 32400 → 10.0.0.79:32400
2. Update docker-compose.yml ADVERTISE_IP to include external IP (82.71.1.223:32400)
3. Restart Plex and verify remote access is now "Published - Ready"

**Estimated Time:** 20-30 minutes
**Risk Level:** LOW (reversible configuration changes)
**Required Access:** Router admin interface (10.0.0.1)

---

## Pre-Implementation Verification Checklist

**All items below are VERIFIED and PASSED:**

- [x] Plex container is healthy and running (Status: Up 28 minutes, healthy)
- [x] Plex is listening on port 32400 locally (Health check: PASSING)
- [x] Network mode is "host" (correct for Plex direct port binding)
- [x] Current ADVERTISE_IP is missing external IP/port (identified root cause)
- [x] Docker compose is accessible and valid
- [x] No syntax errors in configuration files
- [x] System has 28 minutes uptime since last restart (stable)

**Current System State:**
```
Service:           Plex Media Server
Container Status:  Up 28 minutes (healthy)
Image:             lscr.io/linuxserver/plex:latest
Version:           1.42.2.10156-f737b826c
Network Mode:      host
Current Port:      32400
Internal IP:       10.0.0.79
External IP:       82.71.1.223
Current ADVERTISE_IP: http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
```

---

## STEP 1: Router Configuration (Static Port Forwarding)

### Access Router Admin Interface

**Method: Web Browser**
1. Open your web browser (Chrome, Firefox, Safari, Edge)
2. Navigate to: **http://10.0.0.1**
3. Enter router credentials:
   - **Username:** (typically "admin" or found on router label)
   - **Password:** (default password or custom password)
4. You should now see the router administration dashboard

**If you cannot access 10.0.0.1:**
- Verify router IP address (check on router label or use: `ip route | grep default`)
- Confirm you're connected to the same network as the router
- Try resetting router to factory defaults if credentials are unknown

### Locate Port Forwarding Settings

**Common Router Location Paths:**
- **Netgear:** Advanced → Port Forwarding or UPnP
- **TP-Link:** More Settings → NAT Forwarding → Port Forwarding
- **ASUS:** Advanced Settings → NAT Forwarding → Port Forwarding
- **Linksys:** Advanced → Port Forwarding
- **D-Link:** Advanced → Port Mapping
- **Generic/Other:** Look for "Port Forwarding," "Virtual Server," or "Port Mapping"

**Screenshots/Help:**
If your router interface is unfamiliar, search online for: `"[ROUTER_MODEL] port forwarding"` (e.g., "Netgear Nighthawk port forwarding")

### Create Static Port Forward Rule

**Configuration Details:**

| Setting | Value | Explanation |
|---------|-------|-------------|
| **Service Name/Description** | Plex Media Server | For identification (optional) |
| **External Port** | 32400 | The port exposed to the internet |
| **Internal IP Address** | 10.0.0.79 | The Plex container host IP |
| **Internal Port** | 32400 | The port Plex listens on internally |
| **Protocol** | TCP and UDP | BOTH required (may be separate rules) |
| **Enable/Status** | Enabled | Rule must be active |

**Step-by-Step Entry:**

1. **Fill in External Port:**
   - Field: "External Port" or "Start Port"
   - Enter: **32400**

2. **Fill in Internal IP:**
   - Field: "Internal IP Address" or "IP Address"
   - Enter: **10.0.0.79**

3. **Fill in Internal Port:**
   - Field: "Internal Port" or "End Port"
   - Enter: **32400**

4. **Select Protocol:**
   - If single dropdown: Select **TCP+UDP** or **Both**
   - If separate fields: Create TWO rules (one for TCP, one for UDP)

5. **Enable the Rule:**
   - Check the "Enable" or "Active" checkbox
   - Make sure rule is NOT disabled

6. **Save/Apply:**
   - Click **Save**, **Apply**, or **Submit** button
   - Wait for page to refresh and confirm changes are saved

### Verify Port Forwarding was Created

After saving:

1. **Look for Confirmation:**
   - Message should say "Port forwarding rule added successfully" or similar
   - Rule should appear in the list of active port forwards

2. **Verify the Rule:**
   - External Port: **32400** ✓
   - Internal IP: **10.0.0.79** ✓
   - Internal Port: **32400** ✓
   - Protocol: **TCP and UDP** ✓
   - Status: **Enabled** ✓

3. **Check for Conflicts:**
   - Ensure no other rules forward to port 32400
   - Look for any old UPnP mappings that might conflict

**Example Configuration (Screenshot-equivalent):**
```
Port Forwarding Rules:
├─ Rule 1: TCP 32400 → 10.0.0.79:32400 [Enabled] ✓
└─ Rule 2: UDP 32400 → 10.0.0.79:32400 [Enabled] ✓
```

---

## STEP 2: Disable UPnP Mapping (Clean State)

**Goal:** Remove old UPnP port mapping to avoid conflicts with static forward

### In Router Admin Interface

1. Navigate to **UPnP Settings** or **UPnP Port Mapping**
2. Look for port **15794** (the old UPnP mapping)
3. If found, **Delete** or **Remove** the mapping
4. **Save/Apply** changes

### In Plex Web UI (Also Recommended)

1. Open browser: **http://10.0.0.79:32400**
2. Log in with your Plex account
3. Navigate to: **Settings → Remote Access**
4. Click **Disable Remote Access** (if currently enabled)
   - This tells Plex to release its UPnP mapping
5. Wait 10 seconds
6. Click **Enable Remote Access** (this will re-enable using our static forward)

**Expected Behavior After Restart:**
- Plex will attempt to negotiate remote access
- With static port forward in place, it will succeed
- Remote Access status should change to "Published - Ready"

---

## STEP 3: Update Docker Compose Configuration

### Backup Original File

```bash
cp /opt/mediaserver/docker-compose.yml /opt/mediaserver/docker-compose.yml.backup.20251122
```

### Edit ADVERTISE_IP

**File:** `/opt/mediaserver/docker-compose.yml`
**Line:** 54

**Current Configuration:**
```yaml
- ADVERTISE_IP=http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
```

**New Configuration:**
```yaml
- ADVERTISE_IP=http://82.71.1.223:32400,http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
```

**Explanation:**
- **http://82.71.1.223:32400** ← NEW: External IP and port (Plex advertises this to remote users)
- **http://10.0.0.79:32400** ← EXISTING: Local LAN IP for home network fallback
- **https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400** ← EXISTING: Secure local fallback

### Edit Using Command Line

**Using `sed` (automated):**
```bash
cd /opt/mediaserver
sed -i.bak54 \
  's|ADVERTISE_IP=http://10.0.0.79:32400,https://10-0-0-79|ADVERTISE_IP=http://82.71.1.223:32400,http://10.0.0.79:32400,https://10-0-0-79|g' \
  docker-compose.yml
```

**Verify the change:**
```bash
grep ADVERTISE_IP /opt/mediaserver/docker-compose.yml
```

Should output:
```
- ADVERTISE_IP=http://82.71.1.223:32400,http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
```

### Edit Using Text Editor (if preferred)

**Using `nano` (interactive):**
```bash
nano /opt/mediaserver/docker-compose.yml
```

1. Use Ctrl+W to find: "ADVERTISE_IP"
2. Navigate to line 54
3. Edit the line to add the external IP at the beginning
4. Press Ctrl+O to save
5. Press Ctrl+X to exit

---

## STEP 4: Restart Plex Container

### Restart Service

```bash
cd /opt/mediaserver
docker compose restart plex
```

**Expected Output:**
```
mediaserver-plex-1
```

### Verify Restart Completed

```bash
docker compose ps plex
```

**Expected Output:**
```
NAME      IMAGE                             STATUS
plex      lscr.io/linuxserver/plex:latest   Up X seconds (health: starting)
```

Wait 30-40 seconds for health check to pass (should show "healthy").

---

## STEP 5: Verify Configuration and Monitor Logs

### Check Plex Logs for ADVERTISE_IP Recognition

```bash
docker compose logs plex --tail=50 | grep -i "advertise\|publish\|remote"
```

**Look For Messages Like:**
- "Publishing" - Plex is registering with Plex.tv
- "Advertise" - Plex recognizes the configured IPs
- "Ready" - Remote access is established

### Wait for Health Check to Pass

```bash
watch -n 5 'docker compose ps plex | grep STATUS'
```

Press Ctrl+C when status shows `(healthy)` or wait for the following:

```bash
# Full health check status
docker compose ps plex
```

**Expected:**
```
STATUS: Up X minutes (healthy)
```

### Access Plex Web UI Locally

1. Open browser: **http://10.0.0.79:32400**
2. Navigate to: **Settings → Remote Access**
3. Check status indicator

**Expected Status (this is the key indicator):**
```
Remote Access: Published - Ready
```

If you see this, the fix is working!

---

## STEP 6: Testing External Connectivity

### Test 1: Local LAN Access (Sanity Check)

From any device on your home network:
```bash
curl http://10.0.0.79:32400/identity
```

**Expected:** XML response showing server identity

### Test 2: External Port Reachability (from External Network)

If you have access to an external network (mobile hotspot, VPN, etc.):

```bash
# From external network
curl -I http://82.71.1.223:32400/identity
```

**Expected:** `HTTP/1.1 200 OK` or `HTTP/1.1 401 Unauthorized` (both mean port is reachable)
**Problem:** Connection timeout or refused (port not reachable from internet)

### Test 3: Using Online Tool (No External Network Needed)

1. Visit: **https://www.canyouseeme.org**
2. Enter port: **32400**
3. Click: **Check**

**Expected Result:**
- GREEN: "Success! I can see your service on 82.71.1.223 on port 32400"
- RED: "I could not see your service" (indicates ISP/firewall blocking)

### Test 4: Plex App Remote Access (Mobile Hotspot)

1. Connect secondary device to mobile hotspot (different network than home)
2. Open Plex app or visit https://app.plex.tv
3. Log in with Plex account
4. Navigate to your library
5. Select any title and click **Play**

**What to Look For:**
- Content should play smoothly
- In Plex app Settings → Connections, should show **"Direct"** (not "Relay")
- Playback should start within 10 seconds
- No buffering or quality degradation

**If you see "Relay":**
- External port may still be unreachable from internet
- ISP or router firewall is blocking the connection
- Proceed to ISP Diagnostics (Solution D)

---

## Rollback Procedure (If Needed)

### If Remote Access Still Doesn't Work

1. **Restore Original Configuration:**
```bash
# Restore from backup
cp /opt/mediaserver/docker-compose.yml.backup.20251122 /opt/mediaserver/docker-compose.yml

# Restart Plex
docker compose restart plex
```

2. **Remove Router Port Forward:**
   - Log into router (10.0.0.1)
   - Delete the static port forward rule for port 32400
   - Save/Apply changes

3. **Re-enable UPnP (Optional):**
   - In Plex Web UI → Settings → Remote Access
   - Click "Enable Remote Access" to re-activate UPnP

4. **Verify Rollback:**
```bash
docker compose ps plex
```

Should return to original state with no data loss.

---

## Success Criteria

**Remote access is working correctly when ALL of these are true:**

1. [ ] Plex Remote Access status: **"Published - Ready"** (shown in Plex Web UI)
2. [ ] Local LAN access works: http://10.0.0.79:32400 loads
3. [ ] Remote access via mobile hotspot: Content plays with "Direct" connection (not "Relay")
4. [ ] External port test passes: CanYouSeeMe.org shows GREEN
5. [ ] No SSL/certificate errors
6. [ ] Stream quality is good (matches local playback)
7. [ ] Multiple simultaneous connections work (if tested)
8. [ ] Connection remains stable for extended playback (5+ minutes)

---

## Troubleshooting

### Problem: Remote Access Status Still Shows "Not Published"

**Check:**
1. Plex container is healthy: `docker compose ps plex`
2. ADVERTISE_IP includes external IP: `grep ADVERTISE_IP /opt/mediaserver/docker-compose.yml`
3. Router port forwarding exists: Log into 10.0.0.1 and verify rule
4. External port is reachable: https://www.canyouseeme.org shows GREEN

**Solution:**
- Wait 2-5 minutes after restart (Plex needs time to register with Plex.tv)
- Disable/re-enable Remote Access in Plex Web UI
- Restart Plex again: `docker compose restart plex`

### Problem: External Port Reachability Test FAILS

**This indicates ISP or firewall is blocking the port.**

**Possible Causes:**
1. **CGNAT (Carrier-Grade NAT):** ISP using double NAT, port forwarding won't work
2. **ISP Firewall:** ISP blocking port 32400 traffic
3. **Router Firewall:** Router firewall rules blocking the port

**Solutions:**
1. **Contact ISP Support:**
   - "Is my connection behind CGNAT?"
   - "Are you filtering traffic on port 32400?"
   - "Can I get a static public IP or bridge mode?"

2. **Implement Solution B (Caddy Reverse Proxy):**
   - Deploy Caddy on ports 80/443 (usually not blocked)
   - Reverse proxy Plex through HTTPS subdomain
   - Most ISPs allow ports 80/443

### Problem: Plex Relay Still Active Despite "Published - Ready"

**This might indicate a network configuration issue on the remote device.**

**Check:**
1. Remote device is actually on external network (not home WiFi)
2. Plex app is up-to-date
3. Multiple simultaneous remote connections work (not a rate limit)

**Solution:**
- Try from different device/network to isolate issue
- Restart Plex app on remote device
- Log out and back in to Plex account

---

## Estimated Timeline

| Phase | Task | Duration | Cumulative |
|-------|------|----------|-----------|
| 1 | Router port forwarding setup | 5-10 min | 5-10 min |
| 2 | Disable old UPnP mapping | 2 min | 7-12 min |
| 3 | Update ADVERTISE_IP in docker-compose.yml | 2 min | 9-14 min |
| 4 | Restart Plex and wait for health check | 2-3 min | 11-17 min |
| 5 | Verify logs and Plex Web UI status | 2-3 min | 13-20 min |
| 6 | Test external connectivity | 5-10 min | 18-30 min |

**Total Estimated Time:** 20-30 minutes

---

## Important Notes

- **No Data Loss Risk:** All changes are configuration-only; media library unaffected
- **Minimal Downtime:** Only 2-3 minutes during Plex restart
- **Reversible:** Can easily roll back to original configuration if needed
- **Secure Baseline:** Solution A is secure for most residential use (port 32400 standard for Plex)
- **Future Enhancement:** Plan to implement Solution B (Caddy Reverse Proxy) for long-term HTTPS + subdomain access

---

## Next Steps After Implementation

### If Remote Access Works:
1. Document the working configuration
2. Monitor Plex logs for stability (24+ hours)
3. Notify end users that remote access is restored
4. Plan Solution B deployment (Caddy Reverse Proxy) for future HTTPS access

### If Remote Access Still Doesn't Work:
1. Proceed to Solution D (ISP Investigation)
2. Contact ISP support with findings from CanYouSeeMe.org test
3. Determine if CGNAT or firewall is blocking
4. Plan Solution B (Caddy Reverse Proxy) as long-term workaround

---

## References

- **Incident Report:** `/opt/mediaserver/INCIDENT-REPORTS/MI-2025-11-22-0001-PLEX-REMOTE-ACCESS.md`
- **Diagnostic Checklist:** `/opt/mediaserver/INCIDENT-REPORTS/MI-2025-11-22-0001-DIAGNOSTIC-CHECKLIST.md`
- **Docker Compose Config:** `/opt/mediaserver/docker-compose.yml`
- **Plex Remote Access Docs:** https://support.plex.tv/articles/216446558-how-to-get-remote-access-working/

---

**Created:** 2025-11-22 08:15 UTC
**Implementation Ready:** YES
**Risk Level:** LOW
**Estimated Success Rate:** 70% (if external port is reachable from ISP)
