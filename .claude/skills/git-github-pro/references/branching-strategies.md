# Branching Strategies & Patterns

## Git Flow Strategy (Complex Projects)

Ideal for projects with scheduled releases and multiple versions in production.

**Main branches:**
- `main` - Production-ready code (stable releases)
- `develop` - Integration branch for features (next release)

**Supporting branches:**
- `feature/*` - Feature development (branch from `develop`, merge back to `develop`)
- `release/*` - Release preparation (branch from `develop`, merge to `main` and `develop`)
- `hotfix/*` - Production bug fixes (branch from `main`, merge to `main` and `develop`)

**Workflow:**
```bash
# Start feature
git checkout develop
git pull origin develop
git checkout -b feature/new-component

# Finish feature
git checkout develop
git pull origin develop
git merge --no-ff feature/new-component
git push origin develop
git push origin --delete feature/new-component

# Create release
git checkout -b release/1.2.0 develop
# Update version numbers
git commit -am "Bump version to 1.2.0"
git checkout main
git merge --no-ff release/1.2.0
git tag -a v1.2.0
git checkout develop
git merge --no-ff release/1.2.0
git push origin main develop --tags
```

## GitHub Flow (Simple, Continuous Deployment)

Best for continuous deployment and rapid iteration.

**Single main branch:** `main` is always production-ready

**Process:**
1. Create descriptive feature branch: `feature/add-dark-mode`
2. Make changes and commit regularly
3. Open pull request for review
4. Deploy from PR preview if available
5. Merge after approval and status checks pass
6. Auto-deploy from main

```bash
git checkout main
git pull origin main
git checkout -b feature/add-dark-mode
# ... make changes ...
git push origin feature/add-dark-mode
# Create PR via GitHub UI
# After approval and CI passes:
git checkout main
git pull origin main
git merge --squash feature/add-dark-mode
git push origin main
```

## Trunk-Based Development (Highly Skilled Teams)

Continuous deployment with minimal branching.

**Single branch:** `main` is always deployable

**Key practices:**
- Short-lived branches (<1 day)
- Frequent commits to main
- Feature flags for incomplete work
- Robust CI/CD pipeline
- High test coverage

```bash
git checkout main
git pull origin main
git checkout -b feature/payment-gateway
# ... small, focused changes ...
git commit -m "feat: add stripe integration (feature-flagged)"
git push origin feature/payment-gateway
# Quick PR review and merge
# Deploy immediately after merge
```

## Release Branch Strategy

For managing multiple versions simultaneously.

**Structure:**
- `main` - Latest stable release
- `release/1.x` - Maintenance for version 1.x
- `release/2.x` - Maintenance for version 2.x
- `develop` - Next major version development

**Use when:**
- Supporting multiple versions
- Long-term maintenance required
- Staggered deployments

```bash
# Create maintenance branch from release tag
git checkout -b release/2.0 v2.0.0

# Backport bug fixes
git checkout release/2.0
git cherry-pick <commit-hash>
git push origin release/2.0

# Tag patch release
git tag -a v2.0.1
git push origin v2.0.1
```

## Forking Workflow (Open Source)

Contributors fork repo, make changes, submit PRs.

```bash
# In forked repository
git clone https://github.com/yourname/project.git
git remote add upstream https://github.com/original/project.git

# Keep fork updated
git fetch upstream
git rebase upstream/main

# Create feature branch
git checkout -b feature/new-feature

# Push to your fork
git push origin feature/new-feature

# Create PR from your fork to upstream
# After merge, cleanup:
git checkout main
git pull upstream main
git push origin main
git branch -d feature/new-feature
git push origin --delete feature/new-feature
```

## Branch Naming Conventions

Follow consistent naming to improve clarity and automation:

```
feature/<description>     # New features
fix/<description>         # Bug fixes
hotfix/<description>      # Production bugs
release/<version>         # Release preparation
chore/<description>       # Maintenance, dependency updates
docs/<description>        # Documentation changes
test/<description>        # Test-specific changes
refactor/<description>    # Code refactoring
perf/<description>        # Performance improvements
```

Good examples:
- `feature/user-authentication`
- `fix/profile-image-upload-bug`
- `hotfix/payment-timeout-issue`
- `chore/update-eslint-config`

Avoid:
- Single-word branches like `auth`, `fix`, `update`
- Ambiguous names like `wip`, `temporary`, `test`
- Branches with slashes in feature names

## Protecting Important Branches

Prevent accidental pushes to production:

```bash
# Set protected branch rules in GitHub:
# Settings → Branches → Branch protection rules

# For main/master branch, configure:
# ✓ Require pull request reviews (2+ reviewers)
# ✓ Require status checks to pass
# ✓ Require branches to be up to date before merging
# ✓ Dismiss stale pull request approvals
# ✓ Require conversation resolution before merging
# ✓ Restrict who can push to matching branches
```

## Cleanup & Maintenance

Regular branch management keeps repo healthy:

```bash
# List merged branches
git branch --merged main

# Delete local merged branches
git branch -d feature/completed-feature

# Delete remote merged branches (GitHub will do this automatically for PRs)
git push origin --delete feature/completed-feature

# Clean up stale branches (prune)
git fetch origin --prune

# List all branches not merged to main (potential work in progress)
git branch --no-merged main
```

## Common Patterns by Project Type

**Web Application (High Velocity):**
Use GitHub Flow + feature flags for continuous deployment

**Library/Package (Release-Based):**
Use Git Flow with semantic versioning and tagged releases

**Microservices:**
Trunk-based development with feature flags and robust CI/CD

**Open Source:**
Forking workflow with GitHub Flow for maintainers

**Mobile App:**
Git Flow or Release-based, with longer release cycles
