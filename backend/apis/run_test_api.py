from fastapi import APIRouter, HTTPException

router = APIRouter()


def _not_implemented():
    raise HTTPException(status_code=501, detail="Test execution endpoint is not implemented yet.")


@router.get("/run")
def run_tests():
    return _not_implemented()


@router.get("/report")
def report():
    return {"report_url": "/reports/view"}


@router.get("/open")
def open_report():
    return {"report_url": "/reports/view"}
