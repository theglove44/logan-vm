# Pull Request Strategies & Reporting

## PR Creation Best Practices

### Effective PR Description Template

Structure PRs to make review easy and decisions clear:

```markdown
## Description
Brief description of what this PR does and why.

## Related Issue
Closes #123
Related to #456

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Specific change 1
- Specific change 2
- Specific change 3

## Testing Performed
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

**How to test:** Clear steps to verify the changes work

## Checklist
- [ ] My code follows the project style guidelines
- [ ] I have self-reviewed my own code
- [ ] I have commented complex sections
- [ ] I have updated relevant documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective
- [ ] New and existing tests pass locally with my changes
- [ ] Any dependent changes have been merged
```

### PR Size Guidelines

Keep PRs focused and reviewable:

| Size | Lines Changed | Review Time | Frequency | Merge Strategy |
|------|---------------|------------|-----------|----------------|
| Tiny | <50 | <5 min | Frequent | Direct commit (or squash) |
| Small | 50-200 | 10-15 min | Frequent | Squash merge |
| Medium | 200-400 | 20-30 min | Regular | Squash or rebase merge |
| Large | 400+ | >30 min | Rare | Merge commit (preserve history) |

**Large PRs should be split into multiple PRs when possible.**

### Writing Commit Messages in PRs

Follow conventional commits for clear history:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

Examples:
```
feat(auth): add two-factor authentication

Implement TOTP-based 2FA for user accounts.
Users can enable 2FA in security settings and receive backup codes.

Closes #542
```

```
fix(api): handle null response in user endpoint

Add null checks before accessing response properties.
Prevents crashes when API returns empty user object.

Closes #533
```

## PR Analysis & Reporting

### Generating PR Statistics

Query GitHub API to analyze PR patterns:

```bash
# Count merged PRs this month
gh pr list --state merged --search "merged:>=2024-11-01" --limit 1000

# Get average PR review time
gh pr list --state merged --json mergedAt,createdAt --limit 100

# PRs by contributor
gh pr list --state merged --json author --limit 1000 | jq -r '.[] | .author.login' | sort | uniq -c

# PRs by size (rough estimate)
gh pr list --state merged --json additions,deletions --limit 100 | \
  jq '.[] | (.additions + .deletions) as $size | if $size < 50 then "tiny" elif $size < 200 then "small" elif $size < 400 then "medium" else "large" end' | sort | uniq -c
```

### Measuring PR Health

Track these metrics to improve review process:

**Throughput Metrics:**
- Average time from creation to merge
- Number of PRs merged per week/month
- PR creation rate vs merge rate

**Quality Metrics:**
- Number of commits per PR (lower = more focused)
- Churn rate (lines added vs removed)
- Revert rate (how many merged PRs are reverted)

**Collaboration Metrics:**
- Average review comments per PR
- Time to first review
- Number of re-reviews needed

### Automated PR Reporting

Create GitHub Actions workflow to generate reports:

```yaml
name: Weekly PR Report
on:
  schedule:
    - cron: '0 9 * * MON'

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate PR Report
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "# Weekly PR Report" >> report.md
          echo "## Last 7 Days" >> report.md
          echo "" >> report.md
          
          gh pr list --state merged --search "merged:>=$(date -d '7 days ago' +%Y-%m-%d)" --json number,title,author,mergedAt --template '### {{.number}}: {{.title}}{{"\n"}}By: {{.author.login}}{{"\n"}}Merged: {{.mergedAt}}{{"\n\n"}}'
          
      - name: Comment on Issue
        run: |
          gh issue comment 1 --body-file report.md
```

## PR Review Practices

### Effective Code Review

**As a reviewer:**
1. Start with high-level understanding (what and why)
2. Check for logic errors and edge cases
3. Look for code style/convention violations
4. Verify tests cover new functionality
5. Check performance implications
6. Provide constructive feedback

**Template for feedback:**

```markdown
### ✅ What's Good
- Clear commit messages
- Good test coverage
- Nice refactoring

### 🔍 Questions
- Why did you choose X over Y approach?
- Have you considered edge case Z?

### 🚀 Suggestions
- Could simplify line 42 using destructuring
- Consider extracting this function to utils

### ⚠️ Concerns
- This might impact performance in high-traffic scenarios
```

### Addressing Feedback

```bash
# Make requested changes
git add file.js
git commit --amend  # for small fixes
# or
git commit -m "fix: address review feedback"

# Update PR
git push --force-with-lease origin feature-branch

# Request re-review in GitHub UI
# Click "Re-request review" on specific reviewers
```

## Advanced PR Techniques

### Cherry-picking to Multiple Branches

Apply a fix to multiple release branches:

```bash
# Commit fix to current branch
git commit -m "fix: critical bug in payment processing"
git push origin fix/payment-bug

# Merge to main first, then cherry-pick to releases
git checkout main
git pull
git merge fix/payment-bug
git push

# Cherry-pick to release branches
git checkout release/2.0
git pull
git cherry-pick <commit-hash>
git push origin release/2.0

git checkout release/1.8
git pull
git cherry-pick <commit-hash>
git push origin release/1.8
```

### Squashing & Rebasing Before Merge

Clean up commit history:

```bash
# Interactive rebase on origin/main
git fetch origin
git rebase -i origin/main

# In editor:
# pick abc123 first commit
# squash def456 second commit
# squash ghi789 third commit

# Update PR with rebased branch
git push --force-with-lease origin feature-branch
```

### Creating PR Templates

Repository-level templates in `.github/pull_request_template.md`:

```markdown
## What does this PR do?
<!-- Brief description of changes -->

## Why are we doing this?
<!-- Motivation and context -->

## Related Issues
<!-- Link to related issues using # -->
Closes #

## Type of Change
<!-- Mark relevant option with X -->
- [ ] Bugfix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing Instructions
<!-- How can reviewers verify this works? -->

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex sections
```

## Handling Complex Review Scenarios

### Disputed Changes

When review comments lead to disagreement:

1. **Discuss in PR comment thread** - provide rationale for approach
2. **Reference documentation** - link to style guide or best practices
3. **Offer alternatives** - suggest compromises if applicable
4. **Escalate if needed** - involve code maintainers/leads

### Large Refactorings

Breaking down massive PRs:

```bash
# Phase 1: Structure changes (no logic change)
git checkout -b refactor/move-files
# Move files without changing functionality
git push -u origin refactor/move-files
# Create and merge PR

# Phase 2: Logic updates
git checkout -b refactor/update-imports
# Update all imports in moved files
git push -u origin refactor/update-imports
# Create and merge PR

# Phase 3: Optimization
git checkout -b refactor/simplify-logic
# Make logic improvements now that structure is clear
git push -u origin refactor/simplify-logic
# Create and merge PR
```

### Reverting PRs

When a merged PR causes issues:

```bash
# Find the merge commit
git log --oneline | grep "Merge pull request"

# Revert the merge
git revert -m 1 <merge-commit-hash>
git push origin main

# Create new PR to re-implement with fixes
git checkout -b fix/reimplement-feature
# Make improvements to original approach
```
