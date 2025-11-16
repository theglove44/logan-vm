#!/bin/bash
# GitHub PR Analysis Script
# Usage: ./pr-analysis.sh [owner/repo] [since-date] [output-file]
# Example: ./pr-analysis.sh myorg/myrepo "2024-11-01" pr-report.md

set -e

REPO="${1:-}"
SINCE_DATE="${2:-2024-11-01}"
OUTPUT="${3:-pr-report.md}"

if [ -z "$REPO" ]; then
    echo "Usage: $0 <owner/repo> [since-date] [output-file]"
    echo "Example: $0 myorg/myrepo 2024-11-01 report.md"
    exit 1
fi

# Verify gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    exit 1
fi

echo "Analyzing PRs for $REPO since $SINCE_DATE..."
echo ""

# Create report
{
    echo "# Pull Request Analysis Report"
    echo "Repository: [$REPO](https://github.com/$REPO)"
    echo "Period: Since $SINCE_DATE"
    echo "Generated: $(date)"
    echo ""

    # Summary Stats
    echo "## Summary Statistics"
    echo ""

    MERGED_COUNT=$(gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 --json number | jq 'length')
    OPEN_COUNT=$(gh pr list -R "$REPO" --state open --limit 1000 --json number | jq 'length')
    CLOSED_COUNT=$(gh pr list -R "$REPO" --state closed --search "closed:>=$SINCE_DATE" --limit 1000 --json number | jq 'length')

    echo "- **Merged PRs**: $MERGED_COUNT"
    echo "- **Open PRs**: $OPEN_COUNT"
    echo "- **Closed PRs**: $CLOSED_COUNT"
    echo ""

    # PR Authors
    echo "## Top Contributors"
    echo ""
    echo "| Author | Merged PRs | Open PRs |"
    echo "|--------|-----------|----------|"
    
    gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 --json author \
        --jq '.[] | .author.login' 2>/dev/null | sort | uniq -c | sort -rn | head -10 | while read COUNT AUTHOR; do
        OPEN=$(gh pr list -R "$REPO" --state open --author "$AUTHOR" --limit 100 --json number 2>/dev/null | jq 'length' || echo "0")
        printf "| %s | %d | %d |\n" "$AUTHOR" "$COUNT" "$OPEN"
    done
    
    echo ""

    # Recent Merged PRs
    echo "## Recently Merged PRs"
    echo ""

    gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 20 \
        --json number,title,author,mergedAt \
        --template '{{range .}}[#{{.number}}](https://github.com/'$REPO'/pull/{{.number}}): {{.title}}
- By: {{.author.login}} on {{.mergedAt | truncate 10}}

{{end}}'

    echo ""
    echo "## Open Pull Requests"
    echo ""

    OPEN_PRS=$(gh pr list -R "$REPO" --state open --limit 20 --json number,title,author,createdAt --jq 'length')
    
    if [ "$OPEN_PRS" -gt 0 ]; then
        gh pr list -R "$REPO" --state open --limit 20 \
            --json number,title,author,createdAt,reviewDecision \
            --template '{{range .}}[#{{.number}}](https://github.com/'$REPO'/pull/{{.number}}): {{.title}}
- By: {{.author.login}} 
- Created: {{.createdAt | truncate 10}}
- Review: {{.reviewDecision | default "Pending"}}

{{end}}'
    else
        echo "No open pull requests"
    fi

    echo ""
    echo "## PR Size Analysis"
    echo ""
    echo "| Range | Count |"
    echo "|-------|-------|"

    TINY=0
    SMALL=0
    MEDIUM=0
    LARGE=0

    gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 \
        --json additions,deletions --jq '.[] | (.additions + .deletions)' | while read SIZE; do
        if [ "$SIZE" -lt 50 ]; then
            ((TINY++))
        elif [ "$SIZE" -lt 200 ]; then
            ((SMALL++))
        elif [ "$SIZE" -lt 400 ]; then
            ((MEDIUM++))
        else
            ((LARGE++))
        fi
    done

    # Note: The loop above won't preserve variables, so we calculate differently
    TINY=$(gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 \
        --json additions,deletions --jq '[.[] | select((.additions + .deletions) < 50)] | length' 2>/dev/null || echo "0")
    SMALL=$(gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 \
        --json additions,deletions --jq '[.[] | select((.additions + .deletions) >= 50 and (.additions + .deletions) < 200)] | length' 2>/dev/null || echo "0")
    MEDIUM=$(gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 \
        --json additions,deletions --jq '[.[] | select((.additions + .deletions) >= 200 and (.additions + .deletions) < 400)] | length' 2>/dev/null || echo "0")
    LARGE=$(gh pr list -R "$REPO" --state merged --search "merged:>=$SINCE_DATE" --limit 1000 \
        --json additions,deletions --jq '[.[] | select((.additions + .deletions) >= 400)] | length' 2>/dev/null || echo "0")

    printf "| Tiny (<50) | %d |\n" "$TINY"
    printf "| Small (50-200) | %d |\n" "$SMALL"
    printf "| Medium (200-400) | %d |\n" "$MEDIUM"
    printf "| Large (400+) | %d |\n" "$LARGE"

    echo ""
    echo "_Report generated at $(date -u +'%Y-%m-%dT%H:%M:%SZ')_"

} > "$OUTPUT"

echo "✅ Report generated: $OUTPUT"
