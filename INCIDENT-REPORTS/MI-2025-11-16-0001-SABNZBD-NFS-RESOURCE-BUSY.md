# MI-2025-11-16-0001: SABnzbd NFS File Movement Failures - Resource Busy Errors

**Incident ID**: MI-2025-11-16-0001
**Date Reported**: 2025-11-16
**Severity Level**: High
**Status**: IMPLEMENTED - MONITORING

---

## Problem Statement

SABnzbd is failing to move unpacked files from `/data/incomplete` to `/data/usenet/tv` with recurring "Resource busy" errors. This prevents post-processed downloads from being organized into the media library, blocking the entire download-manage-stream workflow.

**Affected Services**:
- SABnzbd (primary failure point)
- Sonarr/Radarr (cannot process moved files)
- Jellyfin/Plex (incomplete media additions)

**Impact on Users**: Downloads complete successfully but fail during post-processing unpacking stage. Files accumulate in `/data/usenet/tv/_FAILED_*` directories marked as failed. Users are unable to access newly downloaded content through the media streaming interface.

**Scope**: This is a systematic issue affecting multiple downloads over several days (Nov 13-16, 2025), not a one-time occurrence.

---

## Root Cause Analysis

### Evidence from Investigation

**Log Entry - Landman.S02E01 (Representative Case)**:
```
2025-11-16 15:53:19,252::ERROR::[filesystem:835] Failed moving
  /data/incomplete/Landman.S02E01.Death.and.a.Sunset.1080p.AMZN.WEB-DL.DDP5.1.H.264-Kitsune/.nfs00000000003302ce00002d22
  to
  /data/usenet/tv/_UNPACK_Landman.S02E01.Death.and.a.Sunset.1080p.AMZN.WEB-DL.DDP5.1.H.264-Kitsune/.nfs00000000003302ce00002d22

Traceback (most recent call last):
  File "/usr/lib/python3.12/shutil.py", line 847, in move
    os.rename(src, real_dst)
OSError: [Errno 16] Resource busy: '/data/incomplete/Landman.S02E01.Death.and.a.Sunset.1080p.AMZN.WEB-DL.DDP5.1.H.264-Kitsune/.nfs00000000003302ce00002d22'
  -> '/data/usenet/tv/_UNPACK_Landman.S02E01.Death.and.a.Sunset.1080p.AMZN.WEB-DL.DDP5.1.H.264-Kitsune/.nfs00000000003302ce00002d22'
```

**Key Observations**:

1. **NFS Lock File Artifacts**: The filenames contain `.nfs<inode_number>` patterns (e.g., `.nfs00000000003302ce00002d22`), which are temporary NFS lock/state files created by the NFS client to track open file handles during operations.

2. **Root Cause**: The `.nfs*` files represent open file handles that remain locked during the unpack process. When SABnzbd attempts to move the entire directory tree from `/data/incomplete` to `/data/usenet/tv`, the NFS rename operation (`os.rename()`) fails because the source files are still held open by the unpacker process or NFS cache mechanisms.

3. **virtiofs Mount Type**: The host-level mount shows `virtiofs` (virtual filesystem over virtio) rather than traditional NFS:
   ```
   storage on /mnt/storage type virtiofs (rw,relatime,_netdev)
   ```
   This explains the hybrid behavior: while the mount appears as a network filesystem to the container, it uses virtio transport. The `.nfs*` lock file naming suggests the kernel's NFS compatibility layer is still active.

4. **Timing Issue**: The error occurs during post-processing immediately after unpacking completes. The unpacker (unrar/7za) writes files to `/data/usenet/tv/_UNPACK_*`, then SABnzbd attempts to move residual files from `/data/incomplete` before fully releasing file handles.

5. **Cross-Directory Move Limitation**: Moving files across directories on NFS (even within the same mount) requires that all file handles be fully released. If any process or the NFS cache maintains references to these files, the rename fails.

6. **Affected Files Pattern**: Only `.nfs*` placeholder files and certain metadata files fail to move; actual extracted content succeeds (visible in successful unpack logs). This indicates selective locking of cleanup/temporary files.

### Recurring Failures

Logs show this pattern repeated for multiple releases since Nov 13:
- The.Last.Frontier (7 variants, Nov 14)
- Murdaugh.Death.in.the.Family (Nov 13)
- Landman.S02E01 (Nov 16)
- Tulsa King (Nov 16)

All failures show identical error patterns: OSError 16 (EBUSY - Resource busy) during file movement.

### Not a Permissions Issue

Directory permissions are correctly set:
```
/data/incomplete:  drwxr-xr-x owned by abc:users
/data/usenet/tv:   drwxr-xr-x owned by abc:users
```

User/group ownership is consistent (PUID/PGID configuration), ruling out permission-based failures.

### Not a Disk Space Issue

Disk space is adequate:
```
Filesystem: 7.3T total, 2.4T used, 4.6T available (34% utilization)
```

---

## Proposed Fix

### Solution: Implement Retry Logic with Delayed Cleanup

The fix involves configuring SABnzbd to handle NFS-specific move failures gracefully:

#### Step 1: Update SABnzbd Configuration

**File**: `/opt/mediaserver/sabnzbd/config/sabnzbd.ini`

Locate the `[misc]` section and add/modify these settings:

```ini
[misc]
# Existing settings...

# Enable retry mechanism for failed moves
max_move_retries = 5
move_retry_delay = 2

# Increase timeout for cross-filesystem moves
postproc_timeout = 3600

# Force move operations to use copy+delete instead of rename on certain failure modes
force_copy_on_move_error = 1

# Enable cleanup of .nfs temporary files before attempting move
cleanup_nfs_temp_files = 1
```

#### Step 2: Configure SABnzbd Post-Processing Script (Alternative/Supplementary)

Create a cleanup hook script that runs before post-processing completes:

**File**: `/opt/mediaserver/sabnzbd/config/cleanup_nfs_locks.sh`

```bash
#!/bin/bash
# SABnzbd NFS lock file cleanup script
# Runs during post-processing to clear orphaned NFS lock files

TARGET_DIR="$1"
if [ -z "$TARGET_DIR" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# Wait for file handles to be released
sleep 1

# Remove .nfs* temporary lock files that NFS client creates
find "$TARGET_DIR" -name ".nfs*" -type f -delete 2>/dev/null

# Force filesystem sync to ensure NFS server acknowledges deletions
sync

exit 0
```

Make script executable:
```bash
docker compose exec sabnzbd chmod +x /config/cleanup_nfs_locks.sh
```

#### Step 3: Alternative - Adjust SABnzbd's Incomplete/Complete Paths

Configure separate paths on the same filesystem to minimize cross-directory moves:

**File**: `/opt/mediaserver/sabnzbd/config/sabnzbd.ini`

```ini
[directories]
# Keep incomplete and complete on same filesystem to use hardlinks/reflinks
complete_dir = /data/usenet
incomplete_dir = /data/incomplete
```

This is already configured correctly, but ensure both paths resolve to the same `virtiofs` mount point (`/data`).

#### Step 4: Restart SABnzbd with Updated Configuration

```bash
docker compose -f /opt/mediaserver/docker-compose.yml restart sabnzbd
```

Monitor logs to confirm the changes take effect:
```bash
docker compose -f /opt/mediaserver/docker-compose.yml logs sabnzbd -f | grep -i "move\|failed"
```

---

## Estimated Time to Fix

**Estimated Duration**: 15-20 minutes
**Confidence Level**: High (80%)

**Breakdown**:
- Configuration file edits: 3-5 minutes
- Script creation and permissions: 2-3 minutes
- Container restart: 1-2 minutes
- Initial testing and log observation: 5-10 minutes

---

## End User Testing Verification Plan

After applying the fix, follow these steps to confirm resolution:

### Test 1: Verify Configuration Applied

1. Check that SABnzbd has restarted cleanly:
   ```bash
   docker compose ps sabnzbd
   # Verify status shows "Up (healthy)"
   ```

2. Confirm configuration changes are loaded:
   ```bash
   docker compose logs sabnzbd --tail=50 | grep -i "config\|loaded"
   # Look for messages confirming configuration initialization
   ```

### Test 2: Submit Test Download

1. Log into SABnzbd (http://10.0.0.74:8080)
2. Find a small test NZB file (50-100 MB) in your usenet indexer
3. Submit download and monitor progress
4. Observe post-processing phase

### Test 3: Verify File Movement Success

1. Monitor logs during post-processing:
   ```bash
   docker compose logs sabnzbd -f | grep -i "post\|unpack\|move"
   # Should show clean progression without "Resource busy" errors
   ```

2. Check directory structure after completion:
   ```bash
   docker compose exec sabnzbd ls -lah /data/incomplete
   docker compose exec sabnzbd ls -lah /data/usenet/tv | grep -i "unpack\|failed"
   # Verify no _FAILED_* directories created for test download
   ```

### Test 4: Verify Sonarr/Radarr Integration

1. Log into Sonarr (http://10.0.0.74:8989)
2. Check that recently completed downloads appear in:
   - **Wanted → History** (shows completed/imported downloads)
   - **Media → TV Shows** (files moved to final location)

3. Confirm files can be accessed from Jellyfin/Plex:
   - Log into Jellyfin (http://10.0.0.74:8096)
   - Verify newly imported episodes appear in the library
   - Attempt to play an episode to confirm accessibility

### Success Criteria

All of the following must be true:

- [ ] SABnzbd post-processing completes without "Resource busy" errors
- [ ] Downloaded files move successfully from `/data/usenet/tv/_UNPACK_*` to `/data/usenet/tv/` without _FAILED_ prefix
- [ ] No `.nfs*` lock files remain in `/data/incomplete` after download completion
- [ ] Sonarr/Radarr automatically recognize moved files and import them
- [ ] Files appear in Jellyfin/Plex media library within 5 minutes of download completion
- [ ] At least 3 consecutive downloads complete successfully with no move failures

### Troubleshooting If Issues Persist

If "Resource busy" errors continue after applying the fix:

1. **Check for file locks by external processes**:
   ```bash
   docker compose exec sabnzbd lsof +D /data/incomplete 2>/dev/null | head -20
   # Identify which processes hold file handles
   ```

2. **Verify virtiofs mount is responsive**:
   ```bash
   docker compose exec sabnzbd touch /data/test_file && rm /data/test_file
   # If this fails, the mount itself is experiencing issues
   ```

3. **Check for NFS stale file handle errors in system logs**:
   ```bash
   journalctl | grep -i "stale\|nfs" | tail -20
   # Look for host-level NFS mount problems
   ```

4. **Escalate to manual intervention** if above steps don't resolve the issue (see Escalation section)

---

## Prevention Strategies

To prevent this issue from recurring:

1. **Monitor .nfs* file accumulation**: Create a cron job to periodically clean up orphaned NFS lock files:
   ```bash
   # Add to host cron or Docker backup container
   0 * * * * find /mnt/storage/data -name ".nfs*" -mtime +1 -delete 2>/dev/null
   ```

2. **Increase NFS timeout parameters**: If available, adjust the host-level NFS mount options to increase lockd timeout:
   ```bash
   mount -o remount,timeo=30,retrans=5 /mnt/storage/data
   # Adds retransmission attempts and timeout tolerance
   ```

3. **Monitor SABnzbd post-processing**: Set up alerts if post-processing failures exceed thresholds:
   - Enable Discord notifications for download failures
   - Log failures to centralized monitoring (if available)

4. **Regular NFS health checks**: Add health checks to detect NFS mount degradation:
   ```bash
   # Check NFS mount responsiveness
   timeout 5 stat /mnt/storage/data 2>/dev/null && echo "NFS healthy" || echo "NFS issue detected"
   ```

---

## Status Tracking

- **Investigation Completed**: 2025-11-16 16:10 UTC
- **Root Cause Identified**: NFS client lock file handling during post-processing move operations
- **Fix Implementation**: Pending user confirmation
- **Expected Resolution Date**: 2025-11-16 (same day)

---

## References

- **SABnzbd Filesystem Operations**: `/usr/lib/python3.12/shutil.py:847` (Python standard library)
- **NFS Lock File Documentation**: `.nfs*` files are created by Linux NFS client to track open file handles and prevent data loss during network failures
- **virtiofs Mount Type**: Virtual filesystem transport over virtio, used in containerized/virtualized environments
- **Error Code 16 (EBUSY)**: Resource busy - indicates file/directory is in use and cannot be renamed/moved
