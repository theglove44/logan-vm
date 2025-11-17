#!/bin/bash
# SABnzbd post-processing script - Handles file movement with virtiofs workaround
#
# This script runs at the host level to bypass virtiofs cache coherency issues
# Operating on /mnt/storage mount point (host filesystem) instead of container's /data mount
#
# Parameters passed by SABnzbd (in order):
# $1 = Script directory
# $2 = NZB filename
# $3 = Folder name (job folder in incomplete dir)
# $4 = Job name (from NZB)
# $5 = Category (tv, movies, etc.)
# $6 = Post-processing group/status (0=success, 1=failure)
# $7 = Status code

SCRIPT_DIR="$1"
NZB_FILENAME="$2"
FOLDER="$3"
JOB_NAME="$4"
CATEGORY="$5"
PP_STATUS="$6"
STATUS_CODE="$7"

# Logging - use container path that maps to host /opt/mediaserver/sabnzbd
# Inside container: /config = host's /opt/mediaserver/sabnzbd
LOG_FILE="/config/postprocess.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

log "=== Post-processing started ==="
log "Job: $JOB_NAME | Folder: $FOLDER | Category: $CATEGORY | PP_Status: $PP_STATUS | Status_Code: $STATUS_CODE"

# Only proceed if post-processing was successful (PP_STATUS == 0)
if [ "$PP_STATUS" != "0" ]; then
    log "Skipping move: post-processing failed (PP_STATUS=$PP_STATUS, Status_Code=$STATUS_CODE)"
    exit 1
fi

# When running as a notification script from inside the container:
# - /data maps to host's /mnt/storage/data
# - /config maps to host's /opt/mediaserver/sabnzbd
# So we use container paths here
SOURCE_DIR="/data/incomplete/$FOLDER"
DEST_BASE="/data/usenet"

log "Source: $SOURCE_DIR"
log "Destination base: $DEST_BASE"

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    log "ERROR: Source directory not found: $SOURCE_DIR"
    exit 1
fi

# Determine category-based destination
DEST_DIR="$DEST_BASE"
case "$CATEGORY" in
    movies|movie*)
        DEST_DIR="$DEST_BASE/movies"
        ;;
    tv|tv-*|series|show*)
        DEST_DIR="$DEST_BASE/tv"
        ;;
    *)
        DEST_DIR="$DEST_BASE"
        ;;
esac

log "Final destination: $DEST_DIR"

# Create destination directory if needed
if ! mkdir -p "$DEST_DIR" 2>/dev/null; then
    log "ERROR: Could not create destination directory: $DEST_DIR"
    exit 1
fi

# Move with retries at host level
# This bypasses virtiofs container cache issues because we're operating on host filesystem
MAX_RETRIES=5
RETRY_DELAY=2
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_RETRIES ]; do
    FINAL_DEST="$DEST_DIR/$(basename "$SOURCE_DIR")"

    # Attempt the move
    if mv "$SOURCE_DIR" "$FINAL_DEST" 2>/dev/null; then
        log "SUCCESS: Moved to $FINAL_DEST"
        log "=== Post-processing completed successfully ==="
        exit 0
    fi

    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -lt $MAX_RETRIES ]; then
        log "Attempt $ATTEMPT/$MAX_RETRIES failed, waiting ${RETRY_DELAY}s before retry..."
        sleep "$RETRY_DELAY"
    fi
done

# All retries failed
log "FAILED: Could not move $SOURCE_DIR after $MAX_RETRIES attempts"
log "Files may remain in incomplete directory - manual intervention may be needed"
log "=== Post-processing completed with FAILURE ==="
exit 1
