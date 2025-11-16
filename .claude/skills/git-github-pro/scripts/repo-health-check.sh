#!/bin/bash
# Git Repository Health Check Script
# Usage: ./repo-health-check.sh [path-to-repo]

set -e

REPO_PATH="${1:-.}"

if [ ! -d "$REPO_PATH/.git" ]; then
    echo "Error: Not a git repository: $REPO_PATH"
    exit 1
fi

cd "$REPO_PATH"

echo "==================================="
echo "  Git Repository Health Check"
echo "==================================="
echo ""

# Basic Info
echo "📊 Repository Information"
echo "------------------------"
REPO_NAME=$(basename "$PWD")
echo "Repository: $REPO_NAME"
echo "Path: $PWD"

# Branches
echo ""
echo "🌿 Branch Information"
echo "--------------------"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current Branch: $CURRENT_BRANCH"

TOTAL_BRANCHES=$(git branch -a | wc -l)
LOCAL_BRANCHES=$(git branch | wc -l)
REMOTE_BRANCHES=$(git branch -r | wc -l)

echo "Total Branches: $TOTAL_BRANCHES (Local: $LOCAL_BRANCHES, Remote: $REMOTE_BRANCHES)"
echo ""
echo "Recent Branches:"
git branch -v | head -10

# Commits
echo ""
echo "📝 Commit Information"
echo "--------------------"
TOTAL_COMMITS=$(git rev-list --all --count)
echo "Total Commits: $TOTAL_COMMITS"

echo ""
echo "Recent Commits:"
git log --oneline -5

# Status
echo ""
echo "📈 Working Directory Status"
echo "---------------------------"
STATUS=$(git status --porcelain)
if [ -z "$STATUS" ]; then
    echo "✅ Working directory is clean"
else
    echo "⚠️  Uncommitted changes:"
    echo "$STATUS" | head -10
    REMAINING=$(echo "$STATUS" | wc -l)
    if [ $REMAINING -gt 10 ]; then
        echo "... and $((REMAINING - 10)) more"
    fi
fi

# Stashes
echo ""
echo "🔦 Stash Information"
echo "-------------------"
STASH_COUNT=$(git stash list | wc -l)
if [ $STASH_COUNT -eq 0 ]; then
    echo "✅ No stashes"
else
    echo "⚠️  $STASH_COUNT stash(es):"
    git stash list
fi

# Repository Integrity
echo ""
echo "🔍 Repository Integrity"
echo "-----------------------"
if git fsck --quick >/dev/null 2>&1; then
    echo "✅ Repository integrity check passed"
else
    echo "❌ Repository has integrity issues"
fi

# Remotes
echo ""
echo "🌐 Remote Information"
echo "--------------------"
if git remote -v | grep -q .; then
    echo "Remotes:"
    git remote -v
    echo ""
    echo "Tracking Status:"
    git branch -vv | head -5
else
    echo "⚠️  No remotes configured"
fi

# Size
echo ""
echo "💾 Repository Size"
echo "------------------"
REPO_SIZE=$(du -sh .git | cut -f1)
echo "Git Directory Size: $REPO_SIZE"

# Packed vs Loose
PACKED=$(git count-objects -v | grep "^count:" | awk '{print $2}')
LOOSE=$(git count-objects -v | grep "^size:" | awk '{print $2}')
echo "Loose Objects: $PACKED"
echo "Packed Size: $LOOSE KB"

if [ "$LOOSE" -gt 10000 ]; then
    echo ""
    echo "💡 Recommendation: Run 'git gc --aggressive' to optimize repository"
fi

# Summary
echo ""
echo "==================================="
echo "✅ Health check complete"
echo "==================================="
