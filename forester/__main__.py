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
            author=args.author or "Unknown"
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
        success, error = checkout(repo_path, args.target, force=args.force)
        
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
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())



