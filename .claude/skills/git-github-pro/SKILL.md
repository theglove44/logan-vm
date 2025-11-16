---
name: git-github-pro
description: Complete Git repository management with GitHub Actions integration. Use when working with Git workflows including branch management, feature branches, pull request operations, commit management, repository health, and GitHub Actions automation. Supports local operations, remote synchronization, PR creation and analysis, and CI/CD pipeline management.
---

# Git & GitHub Pro

Master Git repository management and GitHub Actions automation. This skill provides comprehensive workflows for professional Git practices including branching strategies, pull request management, repository maintenance, and CI/CD automation.

## Core Workflows

### Branch Management

**Creating feature branches:** Always use descriptive branch names following conventional patterns. Create feature branches from the latest main/master:
```bash
git fetch origin
git checkout -b feature/user-auth-system
# or for bug fixes: git checkout -b fix/login-validation-bug
# or for chores: git checkout -b chore/update-dependencies
```

**Branch protection and maintenance:** Ensure branches are up-to-date before merging:
```bash
git fetch origin
git rebase origin/main  # or --merge for merge commits
git push --force-with-lease origin feature/branch-name
```

Keep local branches clean by deleting merged branches:
```bash
git branch -d local-branch-name  # deleted locally
git push origin --delete remote-branch-name  # delete on remote
```

### Commit Hygiene

Write atomic, well-described commits:
- One logical change per commit
- Use present tense: "Add user authentication" not "Added authentication"
- Start with type prefix: feat, fix, refactor, docs, test, chore, style
- Include context in commit body when needed

Stage strategically:
```bash
git add file1.js file2.js  # specific files
git add --patch  # interactive, select hunks
git diff --staged  # review before committing
```

### Pull Request Workflow

**Creating PRs with context:**

1. Push feature branch and create PR with comprehensive description
2. Include "Why" not just "What" - motivation and context
3. Reference related issues using `#issue-number`
4. Use PR templates if repository has them (check `.github/pull_request_template.md`)

**Review and iteration:**

- Keep PRs focused and reasonably sized (<400 lines when possible)
- Respond to review comments promptly with clarifications or code updates
- Use `git commit --amend` for fixup commits on the same feature
- Force-push to update PR: `git push --force-with-lease`
- Request re-review after addressing all feedback

**Merging strategies:**

- **Squash merge** for feature branches (single logical commit to main)
- **Rebase merge** for bug fixes (keeps linear history)
- **Merge commits** for significant features/releases (preserves branch history)

### Repository Health

**Check repository status:**
```bash
git status  # working directory state
git log --oneline -n 10  # recent commits
git branch -a  # all branches local and remote
git remote -v  # configured remotes
```

**Detect issues:**
```bash
git fsck  # filesystem integrity check
git gc --aggressive  # optimize repository
git log --all --oneline --graph --decorate  # visualize history
```

### Working with Uncommitted Changes

**Save work temporarily:**
```bash
git stash  # save changes and reset working directory
git stash list  # view all stashes
git stash pop  # restore most recent stash
git stash apply stash@{n}  # restore specific stash without removing
```

**Discard changes safely:**
```bash
git diff  # review changes before discarding
git checkout -- file.js  # discard changes in single file
git reset --hard  # discard all uncommitted changes (destructive)
```

### Handling Merge Conflicts

When encountering conflicts during merge/rebase:

1. Review conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
2. Manually edit files to resolve conflicts (or use merge tool)
3. Test the resolved code
4. Stage resolved files: `git add resolved-file.js`
5. Complete merge: `git commit` or rebase: `git rebase --continue`

Use tools for complex conflicts:
```bash
git mergetool  # launches configured merge tool
```

## GitHub Actions Integration

### Workflow Files Location

All GitHub Actions workflows live in `.github/workflows/` directory as YAML files. They trigger automatically on events (push, pull_request, schedule, manual dispatch).

### Essential Workflows to Maintain

**PR Quality Checks:**
- Lint and format validation
- Type checking (TypeScript, etc.)
- Unit and integration tests
- Code coverage reports
- Security scanning

**Continuous Integration:**
- Build validation on every push
- Automated testing on PR creation
- Status checks that block merging until passing

**Repository Maintenance:**
- Auto-labeling PRs based on files changed
- Dependency updates (Dependabot integration)
- Stale issue/PR management
- Automated changelog generation

**Release Automation:**
- Version bumping (semantic versioning)
- Release creation and publication
- Artifact building and distribution

### Working with Workflows

**Monitoring workflow runs:**
- Check "Actions" tab in GitHub UI for run status
- View logs for failed steps to debug
- Re-run failed workflows after fixes

**Debugging failing workflows:**
```yaml
# Add debug logging to workflow steps
- name: Debug step
  run: |
    echo "DEBUG: Current branch: ${{ github.ref }}"
    ls -la
    pwd
```

**Common patterns:**

```yaml
# Run tests on PR
on:
  pull_request:
    branches: [main, develop]
    
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: npm ci
      - run: npm run lint
      - run: npm test
```

## Git Aliases for Efficiency

Configure useful aliases in `.gitconfig` or set locally:
```bash
git config --local alias.co checkout
git config --local alias.br branch
git config --local alias.ci commit
git config --local alias.st status
git config --local alias.unstage 'reset HEAD --'
git config --local alias.last 'log -1 HEAD'
git config --local alias.visual 'log --graph --oneline --all'
git config --local alias.sync 'pull --rebase origin main'
```

## Common Scenarios

See detailed reference files for specific use cases:
- **PR analysis & reporting**: See [references/pr-strategies.md](references/pr-strategies.md)
- **Branch strategies & patterns**: See [references/branching-strategies.md](references/branching-strategies.md)  
- **GitHub API operations**: See [references/github-api.md](references/github-api.md)
- **Advanced Git techniques**: See [references/advanced-git.md](references/advanced-git.md)

## Quick Diagnostics

When something goes wrong:

```bash
# Check what changed
git diff  # unstaged changes
git diff --staged  # staged changes
git diff main...HEAD  # changes in current branch vs main

# Check history
git log --oneline --all  # see all commits
git reflog  # see all HEAD movements (recovery tool)

# Validate state
git status  # current state
git fsck --full  # check integrity
```

Use `git reflog` to recover lost commits—Git keeps detailed history of all HEAD movements.
