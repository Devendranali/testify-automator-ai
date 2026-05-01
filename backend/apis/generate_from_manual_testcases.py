from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import re
from sqlalchemy.orm import Session
from database.session import get_db
from services.token_service import log_token_usage
from utils.openai_client import call_openai
from utils.openai_client import OpenAIClientError
from utils.request_context import get_project_id

router = APIRouter()

class ManualTestcaseRequest(BaseModel):
    manual_testcase: str | list[str] = Field(..., example=[
        "1. Navigate to login page",
        "2. Enter username 'standard_user'",
        "3. Enter password 'secret_sauce'",
        "4. Click Login button",
        "5. Verify Products page is displayed"
    ])
    prompt: str = Field(
    default=(
        "Write a Playwright Python test for the following manual steps.\n"
        "- Use only visible selectors (get_by_text, get_by_role, get_by_placeholder).\n"
        "- Print before each action.\n"
        "- For every verification, 'should be displayed', or 'verify' step, add a Playwright `expect` assertion, such as `expect(page.get_by_text('...')).to_be_visible()`.\n"
        "- Do not use page.locator or xpath.\n"
        "- Site URL: {site_url}\n"
        "Steps:\n"
        "{manual_steps}"
        )
    )
    site_url: str = Field(default="https://www.saucedemo.com/")

@router.post("/rag/generate-from-manual-testcase")
def generate_from_manual_testcase(
    req: ManualTestcaseRequest,
    project_id: int | None = None,
    db: Session = Depends(get_db),
):
    db_session = db if isinstance(db, Session) else None
    manual_steps = "\n".join(req.manual_testcase) if isinstance(req.manual_testcase, list) else req.manual_testcase.strip()
    prompt = req.prompt.format(manual_steps=manual_steps, site_url=req.site_url)
    try:
        result = call_openai(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        log_token_usage(
            db=db_session,
            project_id=project_id or get_project_id(),
            feature="ui_generation",
            usage=result.get("usage"),
            model=result.get("model"),
        )
    except OpenAIClientError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    test_code = (result.get("content") or "").strip()
    code = re.sub(r"```(?:python)?|```|^\s*Here is.*?:", "", test_code, flags=re.MULTILINE).strip()

    # Write to file in root folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_manualcase_{timestamp}.py"
    filepath = filename  # root folder
    # Optionally add Playwright import if not present
    if "from playwright.sync_api" not in code:
        code = "from playwright.sync_api import sync_playwright, expect\n\n" + code

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    return {"auto_testcase": code, "filename": filename}
