"""
Hooks system for Forester.
Supports pre-commit and post-commit hooks similar to Git.
"""

import logging
import subprocess
import os
import stat
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def get_hooks_dir(repo_path: Path) -> Path:
    """
    Get hooks directory path.

    Args:
        repo_path: Repository root path

    Returns:
        Path to hooks directory
    """
    return repo_path / ".DFM" / "hooks"


def ensure_hooks_dir(repo_path: Path) -> Path:
    """
    Ensure hooks directory exists.

    Args:
        repo_path: Repository root path

    Returns:
        Path to hooks directory
    """
    hooks_dir = get_hooks_dir(repo_path)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir


def hook_exists(repo_path: Path, hook_name: str) -> bool:
    """
    Check if hook script exists.

    Args:
        repo_path: Repository root path
        hook_name: Hook name (e.g., 'pre-commit', 'post-commit')

    Returns:
        True if hook exists and is executable
    """
    hooks_dir = get_hooks_dir(repo_path)
    hook_path = hooks_dir / hook_name

    if not hook_path.exists():
        return False

    if not hook_path.is_file():
        return False

    # Check if file is executable
    file_stat = hook_path.stat()
    is_executable = bool(file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

    return is_executable


def run_hook(
    repo_path: Path,
    hook_name: str,
    env_vars: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    can_fail: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Run a hook script.

    Args:
        repo_path: Repository root path
        hook_name: Hook name (e.g., 'pre-commit', 'post-commit')
        env_vars: Additional environment variables to pass to hook
        timeout: Maximum execution time in seconds
        can_fail: If True, hook failure won't raise exception (for post-commit)

    Returns:
        Tuple of (success: bool, error_message: Optional[str])

    Raises:
        ValueError: If hook fails and can_fail=False
    """
    hooks_dir = get_hooks_dir(repo_path)
    hook_path = hooks_dir / hook_name

    if not hook_path.exists():
        return (True, None)  # Hook doesn't exist, skip silently

    if not hook_path.is_file():
        logger.warning(f"Hook '{hook_name}' exists but is not a file, skipping")
        return (True, None)

    # Prepare environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Make sure hook is executable
    try:
        current_mode = hook_path.stat().st_mode
        hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError as e:
        logger.warning(f"Failed to make hook '{hook_name}' executable: {e}")

    # Run hook
    try:
        logger.debug(f"Running hook: {hook_name}")
        result = subprocess.run(
            [str(hook_path)],
            cwd=str(repo_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Hook '{hook_name}' failed with exit code {result.returncode}"
            logger.warning(f"Hook '{hook_name}' failed: {error_msg}")
            
            if not can_fail:
                return (False, error_msg)
            else:
                # Post-commit hooks can fail without blocking
                return (True, None)

        if result.stdout:
            logger.debug(f"Hook '{hook_name}' output: {result.stdout.strip()}")

        return (True, None)

    except subprocess.TimeoutExpired:
        error_msg = f"Hook '{hook_name}' timed out after {timeout} seconds"
        logger.error(error_msg)
        if not can_fail:
            return (False, error_msg)
        return (True, None)

    except Exception as e:
        error_msg = f"Hook '{hook_name}' error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if not can_fail:
            return (False, error_msg)
        return (True, None)


def run_pre_commit_hook(
    repo_path: Path,
    branch: str,
    author: str,
    message: str,
    skip_hooks: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Run pre-commit hook.

    Args:
        repo_path: Repository root path
        branch: Branch name
        author: Author name
        message: Commit message
        skip_hooks: If True, skip hook execution

    Returns:
        Tuple of (success: bool, error_message: Optional[str])

    Raises:
        ValueError: If hook fails
    """
    if skip_hooks:
        return (True, None)

    env_vars = {
        'DFM_BRANCH': branch,
        'DFM_AUTHOR': author,
        'DFM_MESSAGE': message,
        'DFM_REPO_PATH': str(repo_path),
    }

    success, error = run_hook(
        repo_path,
        'pre-commit',
        env_vars=env_vars,
        timeout=30,
        can_fail=False  # Pre-commit hooks can block commit
    )

    if not success:
        raise ValueError(error or "Pre-commit hook failed")

    return (True, None)


def run_post_commit_hook(
    repo_path: Path,
    commit_hash: str,
    branch: str,
    author: str,
    message: str,
    skip_hooks: bool = False
) -> None:
    """
    Run post-commit hook.

    Args:
        repo_path: Repository root path
        commit_hash: Commit hash
        branch: Branch name
        author: Author name
        message: Commit message
        skip_hooks: If True, skip hook execution
    """
    if skip_hooks:
        return

    env_vars = {
        'DFM_COMMIT_HASH': commit_hash,
        'DFM_BRANCH': branch,
        'DFM_AUTHOR': author,
        'DFM_MESSAGE': message,
        'DFM_REPO_PATH': str(repo_path),
    }

    # Post-commit hooks can fail without blocking
    success, error = run_hook(
        repo_path,
        'post-commit',
        env_vars=env_vars,
        timeout=30,
        can_fail=True  # Post-commit hooks don't block
    )

    if not success and error:
        logger.warning(f"Post-commit hook failed (non-blocking): {error}")


def run_pre_checkout_hook(
    repo_path: Path,
    target: str,
    skip_hooks: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Run pre-checkout hook.

    Args:
        repo_path: Repository root path
        target: Branch name or commit hash
        skip_hooks: If True, skip hook execution

    Returns:
        Tuple of (success: bool, error_message: Optional[str])

    Raises:
        ValueError: If hook fails
    """
    if skip_hooks:
        return (True, None)

    env_vars = {
        'DFM_TARGET': target,
        'DFM_REPO_PATH': str(repo_path),
    }

    success, error = run_hook(
        repo_path,
        'pre-checkout',
        env_vars=env_vars,
        timeout=30,
        can_fail=False  # Pre-checkout hooks can block checkout
    )

    if not success:
        raise ValueError(error or "Pre-checkout hook failed")

    return (True, None)


def run_post_checkout_hook(
    repo_path: Path,
    target: str,
    skip_hooks: bool = False
) -> None:
    """
    Run post-checkout hook.

    Args:
        repo_path: Repository root path
        target: Branch name or commit hash
        skip_hooks: If True, skip hook execution
    """
    if skip_hooks:
        return

    env_vars = {
        'DFM_TARGET': target,
        'DFM_REPO_PATH': str(repo_path),
    }

    # Post-checkout hooks can fail without blocking
    success, error = run_hook(
        repo_path,
        'post-checkout',
        env_vars=env_vars,
        timeout=30,
        can_fail=True  # Post-checkout hooks don't block
    )

    if not success and error:
        logger.warning(f"Post-checkout hook failed (non-blocking): {error}")

