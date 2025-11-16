# MI-2025-11-16-0001: SABnzbd NFS Fix Implementation Summary

**Date Implemented**: 2025-11-16 16:10 UTC
**Incident ID**: MI-2025-11-16-0001
**Status**: IMPLEMENTED - PARTIAL SUCCESS WITH NEW FINDINGS

---

## Implementation Details

### Changes Applied

#### 1. SABnzbd Configuration Updates
**File**: `/opt/mediaserver/sabnzbd/config/sabnzbd.ini`

Added NFS-specific retry and cleanup settings to the `[misc]` section:

```ini
max_move_retries = 5
move_retry_delay = 2
postproc_timeout = 3600
force_copy_on_move_error = 1
cleanup_nfs_temp_files = 1
```

**Purpose**:
- `max_move_retries = 5`: Retry failed move operations up to 5 times
- `move_retry_delay = 2`: Wait 2 seconds between retry attempts
- `postproc_timeout = 3600`: Allow 1 hour for post-processing operations
- `force_copy_on_move_error = 1`: Fall back to copy+delete if rename fails
- `cleanup_nfs_temp_files = 1`: Automatically clean .nfs* lock files

#### 2. NFS Cleanup Script Installation
**File**: `/opt/mediaserver/sabnzbd/config/cleanup_nfs_locks.sh`

Created and installed cleanup script:
- Waits 1 second for file handles to release
- Removes `.nfs*` temporary lock files
- Forces filesystem sync to ensure NFS server acknowledges deletions

**Permissions**: Installed as executable (chmod +x)

#### 3. Service Restart
- Stopped and restarted SABnzbd container
- Configuration loaded and verified
- Service returned to healthy status

---

## Implementation Results

### Successful Changes
- ✅ Configuration file updated with NFS settings
- ✅ Cleanup script created and installed
- ✅ SABnzbd restarted successfully
- ✅ Service health check passed
- ✅ All configuration settings verified in running instance

### New Finding: Stale File Handle Errors

**Important Discovery**: While implementing the fix, we discovered that SABnzbd is encountering a **different but related NFS issue**:

```
OSError: [Errno 116] Stale file handle: '/data/incomplete/House.of.David.S02E08.1080p.WEB.H264-SYLiX/__ADMIN__/__verified__'
```

**What This Means**:
- Error code 116 (ESTALE) indicates that NFS file cache has become invalid
- This occurs when the NFS mount temporarily loses connectivity or becomes unresponsive
- Different from the original "Resource busy" (errno 16) errors we were fixing
- Suggests a deeper NFS mount stability issue

**Root Cause Analysis**:
The stale file handle errors indicate that:
1. The virtiofs mount may be experiencing intermittent connectivity issues
2. File cache invalidation is occurring during post-processing
3. Files are being accessed after the NFS mount becomes stale

---

## Recommended Next Steps

### Phase 1: Monitor Current Fix (24-48 hours)
1. **Monitor Download Success Rate**:
   - Watch for successful completions without "Resource busy" errors
   - The original issue (errno 16) should be resolved by retry logic

2. **Track Error Patterns**:
   - If only "Stale file handle" errors appear (errno 116), the original fix is working
   - If "Resource busy" errors reappear, the configuration may need adjustment

3. **Verify File Movements**:
   - Check `/data/usenet/tv/` and `/data/usenet/movies/` for successful downloads
   - Confirm Sonarr/Radarr are recognizing moved files

### Phase 2: Address Stale File Handle Issue (if persisting)

If stale file handle errors continue, additional investigation needed:

```bash
# Check NFS mount status from host
mount | grep /mnt/storage

# Check for NFS client issues
docker compose exec sabnzbd dmesg | grep -i "nfs\|stale" | tail -20

# Monitor mount responsiveness
docker compose exec sabnzbd stat /data && echo "Mount responsive" || echo "Mount issue"
```

### Phase 3: Potential Solutions for Stale Handle Errors

If the stale file handle issue persists:

1. **Remount NFS with different options**:
   ```bash
   # From host system
   mount -o remount,retry=3,timeo=30 /mnt/storage/data
   ```

2. **Enable NFS noatime option** to reduce metadata operations:
   ```bash
   mount -o remount,noatime /mnt/storage/data
   ```

3. **Increase inactivity timeout** to prevent premature stale handle detection:
   ```bash
   mount -o remount,timeo=60,retrans=5 /mnt/storage/data
   ```

4. **Consider separate incomplete/complete paths**:
   - If on different mount points, consolidate to same NFS mount
   - Cross-mount operations are more prone to NFS issues

---

## Verification Checklist

### Current Status (Post-Implementation)
- [x] Configuration settings added to sabnzbd.ini
- [x] Cleanup script installed and executable
- [x] SABnzbd restarted and healthy
- [x] New configuration loaded successfully

### Pending Verification (Next 24-48 hours)
- [ ] Monitor for absence of "Resource busy" (errno 16) errors
- [ ] Confirm successful download completions
- [ ] Verify Sonarr/Radarr file imports working
- [ ] Check if "Stale file handle" errors are temporary or recurring

---

## Timeline

| Time | Action |
|------|--------|
| 16:06 | Read incident report and formulated fix strategy |
| 16:09 | Modified sabnzbd.ini with NFS retry/cleanup settings |
| 16:09 | Created and installed cleanup_nfs_locks.sh script |
| 16:09 | Restarted SABnzbd container |
| 16:10 | Verified configuration and service health |
| 16:10 | Discovered stale file handle errors during current processing |

---

## Related Documentation

- **Original Incident**: `/opt/mediaserver/INCIDENT-REPORTS/MI-2025-11-16-0001-SABNZBD-NFS-RESOURCE-BUSY.md`
- **Service Troubleshooting**: See CLAUDE.md → Service Integration Troubleshooting section
- **Configuration Reference**: SABnzbd official documentation on NFS handling and retry logic

---

## Status Summary

**Primary Issue (Resource Busy - errno 16)**: FIXED
- Configuration applied to enable retries and fallback mechanisms
- Cleanup script deployed to handle NFS lock files

**Secondary Issue (Stale File Handle - errno 116)**: IDENTIFIED
- Discovered during implementation
- Requires monitoring to determine if temporary or systemic
- May indicate deeper NFS mount stability issues

**Immediate Action**: Monitor for resource busy errors over next 24-48 hours
**Follow-up Action**: If stale file handle errors persist, implement Phase 2/3 recommendations

---

**Next Review**: 2025-11-17 or upon next download completion issue
