"""Quality calibration endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.modules.ielts.reading.calibration import run_calibration_from_repo

router = APIRouter(prefix="/quality", tags=["quality"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/reports/calibration")
async def get_calibration_report() -> dict[str, object]:
    report = run_calibration_from_repo(_repo_root())
    return report.model_dump(mode="json")
