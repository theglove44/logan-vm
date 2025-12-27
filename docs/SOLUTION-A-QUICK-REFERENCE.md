# Solution A: Quick Reference Card
**Plex Remote Access - Static Port Forwarding Fix**
**Incident:** MI-2025-11-22-0001

---

## Current Status (As of 2025-11-22 08:16 UTC)

**Docker-level Changes: COMPLETE**
```
✓ ADVERTISE_IP updated to include external IP (82.71.1.223:32400)
✓ Plex container restarted successfully
✓ Health check passing (Up 41 seconds - healthy)
✓ Local endpoint responding (/identity returns XML)
✓ Configuration backup created
```

**Router-level Changes: PENDING**
```
⚠ Static port forwarding NOT YET CONFIGURED
⚠ Must configure on router before external access works
⚠ Expected port forward: TCP/UDP 32400 → 10.0.0.79:32400
```

---

## Critical Information

| Item | Value |
|------|-------|
| **External IP** | 82.71.1.223 |
| **External Port** | 32400 |
| **Internal IP** | 10.0.0.79 |
| **Internal Port** | 32400 |
| **Protocol** | TCP + UDP (BOTH required) |
| **Router Address** | http://10.0.0.1 |
| **Plex Web UI** | http://10.0.0.79:32400 |
| **Plex Container** | plex (Up 41 seconds - healthy) |

---

## What You Need to Do RIGHT NOW

### Step 1: Router Configuration (MOST IMPORTANT)

1. **Access Router:**
   - Open browser: http://10.0.0.1
   - Log in with router admin credentials

2. **Configure Port Forwarding:**
   - Find: Port Forwarding or NAT Forwarding settings
   - Create Rule:
     - External Port: **32400**
     - Internal IP: **10.0.0.79**
     - Internal Port: **32400**
     - Protocol: **TCP and UDP** (both required!)
   - Save and Apply

3. **Verify:**
   - Rule appears in active port forwarding list
   - Rule is ENABLED (not disabled)

**Time Required:** 5-10 minutes

### Step 2: Test External Connectivity

1. **Visit:** https://www.canyouseeme.org
2. **Enter Port:** 32400
3. **Click:** Check
4. **Wait:** 10-15 seconds for result

**Expected Result:**
- **GREEN:** "Success! I can see your service on 82.71.1.223 on port 32400"
- **RED:** "I could not see your service" (troubleshoot - see below)

**Time Required:** 2 minutes

### Step 3: Test Remote Access

**If CanYouSeeMe returned GREEN:**

1. Enable mobile hotspot (different network than home)
2. Connect test device to hotspot
3. Open Plex app or https://app.plex.tv
4. Log in
5. Select any content and press Play
6. Check connection type (should say "Direct" not "Relay")

**If connection shows "Direct" and plays smoothly:** SUCCESS!

**Time Required:** 5 minutes

---

## Quick Troubleshooting

### Problem: CanYouSeeMe Returns RED

**Possible Cause:** Port forwarding not configured or incorrect

**Quick Fix:**
1. Verify router port forward exists: Log into http://10.0.0.1
2. Check:
   - External port: 32400 ✓
   - Internal IP: 10.0.0.79 ✓
   - Internal port: 32400 ✓
   - Protocol: TCP and UDP ✓
   - Status: ENABLED ✓
3. If any wrong: Fix and save
4. Wait 1 minute
5. Re-test on CanYouSeeMe.org

**If Still RED:**
- ISP may be blocking port 32400
- Contact ISP: "Is port 32400 blocked? Can I use port 80/443?"
- Consider Solution B (Caddy Reverse Proxy) as alternative

### Problem: Plex Shows "Relay" Instead of "Direct"

**Possible Causes:**
1. CanYouSeeMe test is RED (port not reachable)
2. Plex hasn't registered external IP yet (needs 2-5 minutes)
3. Plex app is caching old connection info

**Quick Fix:**
1. Verify Test 3 (CanYouSeeMe) returns GREEN
2. If RED: See "CanYouSeeMe Returns RED" above
3. If GREEN: Wait 5 minutes, then restart Plex app:
   ```bash
   # On server:
   docker compose restart plex
   # Wait 40 seconds
   # On remote device: Close and reopen Plex app
   ```

### Problem: Local Access Works But Remote Doesn't

**This is normal if TEST 3 is RED (port not reachable)**

**Local access will always work because:**
- Local devices are on home network
- Direct LAN connection to 10.0.0.79:32400
- No port forwarding needed for LAN

**Remote access requires:**
- External port reachable from internet (Test 3 must be GREEN)
- Router port forwarding configured correctly
- ISP not blocking the port

**Solution:**
- If Test 3 is RED: Fix port forwarding or contact ISP
- If Test 3 is GREEN but remote still fails: Restart Plex and app (clear cache)

---

## Verification Commands

```bash
# Check Plex status
docker compose ps plex
# Expected: Up X minutes (healthy)

# Check ADVERTISE_IP configuration
grep ADVERTISE_IP /opt/mediaserver/docker-compose.yml
# Expected: ...http://82.71.1.223:32400,http://10.0.0.79:32400,...

# Test local connectivity
docker exec plex curl -s http://127.0.0.1:32400/identity | head
# Expected: XML response with server details

# View recent Plex logs
docker compose logs plex --tail=50 | grep -i "remote\|publish\|advertise"

# Restart Plex if needed
docker compose restart plex
```

---

## Success Indicators (What Should Happen)

**Step 1 (Router):**
- Port forwarding rule appears in router's active rules list
- No error messages

**Step 2 (Reachability):**
- CanYouSeeMe.org returns GREEN with message about port 32400
- Shows your IP: 82.71.1.223

**Step 3 (Remote Access):**
- Plex app connects and shows library
- Connection indicator shows "Direct" (not "Relay")
- Content plays smoothly
- Multiple remote users can connect simultaneously
- Playback stable for 10+ minutes

**Plex Web UI:**
- Settings → Remote Access shows: "Published - Ready"
- (Not "Not Published" or "Mapped - Not Published")

---

## If Everything Works: Next Steps

1. **Keep Testing**
   - Monitor for 24+ hours
   - Ensure stability

2. **Document**
   - Note date and time of successful implementation
   - Save test results

3. **Plan Solution B (Optional)**
   - Current solution (A) works but exposes port 32400 publicly
   - Solution B (Caddy Reverse Proxy) is more secure
   - Plan for implementation next 1-2 weeks
   - Would provide HTTPS and subdomain access (plex.w0lverine.uk)

4. **Close Incident**
   - Mark MI-2025-11-22-0001 as RESOLVED
   - Archive testing documentation

---

## If External Test Fails: Escalation Path

**If CanYouSeeMe returns RED and router config is correct:**

1. **Contact ISP Support**
   - "Is my connection behind Carrier-Grade NAT (CGNAT)?"
   - "Are you filtering traffic on port 32400?"
   - "Can I use ports 80 or 443?"

2. **Alternative Solution: Caddy Reverse Proxy**
   - Deploy Caddy container on ports 80/443 (usually not blocked)
   - Reverse proxy to Plex (more secure, HTTPS)
   - See: `/opt/mediaserver/CLAUDE.md` (search "caddy_plan")
   - Implementation timeline: 1-2 weeks

3. **Workaround in Meantime**
   - Users must accept Plex Relay (lower quality, higher latency)
   - Or access Plex from VPN back to home network
   - Temporary until Solution B deployed

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| SOLUTION-A-IMPLEMENTATION-GUIDE.md | Detailed step-by-step instructions |
| SOLUTION-A-POST-IMPLEMENTATION-TESTING.md | Comprehensive testing checklist |
| MI-2025-11-22-0001-PLEX-REMOTE-ACCESS.md | Full incident report with analysis |
| MI-2025-11-22-0001-DIAGNOSTIC-CHECKLIST.md | Diagnostic decision tree |

---

## Key Contacts & Resources

- **Router Admin Interface:** http://10.0.0.1
- **Plex Web UI:** http://10.0.0.79:32400
- **Port Checker:** https://www.canyouseeme.org
- **Plex Support:** https://support.plex.tv/articles/216446558-how-to-get-remote-access-working/
- **ISP Support:** [Look on your bill or contact your provider]

---

## Configuration Backup

**Original Configuration Saved:**
```
/opt/mediaserver/docker-compose.yml.backup.20251122
```

**To Rollback (if needed):**
```bash
cp /opt/mediaserver/docker-compose.yml.backup.20251122 /opt/mediaserver/docker-compose.yml
docker compose restart plex
```

---

## Timeline Estimate

| Phase | Task | Time | Cumulative |
|-------|------|------|-----------|
| 1 | Router port forwarding setup | 5-10 min | 5-10 min |
| 2 | External connectivity test (CanYouSeeMe) | 2 min | 7-12 min |
| 3 | Remote app testing (if Test 2 passes) | 5-10 min | 12-22 min |
| **Total** | **Complete implementation + testing** | **~20 min** | **20 min** |

**Note:** This assumes port forwarding configuration works correctly. If ISP blocks the port, diagnosis may take longer (1-2 hours including ISP support contact).

---

## What Was Changed

**Configuration Change:**
```diff
- ADVERTISE_IP=http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
+ ADVERTISE_IP=http://82.71.1.223:32400,http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400
```

**Root Cause Addressed:**
- OLD: Plex couldn't advertise external IP to remote users
- NEW: Plex now advertises external IP (82.71.1.223:32400) for direct remote access

**Still Required:**
- Router must forward traffic from external port 32400 to internal 10.0.0.79:32400
- ISP must not block port 32400

---

## Status Summary

**Configuration Status:** ✓ COMPLETE
**Docker Changes:** ✓ APPLIED & TESTED
**Container Health:** ✓ HEALTHY (Up 41+ seconds)
**Local Connectivity:** ✓ VERIFIED
**Router Configuration:** ⚠ PENDING (YOU MUST DO THIS)
**External Testing:** ⚠ AWAITING ROUTER CONFIG
**Issue Resolution:** ⚠ IN PROGRESS

---

**Implementation Date:** 2025-11-22 08:16 UTC
**Incident Reference:** MI-2025-11-22-0001
**Solution Type:** A - Static Port Forwarding
**Risk Level:** LOW (configuration only, reversible)
**Expected Success Rate:** 70% (depends on ISP allowing port 32400)

---

**NEXT ACTION:** Configure static port forwarding on router at http://10.0.0.1
**CRITICAL TEST:** https://www.canyouseeme.org (must return GREEN)
**SUCCESS INDICATOR:** Plex remote app shows "Direct" connection (not "Relay")
