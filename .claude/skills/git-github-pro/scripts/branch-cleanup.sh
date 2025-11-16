#!/bin/bash
# Git Branch Cleanup Script
# Safely removes merged and stale branches
# Usage: ./branch-cleanup.sh [--dry-run] [--remote] [--days N]

set -e

DRY_RUN=false
REMOTE=false
DAYS=30
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --remote)
            REMOTE=true
            shift
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "Git Branch Cleanup Tool"
echo "=================================="
echo "Dry Run: $DRY_RUN"
echo "Cleaning Remote: $REMOTE"
echo "Stale Branch Age: $DAYS days"
echo ""

if [ "$REMOTE" = true ]; then
    echo "🌐 Remote Branch Cleanup"
    echo "------------------------"
    
    # Fetch latest info
    git fetch origin --prune
    
    # Find merged remote branches
    MERGED_BRANCHES=$(git branch -r --merged origin/main | grep -v "\*" | grep -v "main" | grep -v "develop" | grep -v "master")
    
    if [ -z "$MERGED_BRANCHES" ]; then
        echo "✅ No merged remote branches found"
    else
        echo "Merged branches ready for deletion:"
        echo "$MERGED_BRANCHES" | head -20
        
        if [ $DRY_RUN = false ]; then
            echo ""
            read -p "Delete these branches? (y/N) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "$MERGED_BRANCHES" | while read BRANCH; do
                    BRANCH_NAME=$(echo "$BRANCH" | sed 's/^.*\///')
                    git push origin --delete "$BRANCH_NAME" 2>/dev/null && echo "  ✓ Deleted: $BRANCH_NAME"
                done
            fi
        else
            echo "DRY RUN - Would delete:"
            echo "$MERGED_BRANCHES" | sed 's/^/  /'
        fi
    fi

else
    echo "🌿 Local Branch Cleanup"
    echo "----------------------"
    
    # Find merged local branches
    MERGED_BRANCHES=$(git branch --merged | grep -v "\*" | grep -v main | grep -v develop | grep -v master)
    
    if [ -z "$MERGED_BRANCHES" ]; then
        echo "✅ No merged local branches found"
    else
        echo "Merged branches ready for deletion:"
        echo "$MERGED_BRANCHES" | head -20
        MERGED_COUNT=$(echo "$MERGED_BRANCHES" | wc -l)
        
        if [ $DRY_RUN = false ]; then
            echo ""
            read -p "Delete these $MERGED_COUNT branches? (y/N) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "$MERGED_BRANCHES" | while read BRANCH; do
                    git branch -d "$BRANCH" 2>/dev/null && echo "  ✓ Deleted: $BRANCH"
                done
                echo "✅ Cleanup complete"
            fi
        else
            echo "DRY RUN - Would delete:"
            echo "$MERGED_BRANCHES" | sed 's/^/  /'
        fi
    fi

    # Find stale branches
    echo ""
    echo "Finding stale branches (no commits in $DAYS days)..."
    
    STALE_BRANCHES=$(git branch -v | awk -v days=$DAYS -v now=$(date +%s) '{
        branch=$1
        if ($1 != "*") {
            # Get last commit date
            cmd = "git log -1 --format=%ct " branch " 2>/dev/null"
            cmd | getline timestamp
            close(cmd)
            
            if (timestamp != "") {
                age_seconds = now - timestamp
                age_days = age_seconds / 86400
                
                if (age_days > days && branch !~ /^(main|master|develop)$/) {
                    print branch " (" int(age_days) " days old)"
                }
            }
        }
    }')

    if [ -z "$STALE_BRANCHES" ]; then
        echo "✅ No stale branches found"
    else
        echo "Stale branches:"
        echo "$STALE_BRANCHES" | head -20
        
        if [ $DRY_RUN = false ]; then
            read -p "Review and delete stale branches? (y/N) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "$STALE_BRANCHES" | awk '{print $1}' | while read BRANCH; do
                    read -p "Delete $BRANCH? (y/N/q) " -n 1 -r
                    echo ""
                    if [[ $REPLY =~ ^[Qq]$ ]]; then
                        break
                    fi
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        git branch -D "$BRANCH" 2>/dev/null && echo "  ✓ Deleted: $BRANCH"
                    fi
                done
            fi
        else
            echo "DRY RUN - Would prompt for deletion"
        fi
    fi

    # Prune remote tracking branches
    echo ""
    echo "Pruning remote tracking branches..."
    if [ $DRY_RUN = false ]; then
        git fetch origin --prune && echo "✅ Remote tracking branches pruned"
    else
        echo "DRY RUN: Would run 'git fetch origin --prune'"
    fi

fi

echo ""
echo "✅ Branch cleanup finished"
echo ""
echo "Current branches:"
git branch -v | head -10
