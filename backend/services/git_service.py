import os
import shutil
from git import Repo, GitCommandError
import logging

logger = logging.getLogger(__name__)

class GitService:
    def __init__(self, base_dir="temp_repos"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_repo_path(self, repo_url: str) -> str:
        # Create a unique directory name based on repo URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        return os.path.join(self.base_dir, repo_name)

    async def push_test_cases(self, repo_url: str, branch_name: str, commit_message: str, test_cases: list[str]):
        repo_path = self._get_repo_path(repo_url)

        try:
            if os.path.exists(repo_path):
                # If repo already exists, pull latest changes
                repo = Repo(repo_path)
                origin = repo.remotes.origin
                origin.pull()
                logger.info(f"Pulled latest changes for {repo_url}")
            else:
                # Clone the repository if it doesn't exist
                repo = Repo.clone_from(repo_url, repo_path)
                logger.info(f"Cloned {repo_url} to {repo_path}")

            # Checkout to the specified branch, create if it doesn't exist
            if branch_name not in repo.heads:
                repo.create_head(branch_name)
                logger.info(f"Created new branch: {branch_name}")
            repo.git.checkout(branch_name)
            logger.info(f"Checked out to branch: {branch_name}")

            # Write test cases to files
            for i, test_case_content in enumerate(test_cases):
                # Determine a suitable filename. For simplicity, let's use a generic name for now.
                # In a real application, you might want a more structured naming convention.
                file_name = f"automated_test_case_{i}.py" # Assuming Python test cases
                file_path = os.path.join(repo_path, file_name)
                with open(file_path, "w") as f:
                    f.write(test_case_content)
                logger.info(f"Wrote test case to {file_path}")

            # Add, commit, and push
            repo.index.add([file_name for i, _ in enumerate(test_cases)]) # Add all new test case files
            repo.index.commit(commit_message)
            logger.info(f"Committed changes with message: '{commit_message}'")

            origin = repo.remotes.origin
            origin.push(branch_name)
            logger.info(f"Pushed changes to {branch_name} branch.")

        except GitCommandError as e:
            logger.error(f"Git command error: {e}")
            raise Exception(f"Git command failed: {e.stderr}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise Exception(f"An unexpected error occurred during Git operation: {e}")
        finally:
            # Clean up the cloned repository after operation (optional, but good for temp files)
            # shutil.rmtree(repo_path, ignore_errors=True)
            # logger.info(f"Cleaned up temporary repository at {repo_path}")
            pass # Keep the repo for subsequent pushes to avoid re-cloning

git_service = GitService()
