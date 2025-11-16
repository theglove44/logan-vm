# GitHub API & CLI Operations

## GitHub CLI (gh) Essential Commands

The GitHub CLI (`gh`) provides powerful command-line access to GitHub functionality.

### Installation & Setup

```bash
# Install GitHub CLI
# macOS: brew install gh
# Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
# Windows: choco install gh

# Authenticate
gh auth login
# Follow prompts to authenticate

# Verify authentication
gh auth status
```

### Working with Pull Requests

```bash
# List open PRs in current repo
gh pr list

# Filter by status, author, assignee
gh pr list --state open --author @me --limit 10
gh pr list --state merged --search "merged:>=2024-11-01"

# View specific PR
gh pr view 123
gh pr view 123 --json title,body,author,reviews

# Create PR
gh pr create --title "Add new feature" --body "Description of changes"

# Create draft PR
gh pr create --draft --title "WIP: New feature"

# Create PR from specific branch
gh pr create --base main --head feature-branch --title "Title"

# Add reviewer
gh pr edit 123 --add-reviewer username

# Request review from team
gh pr edit 123 --add-reviewer team-name

# Add labels
gh pr edit 123 --add-label "bug,critical"

# Review PR
gh pr review 123 --approve
gh pr review 123 --comment --body "Please clarify this part"
gh pr review 123 --request-changes --body "Needs revision"

# Merge PR
gh pr merge 123 --squash  # squash merge
gh pr merge 123 --rebase  # rebase merge
gh pr merge 123 --merge   # merge commit

# Close PR
gh pr close 123
```

### Working with Issues

```bash
# List issues
gh issue list
gh issue list --state closed --assignee @me

# View issue
gh issue view 123

# Create issue
gh issue create --title "Bug report" --body "Description"

# Add labels
gh issue edit 123 --add-label "bug,help-wanted"

# Assign to user
gh issue edit 123 --assignee username

# Close issue
gh issue close 123 --reason "completed"

# Comment on issue
gh issue comment 123 --body "This is a comment"
```

### Working with Branches

```bash
# List branches
gh api repos/{owner}/{repo}/branches

# Delete branch
gh api repos/{owner}/{repo}/git/refs/heads/{branch} -X DELETE

# Get branch protection status
gh api repos/{owner}/{repo}/branches/main --jq '.protection'

# Update branch protection
gh api repos/{owner}/{repo}/branches/main/protection \
  -X PUT \
  -F required_status_checks[strict]=true \
  -F required_pull_request_reviews[required_approving_review_count]=2
```

### Working with Releases

```bash
# List releases
gh release list

# View specific release
gh release view v1.0.0

# Create release
gh release create v1.0.0 --title "Version 1.0.0" --notes "Release notes here"

# Create pre-release
gh release create v1.0.0-beta --title "Version 1.0.0 Beta" --prerelease

# Upload asset
gh release upload v1.0.0 ./build/app.tar.gz

# Delete release
gh release delete v1.0.0
```

### Useful JSON Output

```bash
# Get PR data as JSON for processing
gh pr list --json number,title,author,mergedAt --state merged

# Format output
gh pr list --json number,title,author --template '{{range .}}{{.number}}: {{.title}} ({{.author.login}}){{"\n"}}{{end}}'

# Extract specific fields
gh pr view 123 --json number --jq '.number'

# Complex queries
gh pr list --json createdAt,updatedAt,author --jq '.[] | select(.author.login == "username")'
```

## GitHub REST API

Direct API calls for advanced operations:

### Authentication

```bash
# Using gh CLI (handles auth automatically)
gh api path/to/endpoint

# Using curl with token
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/owner/repo
```

### Common API Endpoints

```bash
# Get repository info
gh api repos/{owner}/{repo}

# List pull requests
gh api repos/{owner}/{repo}/pulls?state=open

# Get pull request details
gh api repos/{owner}/{repo}/pulls/{pull_number}

# Get pull request reviews
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews

# List commits in PR
gh api repos/{owner}/{repo}/pulls/{pull_number}/commits

# Get commit details
gh api repos/{owner}/{repo}/commits/{sha}

# List issues
gh api repos/{owner}/{repo}/issues

# Get issue details
gh api repos/{owner}/{repo}/issues/{issue_number}

# List pull request files
gh api repos/{owner}/{repo}/pulls/{pull_number}/files
```

### Creating Resources via API

```bash
# Create a comment on PR
gh api repos/{owner}/{repo}/issues/{issue_number}/comments \
  -F body="This is a comment"

# Create a review on PR
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews \
  -X POST \
  -F event=APPROVE \
  -F body="Looks good!"

# Request reviewers
gh api repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers \
  -X POST \
  -F reviewers='["username1","username2"]'
```

### Pagination

```bash
# Get paginated results
gh api repos/{owner}/{repo}/pulls --paginate

# Limit results
gh api repos/{owner}/{repo}/pulls?per_page=100

# Process large result sets in scripts
gh api --paginate repos/{owner}/{repo}/pulls \
  --jq '.[] | {number: .number, title: .title}'
```

## Automation Patterns

### Creating Issue Summary

```bash
#!/bin/bash
# Generate weekly issue summary

OWNER="myorg"
REPO="myrepo"
SINCE=$(date -d "7 days ago" +%Y-%m-%dT%H:%M:%SZ)

echo "# Weekly Issues Report"
echo "Issues created since $SINCE:"
echo ""

gh api repos/$OWNER/$REPO/issues \
  --jq ".[] | select(.created_at > \"$SINCE\") | 
  \"- [#\(.number)](\(.html_url)): \(.title) (@\(.user.login))\"" \
  --paginate
```

### Mass Close Issues with Label

```bash
#!/bin/bash
# Close all 'wontfix' issues

OWNER="myorg"
REPO="myrepo"

gh api repos/$OWNER/$REPO/issues?labels=wontfix \
  --jq '.[] | .number' \
  --paginate | \
while read ISSUE_NUM; do
  gh issue close $ISSUE_NUM -R $OWNER/$REPO
  echo "Closed issue #$ISSUE_NUM"
done
```

### Sync PR Statuses

```bash
#!/bin/bash
# Update all PR labels based on status checks

OWNER="myorg"
REPO="myrepo"

gh api repos/$OWNER/$REPO/pulls?state=open \
  --jq '.[] | .number' | \
while read PR_NUM; do
  STATUS=$(gh api repos/$OWNER/$REPO/commits/$(gh pr view $PR_NUM -R $OWNER/$REPO --json commits --jq '.commits[0].oid')/check-runs --jq '.check_runs[0].conclusion')
  
  if [ "$STATUS" = "success" ]; then
    gh pr edit $PR_NUM -R $OWNER/$REPO --add-label "✅ passing"
  else
    gh pr edit $PR_NUM -R $OWNER/$REPO --add-label "❌ failing"
  fi
done
```

## GitHub GraphQL API

For complex queries and efficient data fetching:

```bash
# Query PR data with GraphQL
gh api graphql -f query='
  query {
    repository(owner:"owner", name:"repo") {
      pullRequests(first: 10, states: OPEN) {
        edges {
          node {
            number
            title
            author {
              login
            }
            reviews(first: 5) {
              nodes {
                author {
                  login
                }
                state
              }
            }
          }
        }
      }
    }
  }
'
```

## Advanced Scripting

### PR Diff Stats

```bash
#!/bin/bash
# Get statistics on PR changes

PR_NUMBER=$1
OWNER="owner"
REPO="repo"

echo "PR #$PR_NUMBER Statistics:"
echo "=========================="

# Get files changed
FILES=$(gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/files --jq '.[].filename')
FILE_COUNT=$(echo "$FILES" | wc -l)

# Get total additions/deletions
ADDITIONS=$(gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/files --jq '[.[].additions] | add')
DELETIONS=$(gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/files --jq '[.[].deletions] | add')

echo "Files Changed: $FILE_COUNT"
echo "Lines Added: $ADDITIONS"
echo "Lines Deleted: $DELETIONS"
echo "Net Change: $(($ADDITIONS - $DELETIONS))"
```

### Review Status Dashboard

```bash
#!/bin/bash
# Show PR review status

OWNER="owner"
REPO="repo"

echo "Open PRs requiring reviews:"
echo "==========================="

gh api repos/$OWNER/$REPO/pulls?state=open \
  --jq '.[] | 
  "PR #\(.number): \(.title)\n" +
  "  Author: \(.user.login)\n" +
  "  Reviews: \(.review_comments) comments\n" +
  "  Status: \(if .draft then "DRAFT" else "READY" end)"' \
  --paginate
```
