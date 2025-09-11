from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from services.git_service import git_service

router = APIRouter()

class GitPushGeneratedRunsRequest(BaseModel):
    repo_url: str = Field(..., description="HTTPS repo URL. For private repos, embed a token if needed.")
    branch_name: str
    commit_message: str

@router.post("/git/push-generated-runs", status_code=status.HTTP_200_OK)
async def push_generated_runs_to_git(request: GitPushGeneratedRunsRequest):
    try:
        result = await git_service.push_generated_runs_folder(
            repo_url=request.repo_url,
            branch_name=request.branch_name,
            commit_message=request.commit_message,
        )
        return {"message": "Generated runs pushed to Git successfully!", "details": result}
    except Exception as e:
        # surface the real reason to the frontend
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
