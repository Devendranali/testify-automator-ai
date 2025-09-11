import os
import shutil
import asyncio
import logging
from typing import List, Dict, Any

from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class GitService:
    def __init__(self, base_dir: str = "temp_repos"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_repo_path(self, repo_url: str) -> str:
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        return os.path.join(self.base_dir, repo_name)

    def _ensure_clean_repo_path(self, repo_path: str) -> None:
        """If path exists but is not a git repo, wipe it."""
        if os.path.exists(repo_path):
            if not os.path.isdir(os.path.join(repo_path, ".git")):
                shutil.rmtree(repo_path, ignore_errors=True)
                logger.info(f"Removed non-git folder at {repo_path}")

    def _configure_user(self, repo: Repo) -> None:
        """Guarantee user.name and user.email for the commit, overriding if necessary."""
        name = os.getenv("GIT_AUTHOR_NAME", "Testify Automator")
        email = os.getenv("GIT_AUTHOR_EMAIL", "automator@testify.com")
        with repo.config_writer() as cw:
            cw.set_value("user", "name", name)
            cw.set_value("user", "email", email)
        logger.info(f"Configured Git user: {name} <{email}>")

    def _checkout_branch(self, repo: Repo, branch_name: str) -> Dict[str, Any]:
        """Checkout branch_name; create from origin/<branch> if exists, else new branch from current HEAD."""
        origin = repo.remotes.origin
        origin.fetch()  # refresh refs

        local_branches = [h.name for h in repo.heads]
        remote_branches = [ref.name.split("/", 1)[1] for ref in origin.refs if ref.name.startswith("origin/")]

        if branch_name in local_branches:
            repo.git.checkout(branch_name)
            logger.info(f"Checked out existing local branch: {branch_name}")
            try:
                repo.git.pull("--rebase", "origin", branch_name)
            except GitCommandError as e:
                logger.warning(f"Pull rebase warning: {e}")
            return {"created": False, "tracked_remote": True}
        elif branch_name in remote_branches:
            repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
            logger.info(f"Created local tracking branch from origin/{branch_name}")
            return {"created": True, "tracked_remote": True}
        else:
            repo.git.checkout("-b", branch_name)
            logger.info(f"Created new local branch: {branch_name}")
            return {"created": True, "tracked_remote": False}

    def _push_with_upstream(self, repo: Repo, branch_name: str) -> None:
        origin = repo.remotes.origin
        try:
            logger.info(f"Attempting git push: {branch_name}:{branch_name}")
            origin.push(f"{branch_name}:{branch_name}")
            logger.info(f"Successfully pushed to origin/{branch_name}")
        except GitCommandError as e:
            logger.warning(f"First push attempt failed, trying with --set-upstream. Error: {e.stderr}")
            try:
                repo.git.push("--set-upstream", "origin", branch_name)
                logger.info(f"Successfully pushed with --set-upstream to origin/{branch_name}")
            except GitCommandError as e_upstream:
                logger.error(f"Git push with --set-upstream failed: {e_upstream.stderr}")
                raise e_upstream # Re-raise the exception after logging

    def _push_generated_runs_folder_sync(self, repo_url: str, branch_name: str, commit_message: str) -> Dict[str, Any]:
        """Synchronous core (runs in a thread)."""
        generated_runs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated_runs"))
        if not os.path.exists(generated_runs_path) or not os.path.isdir(generated_runs_path):
            raise Exception(f"Generated runs folder not found at {generated_runs_path}")

        repo_path = self._get_repo_path(repo_url)
        self._ensure_clean_repo_path(repo_path)

        # Clone or open existing repo
        try:
            if os.path.exists(repo_path) and os.path.isdir(os.path.join(repo_path, ".git")):
                repo = Repo(repo_path)
                logger.info(f"Using existing repo at {repo_path}")
                repo.remotes.origin.fetch()
            else:
                repo = Repo.clone_from(repo_url, repo_path)
                logger.info(f"Cloned {repo_url} to {repo_path}")
        except (InvalidGitRepositoryError, NoSuchPathError):
            shutil.rmtree(repo_path, ignore_errors=True)
            repo = Repo.clone_from(repo_url, repo_path)
            logger.info(f"Re-cloned {repo_url} to {repo_path}")
        except GitCommandError as e:
            raise Exception(f"Git clone/fetch failed: {e.stderr or str(e)}")

        # Ensure we’re on the right branch
        info = self._checkout_branch(repo, branch_name)

        # Copy generated_runs folder into the cloned repo
        destination_path_in_repo = os.path.join(repo_path, "generated_runs")
        if os.path.exists(destination_path_in_repo):
            shutil.rmtree(destination_path_in_repo) # Clear existing folder
        shutil.copytree(generated_runs_path, destination_path_in_repo)
        logger.info(f"Copied {generated_runs_path} to {destination_path_in_repo}")

        # Stage & commit
        # Add all files in the copied directory
        repo.index.add([os.path.relpath(destination_path_in_repo, repo_path)])

        if repo.is_dirty(untracked_files=True):
            self._configure_user(repo)
            repo.index.commit(commit_message)
            logger.info(f"Committed changes in 'generated_runs' with message: '{commit_message}'")
        else:
            logger.info("No changes to commit (noop).")

        # Push
        try:
            self._push_with_upstream(repo, branch_name)
            logger.info(f"Pushed changes to origin/{branch_name}")
        except GitCommandError as e:
            raise Exception(f"Git push failed: {e.stderr or str(e)}")

        return {
            "repo_path": repo_path,
            "branch": branch_name,
            "created_branch": info["created"],
            "tracked_remote": info["tracked_remote"],
        }

    async def push_generated_runs_folder(self, repo_url: str, branch_name: str, commit_message: str) -> Dict[str, Any]:
        # run blocking GitPython ops off the event loop
        return await asyncio.to_thread(
            self._push_generated_runs_folder_sync, repo_url, branch_name, commit_message
        )

git_service = GitService()
