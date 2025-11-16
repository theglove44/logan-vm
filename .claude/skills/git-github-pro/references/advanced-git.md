# Advanced Git Techniques

## History Rewriting & Cleanup

### Interactive Rebase for History Cleanup

Modify commit history before pushing:

```bash
# Rebase last 5 commits
git rebase -i HEAD~5

# In editor, commands for each commit:
pick    - keep commit as-is
reword  - change commit message
edit    - stop to amend this commit
squash  - combine with previous commit
fixup   - like squash, but discard message
drop    - remove commit entirely
exec    - run shell command
break   - pause rebase here
```

Example workflow:

```bash
# Start interactive rebase
git rebase -i origin/main

# Editor shows:
# pick abc123 WIP: auth system
# pick def456 Add login component
# pick ghi789 Fixup: remove console.logs
# pick jkl012 Add tests

# Change to:
# reword abc123 feat: implement auth system
# pick def456 Add login component
# fixup ghi789 Fixup: remove console.logs
# pick jkl012 Add tests

# Git replays commits, prompts for reword
git push --force-with-lease origin feature-branch
```

### Splitting Commits

Separate a commit into multiple focused commits:

```bash
# Start interactive rebase
git rebase -i HEAD~3

# Mark commit to edit:
# edit abc123 mixed: auth and routing changes

# Stop at that commit, then:
git reset HEAD~1  # unstage all changes

# Stage and commit first change
git add auth/
git commit -m "feat: add authentication module"

# Stage and commit second change
git add routing/
git commit -m "feat: update routing configuration"

# Continue rebase
git rebase --continue
```

### Cleaning Up Before Push

Polish your work before making public:

```bash
# View commits you're about to push
git log origin/main..HEAD --oneline

# If history is messy:
git rebase -i origin/main

# Final check:
git log origin/main..HEAD --oneline
git diff origin/main  # verify all changes

# Force push to update PR
git push --force-with-lease
```

## Working with Remote Branches

### Tracking and Syncing

```bash
# See tracking relationship
git branch -vv

# Set upstream for current branch
git branch -u origin/feature-branch
# or
git branch --set-upstream-to=origin/feature-branch

# Pull changes from upstream
git pull  # shorthand when tracking is set

# Fetch all remotes
git fetch --all

# Update all tracking branches
git remote update
```

### Handling Diverged History

When local and remote branches have diverged:

```bash
# Check if behind/ahead
git status

# Option 1: Rebase (linear history)
git rebase origin/main
git push --force-with-lease

# Option 2: Merge (preserve history)
git merge origin/main
git push

# Option 3: Reset to remote (lose local changes)
git reset --hard origin/main
```

## Searching and Finding in Git

### Finding Code Changes

```bash
# Find when line was changed
git blame filename.js

# Find which commits changed specific code
git log -S "search string" --oneline

# Find commits by grep in message
git log --grep="feature name" --oneline

# Find commits by author
git log --author="name" --oneline

# Find commits touching specific file
git log --oneline -- path/to/file.js

# Show what changed in commit
git show <commit-hash>
```

### Complex Search Queries

```bash
# Commits changing specific function
git log -S "functionName" --oneline -- path/to/file.js

# Commits in date range
git log --since="2024-01-01" --until="2024-12-31" --oneline

# Commits by multiple authors
git log --author="Alice\|Bob" --oneline

# Commits not yet merged to main
git log main..HEAD --oneline

# All commits reachable from current, but not from main
git log --not main --oneline
```

## Refspec and Advanced Pushing

### Push to Non-Standard Branches

```bash
# Push to branch with different name on remote
git push origin local-name:remote-name

# Delete remote branch by pushing nothing
git push origin :branch-to-delete
# or
git push origin --delete branch-to-delete

# Push all branches
git push --all origin

# Push all tags
git push --tags origin

# Push specific tag
git push origin v1.0.0
```

## Submodules and Subtrees

### Working with Submodules

Include other repositories within yours:

```bash
# Add submodule
git submodule add https://github.com/user/repo.git path/to/submodule

# Clone repo with submodules
git clone --recurse-submodules <repo-url>

# Update submodules to latest
git submodule update --remote

# Update to specific version
cd path/to/submodule
git checkout <commit-or-tag>
cd ../..
git add path/to/submodule
git commit -m "Update submodule to latest"
```

### Using Subtrees (Alternative to Submodules)

Better for small dependencies:

```bash
# Add subtree
git subtree add --prefix=vendor/lib https://github.com/user/repo.git main --squash

# Update subtree
git subtree pull --prefix=vendor/lib https://github.com/user/repo.git main --squash

# Contribute back to upstream
git subtree push --prefix=vendor/lib https://github.com/user/repo.git main
```

## Bisect for Finding Issues

### Binary Search for Regression

Find which commit introduced a bug:

```bash
# Start bisect session
git bisect start

# Mark current (broken) commit
git bisect bad

# Mark known good commit
git bisect good v1.0.0

# Git checks out commit in middle
# Test the commit...

# Mark as good or bad
git bisect good  # or git bisect bad

# Git narrows search range, repeats
# Eventually finds exact commit

# End bisect session
git bisect reset
```

Example:

```bash
git bisect start
git bisect bad HEAD
git bisect good v2.0.0
# Git checks out mid-point commit
npm test  # verify if bug exists
git bisect bad  # bug present
# Git narrows range further...
# Eventually: "abc123 is the first bad commit"
git show abc123  # see what changed
git bisect reset
```

## Stash Advanced Usage

### Selective Stashing

```bash
# Stash specific files only
git stash push -m "work in progress" path/to/file.js

# Stash with pattern
git stash push -m "api changes" src/api/

# Stash untracked files too
git stash -u

# Stash including ignored files
git stash -a

# List all stashes
git stash list

# Show stash contents
git stash show stash@{0}
git stash show -p stash@{0}  # with diff

# Apply specific stash to new branch
git stash branch feature-branch stash@{0}

# Delete stash
git stash drop stash@{0}

# Delete all stashes
git stash clear
```

## Reflog for Recovery

### Recovering Lost Commits

Git keeps 30-day history of HEAD movements:

```bash
# View all HEAD movements
git reflog

# Example output:
# abc123 HEAD@{0}: checkout: moving from main to feature
# def456 HEAD@{1}: commit: fix: resolve issue
# ghi789 HEAD@{2}: rebase -i: finished

# Recover lost commit
git checkout abc123
# or create branch from it
git branch recovered-work abc123
git checkout recovered-work

# Recover accidentally deleted branch
git reflog
# Find the commit hash
git branch branch-name <commit-hash>
```

## Worktrees for Parallel Work

### Multiple Branches Simultaneously

```bash
# Create new worktree for branch
git worktree add -b feature/new-feature ../feature-work

# List active worktrees
git worktree list

# Remove worktree when done
git worktree remove ../feature-work

# Prune stale worktree entries
git worktree prune
```

Useful for context switching without stashing:

```bash
# Main directory: working on feature/auth
# Create worktree for hotfix:
git worktree add -b hotfix/security-patch ../hotfix-work

# In ../hotfix-work:
# Make changes, test, commit, push
# Create and merge PR

# Back in main directory: still on feature/auth
# Continue work where you left off
```

## Configuration and Optimization

### Performance Optimization

```bash
# Garbage collection
git gc --aggressive

# Repack objects
git repack -A -d

# Clean up reflog
git reflog expire --expire=now --all

# Shallow clone for large repos (faster)
git clone --depth 1 <repo-url>

# Shallow fetch (limited history)
git fetch --depth 10
```

### Useful Git Configurations

```bash
# Speed up operations
git config core.preloadindex true
git config core.checkStat minimal

# Automatic garbage collection
git config gc.autodetach true

# Better diff algorithm
git config diff.algorithm histogram

# Blame ignoring formatting commits
git config blame.ignoreRevsFile .git-blame-ignore-revs
```
