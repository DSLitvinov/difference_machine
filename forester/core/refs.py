"""
Reference management for Forester.
Handles branch references.
"""

from pathlib import Path
from typing import Optional


def get_branch_ref(repo_path: Path, branch: str) -> Optional[str]:
    """
    Get commit hash for a branch.

    Args:
        repo_path: Path to repository root
        branch: Branch name

    Returns:
        Commit hash or None if branch doesn't exist or has no commits
    """
    ref_file = repo_path / ".DFM" / "refs" / "branches" / branch

    if not ref_file.exists():
        return None

    with open(ref_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    return content if content else None


def set_branch_ref(repo_path: Path, branch: str, commit_hash: Optional[str]) -> None:
    """
    Set commit hash for a branch.

    Args:
        repo_path: Path to repository root
        branch: Branch name
        commit_hash: Commit hash (None to clear)
    """
    ref_file = repo_path / ".DFM" / "refs" / "branches" / branch

    # Ensure directory exists
    ref_file.parent.mkdir(parents=True, exist_ok=True)

    with open(ref_file, 'w', encoding='utf-8') as f:
        if commit_hash:
            f.write(commit_hash)
        else:
            f.write("")  # Empty file means no commit


def get_current_branch(repo_path: Path) -> Optional[str]:
    """
    Get current branch name from database.

    ВАЖНО: Всегда открывает новое соединение для гарантии чтения актуальных данных.
    Это предотвращает проблемы с кешированием и транзакциями.

    Args:
        repo_path: Path to repository root

    Returns:
        Branch name or None
    """
    dfm_dir = repo_path / ".DFM"
    if not dfm_dir.exists():
        return None

    db_path = dfm_dir / "forester.db"
    if not db_path.exists():
        return None

    from .database import ForesterDB

    try:
        # ВАЖНО: Используем новое соединение каждый раз для гарантии актуальных данных
        # Context manager гарантирует закрытие соединения после использования
        with ForesterDB(db_path) as db:
            # Принудительно читаем из БД без кеширования
            branch = db.get_current_branch()
            return branch
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting current branch: {e}", exc_info=True)
        return None


def get_current_head_commit(repo_path: Path) -> Optional[str]:
    """
    Get current HEAD commit hash.

    Args:
        repo_path: Path to repository root

    Returns:
        Commit hash or None
    """
    branch = get_current_branch(repo_path)
    if not branch:
        return None

    # First try to get from branch ref
    commit_hash = get_branch_ref(repo_path, branch)
    if commit_hash:
        return commit_hash

    # Fallback to database head if branch ref is empty
    dfm_dir = repo_path / ".DFM"
    db_path = dfm_dir / "forester.db"
    if db_path.exists():
        try:
            from .database import ForesterDB
            with ForesterDB(db_path) as db:
                return db.get_head()
        except Exception:
            pass

    return None




