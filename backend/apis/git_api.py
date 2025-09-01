from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List
from services.git_service import git_service # Import the service

router = APIRouter()

class GitPushRequest(BaseModel):
    repo_url: str
    branch_name: str
    commit_message: str
    test_cases: List[str] # List of test case contents

@router.post("/git/push-testcase", status_code=status.HTTP_200_OK)
async def push_testcase_to_git(request: GitPushRequest):
    try:
        await git_service.push_test_cases(
            repo_url=request.repo_url,
            branch_name=request.branch_name,
            commit_message=request.commit_message,
            test_cases=request.test_cases
        )
        return {"message": "Test cases pushed to Git successfully!"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
