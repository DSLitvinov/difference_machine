#!/usr/bin/env python3
"""
Forester CLI entry point.
Provides command-line interface for Forester version control system.
"""

import sys
import argparse
from pathlib import Path
from .commands.init import init_repository, is_repository, find_repository
from .commands.commit import create_commit, has_uncommitted_changes
from .commands.branch import (
    create_branch,
    list_branches,
    delete_branch,
    get_branch_commits,
    switch_branch,
)
from .commands.checkout import checkout, checkout_branch, checkout_commit
from .commands.stash import create_stash, list_stashes, apply_stash, delete_stash
from .commands.tag import create_tag, delete_tag, list_tags, show_tag


def cmd_init(args):
    """Handle init command."""
    repo_path = Path(args.path) if args.path else Path.cwd()

    try:
        init_repository(repo_path, force=args.force)
        print(f"Initialized Forester repository in {repo_path / '.DFM'}")
        return 0
    except FileExistsError:
        print(f"Error: Repository already exists at {repo_path / '.DFM'}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_commit(args):
    """Handle commit command."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        commit_hash = create_commit(
            repo_path,
            message=args.message or "No message",
            author=args.author or "Unknown",
            skip_hooks=getattr(args, 'no_verify', False)
        )

        if commit_hash:
            print(f"Created commit: {commit_hash[:16]}...")
            return 0
        else:
            print("No changes to commit")
            return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_branch(args):
    """Handle branch commands."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        if args.action == "create":
            create_branch(repo_path, args.name, from_branch=args.from_branch)
            print(f"Created branch: {args.name}")
            return 0

        elif args.action == "list":
            branches = list_branches(repo_path)
            if not branches:
                print("No branches found")
                return 0

            current_branch = None
            for branch in branches:
                if branch['current']:
                    current_branch = branch['name']
                    break

            for branch in branches:
                marker = "* " if branch['current'] else "  "
                name = branch['name']
                commit_info = ""

                if branch['commit_hash']:
                    commit_info = f" -> {branch['commit_hash'][:8]}"
                    if branch['commit']:
                        commit_info += f" ({branch['commit']['message'][:50]})"

                print(f"{marker}{name}{commit_info}")

            return 0

        elif args.action == "delete":
            delete_branch(repo_path, args.name, force=args.force)
            print(f"Deleted branch: {args.name}")
            return 0

        elif args.action == "switch":
            switch_branch(repo_path, args.name)
            print(f"Switched to branch: {args.name}")
            return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_checkout(args):
    """Handle checkout command."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        success, error = checkout(repo_path, args.target, force=args.force, skip_hooks=getattr(args, 'no_verify', False))

        if success:
            print(f"Checked out: {args.target}")
            return 0
        else:
            if error == "uncommitted_changes":
                print("Error: You have uncommitted changes.")
                print("Use --force to discard them, or commit/stash them first.")
            else:
                print(f"Error: {error}")
            return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_stash(args):
    """Handle stash commands."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        if args.action == "create":
            stash_hash = create_stash(repo_path, message=args.message)
            if stash_hash:
                print(f"Created stash: {stash_hash[:16]}...")
                return 0
            else:
                print("No changes to stash")
                return 0

        elif args.action == "list":
            stashes = list_stashes(repo_path)
            if not stashes:
                print("No stashes found")
                return 0

            import datetime
            for stash in stashes:
                timestamp = datetime.datetime.fromtimestamp(stash['timestamp'])
                print(f"stash@{stash['hash'][:8]}  {timestamp.strftime('%Y-%m-%d %H:%M:%S')}  {stash['message']}")
                if stash['branch']:
                    print(f"  Branch: {stash['branch']}")

            return 0

        elif args.action == "apply":
            success, error = apply_stash(repo_path, args.hash, force=args.force)
            if success:
                print(f"Applied stash: {args.hash[:16]}...")
                return 0
            else:
                if error == "uncommitted_changes":
                    print("Error: You have uncommitted changes.")
                    print("Use --force to discard them.")
                else:
                    print(f"Error: {error}")
                return 1

        elif args.action == "delete":
            delete_stash(repo_path, args.hash)
            print(f"Deleted stash: {args.hash[:16]}...")
            return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_status(args):
    """Handle status command."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        from .core.refs import get_current_branch, get_current_head_commit

        # Get current branch
        branch = get_current_branch(repo_path)
        head_commit = get_current_head_commit(repo_path)

        print(f"On branch: {branch or 'detached HEAD'}")
        if head_commit:
            print(f"HEAD: {head_commit[:16]}...")
        else:
            print("HEAD: (no commits yet)")

        # Check for uncommitted changes
        if has_uncommitted_changes(repo_path):
            print("\nYou have uncommitted changes.")
        else:
            print("\nWorking directory clean.")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_rebuild(args):
    """Handle rebuild command."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        from .commands.rebuild_database import rebuild_database

        print("Rebuilding database from storage...")
        success, error = rebuild_database(repo_path, backup=not args.no_backup)

        if success:
            print("Database rebuilt successfully")
            return 0
        else:
            print(f"Error: {error}")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def _compare_trees(parent_tree, current_tree):
    """
    Compare two trees and return changed files.

    Args:
        parent_tree: Tree from parent commit
        current_tree: Tree from current commit

    Returns:
        Dict with 'added', 'modified', 'deleted' lists of TreeEntry objects
    """
    from .models.tree import TreeEntry

    # Build dictionaries by path for easy lookup
    parent_entries = {entry.path: entry for entry in parent_tree.entries}
    current_entries = {entry.path: entry for entry in current_tree.entries}

    added = []
    modified = []
    deleted = []

    # Find added and modified files
    for path, entry in current_entries.items():
        if path not in parent_entries:
            # File was added
            added.append(entry)
        elif entry.hash != parent_entries[path].hash:
            # File was modified (hash changed)
            modified.append(entry)

    # Find deleted files
    for path, entry in parent_entries.items():
        if path not in current_entries:
            deleted.append(entry)

    return {
        'added': added,
        'modified': modified,
        'deleted': deleted
    }


def cmd_show(args):
    """Handle show command - display commit details and files."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        from .core.database import ForesterDB
        from .core.storage import ObjectStorage
        from .models.commit import Commit

        dfm_dir = repo_path / ".DFM"
        db_path = dfm_dir / "forester.db"

        with ForesterDB(db_path) as db:
            storage = ObjectStorage(dfm_dir)

            # Load commit
            commit = Commit.from_storage(args.commit_hash, db, storage)
            if not commit:
                print(f"Error: Commit {args.commit_hash} not found")
                return 1

            # Print commit info
            import datetime
            date_str = datetime.datetime.fromtimestamp(commit.timestamp).strftime('%Y-%m-%d %H:%M:%S')

            print(f"Commit: {commit.hash}")
            print(f"Author: {commit.author}")
            print(f"Date: {date_str}")
            print(f"Message: {commit.message}")
            print(f"Type: {commit.commit_type}")
            # Get tag from database
            commit_data = db.get_commit(commit.hash)
            if commit_data and commit_data.get('tag'):
                print(f"Tag: {commit_data['tag']}")
            if commit.parent_hash:
                print(f"Parent: {commit.parent_hash[:16]}...")

            # Get tree and show files
            if commit.commit_type == "project" and commit.tree_hash:
                tree = commit.get_tree(db, storage)
                if tree:
                    if args.full:
                        # Show all files
                        print(f"\nFiles ({len(tree.entries)}):")
                        for entry in sorted(tree.entries, key=lambda e: e.path):
                            size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                            print(f"  {entry.path}{size_str}")
                    else:
                        # Show only changed files (compare with parent)
                        if commit.parent_hash:
                            parent_commit = Commit.from_storage(commit.parent_hash, db, storage)
                            if parent_commit and parent_commit.tree_hash:
                                parent_tree = parent_commit.get_tree(db, storage)
                                if parent_tree:
                                    # Compare trees
                                    changed_files = _compare_trees(parent_tree, tree)
                                    if changed_files['added'] or changed_files['modified'] or changed_files['deleted']:
                                        total_changed = (len(changed_files['added']) +
                                                        len(changed_files['modified']) +
                                                        len(changed_files['deleted']))
                                        print(f"\nChanged files ({total_changed}):")

                                        # Show deleted files
                                        for entry in sorted(changed_files['deleted'], key=lambda e: e.path):
                                            print(f"  - {entry.path} (deleted)")

                                        # Show modified files
                                        for entry in sorted(changed_files['modified'], key=lambda e: e.path):
                                            size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                                            print(f"  M {entry.path}{size_str}")

                                        # Show added files
                                        for entry in sorted(changed_files['added'], key=lambda e: e.path):
                                            size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                                            print(f"  + {entry.path}{size_str}")
                                    else:
                                        print("\nNo file changes (only metadata changed)")
                                else:
                                    # Parent tree not found, show all files
                                    print(f"\nFiles ({len(tree.entries)}):")
                                    for entry in sorted(tree.entries, key=lambda e: e.path):
                                        size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                                        print(f"  {entry.path}{size_str}")
                            else:
                                # No parent commit or parent has no tree, show all files
                                print(f"\nFiles ({len(tree.entries)}):")
                                for entry in sorted(tree.entries, key=lambda e: e.path):
                                    size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                                    print(f"  {entry.path}{size_str}")
                        else:
                            # No parent commit (first commit), show all files
                            print(f"\nFiles ({len(tree.entries)}):")
                            for entry in sorted(tree.entries, key=lambda e: e.path):
                                size_str = f" ({entry.size:,} bytes)" if entry.size else ""
                                print(f"  {entry.path}{size_str}")
                else:
                    print("\nTree not found")

            # Show meshes if mesh_only commit
            if commit.commit_type == "mesh_only":
                if commit.selected_mesh_names:
                    print(f"\nMeshes ({len(commit.selected_mesh_names)}):")
                    for mesh_name in commit.selected_mesh_names:
                        print(f"  {mesh_name}")
                if commit.mesh_hashes:
                    print(f"\nMesh hashes ({len(commit.mesh_hashes)}):")
                    for mesh_hash in commit.mesh_hashes:
                        print(f"  {mesh_hash[:16]}...")

            return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_log(args):
    """Handle log command - show commit history."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        from .core.refs import get_current_branch
        from .commands.branch import get_branch_commits

        branch_name = args.branch if args.branch else get_current_branch(repo_path)
        if not branch_name:
            print("Error: No branch specified and no current branch")
            return 1

        commits = get_branch_commits(repo_path, branch_name)
        if not commits:
            print(f"No commits in branch '{branch_name}'")
            return 0

        import datetime
        for commit in reversed(commits):  # Show newest first
            date_str = datetime.datetime.fromtimestamp(commit['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            hash_short = commit['hash'][:16]
            message = commit.get('message', 'No message')
            author = commit.get('author', 'Unknown')
            commit_type = commit.get('commit_type', 'project')
            tag = commit.get('tag')

            type_icon = "📦" if commit_type == "mesh_only" else "📁"
            tag_str = f" [{tag}]" if tag else ""
            print(f"{hash_short} {type_icon} {author} | {date_str}{tag_str}")
            print(f"    {message}")
            if args.verbose:
                if commit.get('parent_hash'):
                    print(f"    Parent: {commit['parent_hash'][:16]}...")
                if commit_type == "mesh_only" and commit.get('selected_mesh_names'):
                    mesh_names = commit['selected_mesh_names']
                    if isinstance(mesh_names, str):
                        import json
                        try:
                            mesh_names = json.loads(mesh_names)
                        except:
                            mesh_names = [mesh_names]
                    if mesh_names:
                        print(f"    Meshes: {', '.join(mesh_names)}")
            print()

        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_tag(args):
    """Handle tag commands."""
    repo_path = find_repository(Path.cwd())
    if not repo_path:
        print("Error: Not a Forester repository")
        return 1

    try:
        if args.action == "create":
            create_tag(repo_path, args.name, commit_hash=args.commit)
            print(f"Created tag: {args.name}")
            return 0

        elif args.action == "list":
            tags = list_tags(repo_path)
            if not tags:
                print("No tags found")
                return 0

            import datetime
            for tag_info in tags:
                date_str = datetime.datetime.fromtimestamp(tag_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                commit_hash = tag_info['commit_hash'][:16]
                message = tag_info.get('message', 'No message')
                author = tag_info.get('author', 'Unknown')
                print(f"{tag_info['tag']:20} -> {commit_hash}  {author} | {date_str}")
                print(f"  {message}")

            return 0

        elif args.action == "delete":
            delete_tag(repo_path, args.name)
            print(f"Deleted tag: {args.name}")
            return 0

        elif args.action == "show":
            tag_info = show_tag(repo_path, args.name)
            if not tag_info:
                print(f"Error: Tag '{args.name}' not found")
                return 1

            import datetime
            date_str = datetime.datetime.fromtimestamp(tag_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

            print(f"Tag: {tag_info['tag']}")
            print(f"Commit: {tag_info['commit_hash']}")
            print(f"Author: {tag_info['author']}")
            print(f"Date: {date_str}")
            print(f"Message: {tag_info['message']}")
            print(f"Branch: {tag_info['branch']}")
            print(f"Type: {tag_info['commit_type']}")

            return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="forester",
        description="Forester - Git-like version control for 3D models"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new repository")
    init_parser.add_argument("path", nargs="?", help="Path to initialize (default: current directory)")
    init_parser.add_argument("--force", action="store_true", help="Reinitialize even if repository exists")

    # Commit command
    commit_parser = subparsers.add_parser("commit", help="Create a new commit")
    commit_parser.add_argument("-m", "--message", help="Commit message")
    commit_parser.add_argument("-a", "--author", help="Author name")
    commit_parser.add_argument("--no-verify", action="store_true", help="Skip pre-commit and post-commit hooks")

    # Branch command
    branch_parser = subparsers.add_parser("branch", help="Manage branches")
    branch_subparsers = branch_parser.add_subparsers(dest="action", help="Branch action")

    branch_create = branch_subparsers.add_parser("create", help="Create a new branch")
    branch_create.add_argument("name", help="Branch name")
    branch_create.add_argument("--from", dest="from_branch", help="Branch to copy from")

    branch_subparsers.add_parser("list", help="List all branches")

    branch_delete = branch_subparsers.add_parser("delete", help="Delete a branch")
    branch_delete.add_argument("name", help="Branch name")
    branch_delete.add_argument("--force", action="store_true", help="Force deletion")

    branch_switch = branch_subparsers.add_parser("switch", help="Switch to a branch")
    branch_switch.add_argument("name", help="Branch name")

    # Checkout command
    checkout_parser = subparsers.add_parser("checkout", help="Checkout a branch or commit")
    checkout_parser.add_argument("target", help="Branch name or commit hash")
    checkout_parser.add_argument("--force", action="store_true", help="Discard uncommitted changes")
    checkout_parser.add_argument("--no-verify", action="store_true", help="Skip pre-checkout and post-checkout hooks")

    # Stash command
    stash_parser = subparsers.add_parser("stash", help="Manage stashes")
    stash_subparsers = stash_parser.add_subparsers(dest="action", help="Stash action")

    stash_create = stash_subparsers.add_parser("create", help="Create a stash")
    stash_create.add_argument("-m", "--message", help="Stash message")

    stash_subparsers.add_parser("list", help="List all stashes")

    stash_apply = stash_subparsers.add_parser("apply", help="Apply a stash")
    stash_apply.add_argument("hash", help="Stash hash")
    stash_apply.add_argument("--force", action="store_true", help="Discard uncommitted changes")

    stash_delete = stash_subparsers.add_parser("delete", help="Delete a stash")
    stash_delete.add_argument("hash", help="Stash hash")

    # Status command
    subparsers.add_parser("status", help="Show repository status")

    # Rebuild command
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild database from storage")
    rebuild_parser.add_argument("--no-backup", action="store_true",
                               help="Don't create backup of existing database")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show commit details and files")
    show_parser.add_argument("commit_hash", help="Commit hash to show")
    show_parser.add_argument("--full", action="store_true",
                           help="Show all files in commit (default: show only changed files)")

    # Log command
    log_parser = subparsers.add_parser("log", help="Show commit history")
    log_parser.add_argument("branch", nargs="?", help="Branch name (default: current branch)")
    log_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")

    # Tag command
    tag_parser = subparsers.add_parser("tag", help="Manage tags")
    tag_subparsers = tag_parser.add_subparsers(dest="action", help="Tag action")

    tag_create = tag_subparsers.add_parser("create", help="Create a tag")
    tag_create.add_argument("name", help="Tag name")
    tag_create.add_argument("commit", nargs="?", help="Commit hash (default: current HEAD)")

    tag_subparsers.add_parser("list", help="List all tags")

    tag_delete = tag_subparsers.add_parser("delete", help="Delete a tag")
    tag_delete.add_argument("name", help="Tag name")

    tag_show = tag_subparsers.add_parser("show", help="Show tag information")
    tag_show.add_argument("name", help="Tag name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command handler
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "commit":
        return cmd_commit(args)
    elif args.command == "branch":
        return cmd_branch(args)
    elif args.command == "checkout":
        return cmd_checkout(args)
    elif args.command == "stash":
        return cmd_stash(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "rebuild":
        return cmd_rebuild(args)
    elif args.command == "show":
        return cmd_show(args)
    elif args.command == "log":
        return cmd_log(args)
    elif args.command == "tag":
        return cmd_tag(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())



