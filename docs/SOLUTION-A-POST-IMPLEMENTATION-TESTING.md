# Solution A: Post-Implementation Testing & Validation
**For Incident:** MI-2025-11-22-0001 (Plex Remote Access Degradation)
**Created:** 2025-11-22 08:16 UTC
**Implementation Status:** COMPLETE - CONFIGURATION CHANGED

---

## Implementation Summary

**Changes Applied:**

1. **ADVERTISE_IP Updated** ✓
   - OLD: `http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400`
   - NEW: `http://82.71.1.223:32400,http://10.0.0.79:32400,https://10-0-0-79.9cc05cc3c9c14a059b2a0222e067e786.plex.direct:32400`

2. **Plex Container Restarted** ✓
   - Status: **Up 41 seconds (healthy)**
   - Health Check: **PASSING**
   - Local Endpoint: **RESPONDING** (verified via /identity)

3. **Configuration File Backed Up** ✓
   - Backup Location: `/opt/mediaserver/docker-compose.yml.backup.20251122`

---

## IMPORTANT: Router Configuration Still Required

**CRITICAL STEP NOT YET COMPLETED:**

You must still configure static port forwarding on your router for the external access to work. The ADVERTISE_IP change alone will allow Plex to advertise the external IP, but the router must actually forward traffic.

### Quick Router Setup Checklist

**ACTION REQUIRED - Complete these steps before testing remote access:**

- [ ] Access router admin interface: http://10.0.0.1
- [ ] Log in with router credentials
- [ ] Navigate to Port Forwarding settings
- [ ] Create static port forward:
  - External Port: **32400**
  - Internal IP: **10.0.0.79**
  - Internal Port: **32400**
  - Protocol: **TCP and UDP** (create separate rules if needed)
- [ ] Enable/Save the port forwarding rule
- [ ] Verify rule appears in active port forwarding list
- [ ] (Optional) Delete old UPnP mapping for port 15794 if present

**See:** `/opt/mediaserver/SOLUTION-A-IMPLEMENTATION-GUIDE.md` for detailed router instructions.

---

## Test 1: Local LAN Connectivity (Baseline)

**Objective:** Verify Plex is accessible and functioning on local network

**Prerequisites:**
- Device connected to home WiFi
- Network access to 10.0.0.79

**Test Command (from any device on LAN):**
```bash
curl http://10.0.0.79:32400/identity
```

**Expected Result:**
```
<?xml version="1.0" encoding="UTF-8"?>
<MediaContainer size="0" apiVersion="1.1.1" claimed="1" machineIdentifier="2757a8d90a22f2fd9077c77b9107536981bf1a28" version="1.42.2.10156-f737b826c">
</MediaContainer>
```

**Pass Criteria:**
- Response contains `<MediaContainer>` element
- Status code is 200 OK
- Response time is fast (<500ms)

**Result:** [ ] PASS [ ] FAIL

---

## Test 2: Plex Web UI Access (Local)

**Objective:** Verify Plex web interface is accessible and shows correct configuration

**Prerequisites:**
- Device on home network
- Web browser available

**Steps:**
1. Open browser: http://10.0.0.79:32400
2. Log in with Plex account
3. Navigate to: **Settings** (gear icon)
4. Click: **Remote Access** (left sidebar)
5. Check the status indicator

**Expected Results:**
```
Remote Access Status: Published - Ready
```

**Additional Information to Verify:**
- Server name displays correctly
- Library shows expected content
- Settings page loads without errors
- No SSL/certificate warnings

**Result:** [ ] PASS [ ] FAIL

**Screenshot (for documentation):**
- If status shows "Published - Ready" ✓ = Configuration recognized by Plex
- If status shows "Not Published" ✗ = May need more time or additional troubleshooting

---

## Test 3: External Port Reachability (CRITICAL)

**Objective:** Determine if external IP:port is reachable from the internet

**This test is CRITICAL for determining success. Complete BEFORE testing remote apps.**

### Option A: Online Port Checker (No Equipment Needed)

**Website:** https://www.canyouseeme.org

**Steps:**
1. Visit: https://www.canyouseeme.org
2. In "Port to check" field, enter: **32400**
3. Click: **Check** button
4. Wait 10-15 seconds for result

**Possible Results:**

**GREEN SUCCESS:**
```
Success! I can see your service on 82.71.1.223 on port 32400
Your ISP/Firewall is allowing the connection
```
- [ ] If you see GREEN: Proceed to Test 4 (Remote App Testing)
- Router port forwarding is working
- External IP is reachable
- ISP is not blocking the port

**RED FAILURE:**
```
I could not see your service on <IP> on port 32400
Reasons:
  - Your ISP may be blocking the port
  - Your router may not be configured to forward the port
  - You may not have an internet connection
```
- [ ] If you see RED: **STOP - Troubleshooting Required**
- Router port forwarding may not be configured correctly
- ISP may be blocking port 32400
- Proceed to "Troubleshooting" section below

**Result:** [ ] GREEN (PASS) [ ] RED (FAIL)

### Option B: Command Line Test (from External Network)

**Prerequisites:**
- Access to external network (mobile hotspot, VPN, external server)
- Command-line tools (`nc` or `curl`)

**Test Command:**
```bash
nc -zv 82.71.1.223 32400
# Should output: succeeded (or Connection successful)
```

**Expected Output:**
```
Connection to 82.71.1.223 32400 port [tcp/*] succeeded
```

**Result:** [ ] PASS (succeeded) [ ] FAIL (timeout/refused)

---

## Test 4: Remote App Access (Mobile Hotspot)

**Objective:** Verify remote devices can access Plex and connect directly (not relay)

**Prerequisites:**
- [ ] Test 3 (External Port Reachability) PASSED with GREEN result
- [ ] Device with mobile hotspot or external network access
- [ ] Plex app installed (or access to https://app.plex.tv in browser)
- [ ] Plex account login

**Setup:**
1. Disable home WiFi on test device (or use separate device)
2. Connect to mobile hotspot (or external network)
3. Verify no access to home network (ping 10.0.0.79 should timeout)

**Test Procedure:**

### A. Via Plex Mobile App

**Steps:**
1. Open Plex app on remote device
2. Tap the user icon (bottom right)
3. Tap "Sign In" (if not signed in)
4. Log in with your Plex account
5. Navigate to "Your Libraries" or "Home"
6. Select a movie or TV show
7. Press "Play"

**During Playback:**
1. Tap the 3-dot menu or info button
2. Look for "Connection" or "Settings" section
3. Check connection type indicator

**Success Indicators:**
- [ ] Content plays within 10 seconds of pressing Play
- [ ] Connection shows as **"Direct"** (NOT "Relay")
- [ ] Quality is good (not low/grainy)
- [ ] No buffering or frequent pauses
- [ ] No "Connection Lost" errors
- [ ] Stream continues smoothly for 5+ minutes

**Result:** [ ] PASS (Direct, smooth playback) [ ] FAIL (Relay or errors)

### B. Via Plex Web (https://app.plex.tv)

**Steps:**
1. On remote device (on mobile hotspot), open browser
2. Navigate to: https://app.plex.tv
3. Log in with Plex account
4. Select your server from the list
5. Navigate to a library
6. Select any content
7. Press "Play" button

**Success Indicators:**
- [ ] Web interface loads
- [ ] Server selection works
- [ ] Content plays without SSL errors
- [ ] Playback is smooth
- [ ] No relay indicators

**Result:** [ ] PASS [ ] FAIL

---

## Test 5: Connection Quality Assessment

**Objective:** Verify connection is direct and not relay

**Prerequisites:**
- [ ] Test 4 (Remote App Access) completed
- [ ] Content currently playing on remote device

**Check Connection Type:**

### Via Plex App

**Location:** Settings → Connections (or Info → Connection Details)

**Look For:**
```
Connection Type: Direct (excellent)
Connection Speed: Good/Normal (not "Slow")
Protocol: HTTP or HTTPS (both acceptable)
Address: 82.71.1.223:32400 (external IP should appear)
```

**Pass Criteria:**
- Connection Type: **Direct** ✓
- NOT "Relay" ✗
- NOT "Buffering" or "Slow" ✗

**Result:** [ ] PASS (Direct) [ ] FAIL (Relay/Slow)

### Via Plex Web

**Location:** Settings/Info icon during playback

**Look For:**
- Connection status indicator
- Direct vs Relay indicator
- Current bitrate/quality

**Pass Criteria:**
- Direct connection indicator present
- No relay warning message

**Result:** [ ] PASS [ ] FAIL

---

## Test 6: Multiple Simultaneous Connections

**Objective:** Verify multiple remote users can connect simultaneously

**Prerequisites:**
- [ ] Test 4 (Remote App Access) PASSED
- [ ] 2-3 devices with external network access available
- [ ] All devices logged into Plex

**Setup:**
1. Device 1: Mobile hotspot
2. Device 2: Mobile hotspot (different phone) or separate device
3. Device 3: (Optional) Another external network

**Procedure:**
1. Have each device log into Plex app
2. Each device selects different content
3. All devices press "Play" simultaneously (within 5 seconds)
4. Monitor each for 30-60 seconds

**Success Indicators:**
- [ ] All 3 content items play simultaneously
- [ ] No "Too many remote connections" errors
- [ ] All show "Direct" connection (not relay)
- [ ] No connection drops
- [ ] Quality remains consistent across devices

**Result:** [ ] PASS (all simultaneous) [ ] FAIL (dropped/queued)

---

## Test 7: Extended Duration Playback

**Objective:** Verify connection stability over extended playback

**Prerequisites:**
- [ ] Test 4 (Remote App Access) PASSED
- [ ] Remote device on external network
- [ ] Content queued and ready to play

**Procedure:**
1. Start playing content on remote device
2. Let it play for 10-15 minutes
3. Monitor for:
   - Connection drops or disconnects
   - Quality changes
   - Relay fallback
   - Buffering or pauses
4. Pause video at 5-min mark, wait 1 minute, then resume
5. Verify smooth resume without re-buffering

**Success Indicators:**
- [ ] No connection interruptions during 10+ minute playback
- [ ] Connection remains "Direct" (doesn't fall back to Relay)
- [ ] Quality consistent throughout
- [ ] No buffering after initial 10-second load
- [ ] Pause/resume works smoothly
- [ ] No "Connection Lost" messages

**Result:** [ ] PASS (stable 10+ min) [ ] FAIL (disconnects/relay)

---

## Test 8: Different Client Types

**Objective:** Verify fix works across all Plex client types

**Prerequisites:**
- Remote/external network access
- Multiple client types available (app, web, Cast device, etc.)

**Clients to Test:**
- [ ] Plex Web (https://app.plex.tv)
- [ ] Plex iOS App (if available)
- [ ] Plex Android App (if available)
- [ ] Plex Cast/Smart TV (if available)
- [ ] Desktop app (if available)

**For Each Client:**
1. Log in with Plex account
2. Select same content
3. Press Play
4. Check connection type (Direct vs Relay)
5. Let play for 30 seconds
6. Monitor quality

**Success Criteria (ALL clients):**
- [ ] All connect successfully
- [ ] All show "Direct" connection
- [ ] All stream smoothly
- [ ] No client-specific failures

**Result:** [ ] PASS (all work) [ ] FAIL (some don't work)

**Devices Tested:**
- Client 1: ________________ [ ] PASS [ ] FAIL
- Client 2: ________________ [ ] PASS [ ] FAIL
- Client 3: ________________ [ ] PASS [ ] FAIL

---

## Test 9: Local Fallback (Sanity Check)

**Objective:** Verify local LAN access still works (no regression)

**Prerequisites:**
- Device on home WiFi
- Plex app or web access

**Procedure:**
1. Return to home WiFi
2. Open Plex app or browser to http://10.0.0.79:32400
3. Log in
4. Select any content
5. Press Play
6. Check connection type

**Success Indicators:**
- [ ] Local access works perfectly
- [ ] Connection shows as **"Local"** (not Remote)
- [ ] Playback starts immediately
- [ ] Quality is excellent (local network speed)
- [ ] No dependency on remote configuration
- [ ] Faster load times than remote

**Result:** [ ] PASS (local works) [ ] FAIL (local broken)

---

## FINAL VERIFICATION CHECKLIST

**Required for "Issue Resolved" Status:**

- [ ] **Test 1 PASSED:** Local LAN connectivity verified
- [ ] **Test 2 PASSED:** Plex Web UI accessible, settings visible
- [ ] **Test 3 PASSED:** External port reachable (GREEN from CanYouSeeMe.org)
- [ ] **Test 4 PASSED:** Remote app access working, content plays
- [ ] **Test 5 PASSED:** Connection shows as "Direct" (NOT Relay)
- [ ] **Test 6 PASSED:** Multiple simultaneous connections work
- [ ] **Test 7 PASSED:** Extended playback stable (10+ minutes)
- [ ] **Test 8 PASSED:** Multiple client types work
- [ ] **Test 9 PASSED:** Local fallback still works

**Acceptance Criteria (ALL must be true):**

1. [ ] Remote users can connect directly without relay
2. [ ] Plex Remote Access status shows "Published - Ready"
3. [ ] Connection is "Direct" (not "Relay") for all remote users
4. [ ] Streaming quality and speed equivalent to local access
5. [ ] Multiple simultaneous remote users supported
6. [ ] Connection stable for extended periods (10+ minutes)
7. [ ] No SSL/certificate errors
8. [ ] Local LAN access unaffected

---

## Troubleshooting: Test 3 FAILED (RED Result)

**If CanYouSeeMe.org shows RED (port not reachable), proceed below:**

### Diagnosis Steps

**1. Verify Router Port Forward Configuration**

Log into router (http://10.0.0.1):
- [ ] Port forwarding rule exists for port 32400
- [ ] External port: 32400 (or 15794 if using different port)
- [ ] Internal IP: 10.0.0.79 (correct)
- [ ] Internal port: 32400 (correct)
- [ ] Protocol: TCP and UDP (both required)
- [ ] Rule is **ENABLED** (not disabled)

**If any of above are incorrect:**
1. Edit the port forwarding rule
2. Correct the settings
3. Save/Apply changes
4. Wait 30 seconds
5. Re-run Test 3 (CanYouSeeMe.org)

**If rule is missing entirely:**
1. Create the port forward as per SOLUTION-A-IMPLEMENTATION-GUIDE.md
2. Wait for rule to activate (1-2 minutes)
3. Re-run Test 3

### 2. Verify Plex is Listening

**From inside container:**
```bash
docker exec plex netstat -tlnp | grep 32400
```

**Expected Output:**
```
tcp        0      0 0.0.0.0:32400          0.0.0.0:*               LISTEN
```

**If not present:** Plex may not have restarted properly
- Restart: `docker compose restart plex`
- Wait 40 seconds
- Re-run netstat check

### 3. Check Firewall Rules on Host

```bash
sudo ufw status | grep 32400
sudo iptables -L -n | grep 32400
```

**If rules are blocking:**
```bash
sudo ufw allow 32400
sudo ufw reload
```

### 4. ISP/Network Issue (Most Likely if Above Passes)

**If router config is correct AND Plex is listening AND port checker still fails:**

This indicates **ISP-level blocking:**
- ISP firewall blocking port 32400
- Carrier-Grade NAT (CGNAT) preventing port forwarding from reaching public internet
- ISP filtering non-standard ports

**Next Steps:**
1. Contact ISP support:
   - "Is my connection behind Carrier-Grade NAT (CGNAT)?"
   - "Are you filtering traffic on port 32400?"
   - "Can I use port 80 or 443 instead?"

2. Alternative: Implement Solution B (Caddy Reverse Proxy)
   - Forward ports 80/443 instead (usually allowed by ISP)
   - Caddy proxies to Plex on HTTPS subdomain
   - More secure and professional approach

---

## Troubleshooting: Test 4 FAILED or Shows RELAY

**If remote app shows "Relay" instead of "Direct":**

### Quick Checks

1. **Verify Test 3 Passed (Critical)**
   - If Test 3 is RED (port not reachable), that's the cause
   - Remote cannot connect directly if port isn't reachable from internet
   - Fix port reachability first (see Troubleshooting above)

2. **Verify ADVERTISE_IP Configuration**
   ```bash
   grep ADVERTISE_IP /opt/mediaserver/docker-compose.yml
   ```
   - Should include: `http://82.71.1.223:32400` (external IP)
   - If missing: Re-apply the ADVERTISE_IP change and restart Plex

3. **Wait for Plex Registration**
   - After restart, Plex needs 2-5 minutes to register with Plex.tv
   - Plex.tv needs to acknowledge the external IP
   - Try remote access again after 5 minutes

4. **Clear Plex Cache**
   - Plex app may be caching old connection info
   - Close Plex app completely
   - Wait 30 seconds
   - Reopen app and try again

5. **Verify Server Claim Status**
   ```bash
   docker exec plex curl -s http://127.0.0.1:32400/identity | grep claimed
   ```
   - Should show: `claimed="1"`
   - If `claimed="0"`: Server not claimed, may need to reclaim

### Advanced Troubleshooting

**Check Plex Preferences for Remote Access Settings:**
```bash
find /opt/mediaserver/plex -name "Preferences.xml" -exec grep -i "publish" {} \;
```

**Look for:**
```xml
PublishServerOnPlexOnlineKey="1"
```

**If set to 0:** Enable in Plex Web UI:
- Settings → Remote Access → Enable

---

## Success - What's Next?

**If ALL tests PASSED:**

1. **Document Results**
   - Attach this test report to incident MI-2025-11-22-0001
   - Note: Solution A successful - external port forwarding working
   - Record: ADVERTISE_IP updated successfully

2. **Monitor for 24+ Hours**
   - Watch Plex logs for any errors: `docker compose logs -f plex`
   - Verify connection remains stable
   - Have end users confirm continued access

3. **Plan Solution B (Long-term)**
   - Current solution (A) works but exposes port 32400 directly
   - Plan to implement Caddy Reverse Proxy (Solution B)
   - Provides HTTPS, subdomain access, better security
   - Timeline: Next 1-2 weeks

4. **Close Incident**
   - Mark incident as RESOLVED once 24+ hour stability confirmed
   - Archive this test report
   - Update CLAUDE.md with final configuration

---

## Important Notes

- **Do NOT delete docker-compose.yml.backup.20251122** - Keep for rollback if needed
- **Test 3 (External Port Reachability) is the KEY test** - All others depend on it
- **If Test 3 fails and you've verified router config, the issue is ISP-level** - Not your configuration
- **Multiple simultaneous tests are encouraged** - Don't test just one device
- **Document all results** - Helps with future troubleshooting

---

## Reference

- **Incident Report:** `/opt/mediaserver/INCIDENT-REPORTS/MI-2025-11-22-0001-PLEX-REMOTE-ACCESS.md`
- **Implementation Guide:** `/opt/mediaserver/SOLUTION-A-IMPLEMENTATION-GUIDE.md`
- **Docker Compose:** `/opt/mediaserver/docker-compose.yml`
- **Port Checker:** https://www.canyouseeme.org
- **Plex Support:** https://support.plex.tv/articles/216446558-how-to-get-remote-access-working/

---

**Test Date:** _________________
**Tester:** _________________
**Results Summary:** [ ] ALL PASS [ ] PARTIAL PASS [ ] FAILED
**Status:** [ ] Ready for production [ ] Needs troubleshooting [ ] Rollback recommended

---

**Last Updated:** 2025-11-22 08:16 UTC
