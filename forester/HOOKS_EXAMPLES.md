# Forester Hooks Examples

This document provides examples of hook scripts for Forester version control system.

## Hook Locations

Hooks are stored in `.DFM/hooks/` directory:
- `pre-commit` - Runs before commit creation
- `post-commit` - Runs after commit creation
- `pre-checkout` - Runs before checkout
- `post-checkout` - Runs after checkout

## Environment Variables

Hooks receive environment variables with information about the operation:

### Pre-commit / Post-commit hooks:
- `DFM_BRANCH` - Current branch name
- `DFM_AUTHOR` - Commit author
- `DFM_MESSAGE` - Commit message
- `DFM_REPO_PATH` - Repository root path
- `DFM_COMMIT_HASH` - Commit hash (post-commit only)

### Pre-checkout / Post-checkout hooks:
- `DFM_TARGET` - Branch name or commit hash being checked out
- `DFM_REPO_PATH` - Repository root path

## Example Hooks

### Pre-commit Hook: Validate Commit Message

**File:** `.DFM/hooks/pre-commit`

```bash
#!/bin/bash
# Validate commit message length and format

MIN_LENGTH=10
MAX_LENGTH=200

if [ ${#DFM_MESSAGE} -lt $MIN_LENGTH ]; then
    echo "Error: Commit message too short (minimum $MIN_LENGTH characters)"
    exit 1
fi

if [ ${#DFM_MESSAGE} -gt $MAX_LENGTH ]; then
    echo "Error: Commit message too long (maximum $MAX_LENGTH characters)"
    exit 1
fi

# Check for required prefix (optional)
if [[ ! "$DFM_MESSAGE" =~ ^(feat|fix|docs|style|refactor|test|chore): ]]; then
    echo "Warning: Commit message should start with prefix (feat, fix, docs, etc.)"
    # Don't fail, just warn
fi

exit 0
```

### Pre-commit Hook: Check File Sizes

**File:** `.DFM/hooks/pre-commit`

```bash
#!/bin/bash
# Check for large files before committing

MAX_SIZE=104857600  # 100MB in bytes

# Check files in working directory
WORKING_DIR="$DFM_REPO_PATH/working"
if [ ! -d "$WORKING_DIR" ]; then
    WORKING_DIR="$DFM_REPO_PATH"
fi

find "$WORKING_DIR" -type f ! -path "*/.DFM/*" | while read file; do
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    if [ "$size" -gt "$MAX_SIZE" ]; then
        echo "Error: File $file is too large ($size bytes > $MAX_SIZE bytes)"
        exit 1
    fi
done

exit 0
```

### Post-commit Hook: Send Notification

**File:** `.DFM/hooks/post-commit`

```bash
#!/bin/bash
# Send notification after commit

COMMIT_SHORT="${DFM_COMMIT_HASH:0:16}"
MESSAGE="New commit by $DFM_AUTHOR on branch $DFM_BRANCH: $DFM_MESSAGE ($COMMIT_SHORT)"

# Example: Send to Slack webhook
# curl -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
#   -H 'Content-Type: application/json' \
#   -d "{\"text\": \"$MESSAGE\"}"

# Example: Log to file
LOG_FILE="$DFM_REPO_PATH/.DFM/commit_log.txt"
echo "$(date): $MESSAGE" >> "$LOG_FILE"

exit 0
```

### Post-commit Hook: Auto-tag Releases

**File:** `.DFM/hooks/post-commit`

```bash
#!/bin/bash
# Auto-tag commits with "release:" prefix

if [[ "$DFM_MESSAGE" =~ ^release: ]]; then
    # Extract version from message (e.g., "release: v1.2.3")
    VERSION=$(echo "$DFM_MESSAGE" | sed -n 's/^release: *v\?\(.*\)/\1/p')
    
    if [ -n "$VERSION" ]; then
        TAG_NAME="v$VERSION"
        # Create tag using forester CLI
        cd "$DFM_REPO_PATH"
        python3 -m forester tag create "$TAG_NAME" "$DFM_COMMIT_HASH" 2>/dev/null || true
    fi
fi

exit 0
```

### Pre-checkout Hook: Backup Current State

**File:** `.DFM/hooks/pre-checkout`

```bash
#!/bin/bash
# Create backup before checkout

BACKUP_DIR="$DFM_REPO_PATH/.DFM/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/pre_checkout_${TIMESTAMP}.tar.gz"

# Backup working directory (excluding .DFM)
cd "$DFM_REPO_PATH"
tar -czf "$BACKUP_FILE" --exclude=".DFM" working/ 2>/dev/null || true

echo "Backup created: $BACKUP_FILE"
exit 0
```

### Post-checkout Hook: Update External Dependencies

**File:** `.DFM/hooks/post-checkout`

```bash
#!/bin/bash
# Update external dependencies after checkout

# Example: Reload textures in external tool
# This is just an example - adapt to your workflow

WORKING_DIR="$DFM_REPO_PATH/working"
if [ -d "$WORKING_DIR/textures" ]; then
    echo "Textures directory updated, may need to reload in external tool"
fi

exit 0
```

## Python Hook Example

Hooks can also be Python scripts:

**File:** `.DFM/hooks/pre-commit`

```python
#!/usr/bin/env python3
import os
import sys

# Get environment variables
message = os.environ.get('DFM_MESSAGE', '')
author = os.environ.get('DFM_AUTHOR', '')
branch = os.environ.get('DFM_BRANCH', '')

# Validate commit message
if len(message) < 10:
    print("Error: Commit message too short")
    sys.exit(1)

# Check for forbidden words
forbidden = ['WIP', 'TODO', 'FIXME']
if any(word in message.upper() for word in forbidden):
    print("Warning: Commit message contains forbidden words")
    # Don't fail, just warn
    sys.exit(0)

sys.exit(0)
```

## Making Hooks Executable

After creating a hook script, make it executable:

```bash
chmod +x .DFM/hooks/pre-commit
chmod +x .DFM/hooks/post-commit
```

Forester will automatically make hooks executable when running them, but it's good practice to set permissions manually.

## Skipping Hooks

To skip hooks during commit or checkout:

```bash
# Skip hooks when committing
forester commit -m "Message" --no-verify

# Skip hooks when checking out
forester checkout main --no-verify
```

## Hook Execution

- **Pre-commit hooks**: Must return exit code 0 to allow commit. Non-zero exit code blocks commit.
- **Post-commit hooks**: Can fail without blocking (non-zero exit code is logged but doesn't affect commit).
- **Pre-checkout hooks**: Must return exit code 0 to allow checkout. Non-zero exit code blocks checkout.
- **Post-checkout hooks**: Can fail without blocking (non-zero exit code is logged but doesn't affect checkout).

## Timeout

Hooks have a default timeout of 30 seconds. If a hook takes longer, it will be terminated and the operation will fail (for pre-commit/pre-checkout) or continue (for post-commit/post-checkout).



