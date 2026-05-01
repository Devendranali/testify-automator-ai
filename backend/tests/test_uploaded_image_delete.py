import asyncio
import os
import sys
import tempfile
import uuid
import json
from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

_DB_DIR = Path(tempfile.mkdtemp())
_DB_PATH = _DB_DIR / "uploaded-image-delete.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

from database import session as db_session  # noqa: E402
from database.models import ImageMetadata, Organization, OrganizationMember, Project, ProjectFile, User, TestCaseMetadata  # noqa: E402
from database.project_storage import DatabaseBackedProjectStorage  # noqa: E402
from apis.projects_api import _ensure_project_structure  # noqa: E402
from fastapi import UploadFile  # noqa: E402
from utils.match_utils import normalize_page_name  # noqa: E402
from apis.generate_page_methods import _page_entries_from_enrichment  # noqa: E402
from apis.image_text_api import (  # noqa: E402
    DeleteUploadedImagesRequest,
    PreviewImageImpactRequest,
    delete_uploaded_images,
    preview_image_change_impact,
    replace_uploaded_image,
)


Organization.__table__.create(db_session.engine, checkfirst=True)
Project.__table__.create(db_session.engine, checkfirst=True)
User.__table__.create(db_session.engine, checkfirst=True)
OrganizationMember.__table__.create(db_session.engine, checkfirst=True)
ProjectFile.__table__.create(db_session.engine, checkfirst=True)
ImageMetadata.__table__.create(db_session.engine, checkfirst=True)
TestCaseMetadata.__table__.create(db_session.engine, checkfirst=True)


def _create_user_and_project(db):
    org = Organization.get_or_create(db, "Delete Image Org")
    user = User(
        organization=org.name,
        organization_id=org.id,
        email="delete-image-user@example.com",
        password_hash="test-hash",
    )
    db.add(user)
    db.flush()
    OrganizationMember.ensure_member(db, user.id, org.id)

    project = Project(
        organization=org.name,
        organization_id=org.id,
        created_by=user.id,
        project_name=f"Delete Image Project {uuid.uuid4().hex[:8]}",
        framework="Playwright",
        language="Python",
    )
    db.add(project)
    db.commit()
    db.refresh(user)
    db.refresh(project)
    return user, project


def test_delete_uploaded_image_removes_matching_page_method_from_disk_and_db():
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        project_root = Path(project_paths["project_root"])
        src_root = Path(project_paths["src_dir"])

        root_storage = DatabaseBackedProjectStorage(project, project_root, db)
        root_storage.write_file("data/images/checkout-page.png", "ZmFrZS1pbWFnZQ==", "base64")

        src_storage = DatabaseBackedProjectStorage(project, src_root, db)
        src_storage.write_file("pages/checkout_page_page_methods.py", "# generated pom", "utf-8")

        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[{"label_text": "Checkout"}],
            )
        )
        db.commit()

        response = asyncio.run(
            delete_uploaded_images(
                project_id=project.id,
                payload=DeleteUploadedImagesRequest(image_names=["checkout-page.png"]),
                db=db,
                current_user=user,
            )
        )
        db.commit()

        assert response["status"] == "success"
        assert response["deleted"][0]["image_name"] == "checkout-page.png"
        assert response["deleted"][0]["pom_path"] == "pages/checkout_page_page_methods.py"

        assert (
            db.query(ProjectFile)
            .filter(ProjectFile.project_id == project.id, ProjectFile.path == "data/images/checkout-page.png")
            .first()
            is None
        )
        assert (
            db.query(ProjectFile)
            .filter(ProjectFile.project_id == project.id, ProjectFile.path == "pages/checkout_page_page_methods.py")
            .first()
            is None
        )
        assert (
            db.query(ImageMetadata)
            .filter(ImageMetadata.project_id == project.id, ImageMetadata.image_name == "checkout-page.png")
            .first()
            is None
        )
        assert response["impact"]["change_type"] == "delete"
    finally:
        db.close()


def test_delete_uploaded_image_returns_impacted_testcases_for_removed_page():
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        project_root = Path(project_paths["project_root"])
        src_root = Path(project_paths["src_dir"])

        root_storage = DatabaseBackedProjectStorage(project, project_root, db)
        root_storage.write_file("data/images/checkout-page.png", "ZmFrZS1pbWFnZQ==", "base64")

        src_storage = DatabaseBackedProjectStorage(project, src_root, db)
        src_storage.write_file("pages/checkout_page_page_methods.py", "# generated pom", "utf-8")
        (src_root / "tests" / "ui").mkdir(parents=True, exist_ok=True)
        (src_root / "tests" / "ui" / "test_checkout.py").write_text(
            "from pages.checkout_page_page_methods import *\n\n"
            "def test_checkout_flow(page):\n"
            "    click_checkout(page)\n",
            encoding="utf-8",
        )

        case_uuid = uuid.uuid4().hex
        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[],
            )
        )
        db.add(
            TestCaseMetadata(
                project_id=project.id,
                case_uuid=case_uuid,
                test_name="checkout_flow",
                display_name="Checkout Flow",
                user_story="Checkout story",
                auto_testcase="auto",
                test_type="ui",
                script_path="tests/ui/test_checkout.py",
                runner_script_path=None,
                markers=[],
                tags=[],
                priority="Low",
            )
        )
        db.commit()

        response = asyncio.run(
            delete_uploaded_images(
                project_id=project.id,
                payload=DeleteUploadedImagesRequest(image_names=["checkout-page.png"]),
                db=db,
                current_user=user,
            )
        )

        assert response["impact"]["count"] == 1
        impacted = response["impact"]["impacted_testcases"][0]
        assert impacted["case_uuid"] == case_uuid
        assert impacted["reason"] == "page_missing_after_image_change"
        assert impacted["script_path"] == "tests/ui/test_checkout.py"
        assert "checkout_page_page_methods" in impacted["impacted_page_modules"]
    finally:
        db.close()


def test_replace_uploaded_image_deletes_old_asset_and_regenerates_new_page(monkeypatch):
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        calls = {}

        async def _fake_delete(project_id, payload, db, current_user):
            calls["delete"] = {
                "project_id": project_id,
                "image_names": list(payload.image_names),
            }
            return {"status": "success", "deleted": [{"image_name": payload.image_names[0]}], "missing": []}

        async def _fake_upload(project_id, images, ordered_images, db, current_user):
            calls["upload"] = {
                "project_id": project_id,
                "filenames": [img.filename for img in images],
                "ordered_images": ordered_images,
            }
            body = (
                b'{"status":"success","data":[{"image_name":"replacement-page.png","page_name":"replacement_page"}]}'
            )

            class _Response:
                def __init__(self, body):
                    self.body = body

            return _Response(body)

        def _fake_generate(project_id, pages, db, current_user):
            calls["generate"] = {
                "project_id": project_id,
                "pages": pages,
            }
            return {"replacement_page": {"methods_file": "pages/replacement_page_page_methods.py"}}

        monkeypatch.setattr("apis.image_text_api.delete_uploaded_images", _fake_delete)
        monkeypatch.setattr("apis.image_text_api.upload_image", _fake_upload)
        monkeypatch.setattr("apis.generate_page_methods.generate_page_methods", _fake_generate)

        upload = UploadFile(filename="replacement-page.png", file=open(__file__, "rb"))
        try:
            response = asyncio.run(
                replace_uploaded_image(
                    project_id=project.id,
                    old_image_name="checkout-page.png",
                    image=upload,
                    db=db,
                    current_user=user,
                )
            )
        finally:
            upload.file.close()

        assert response["status"] == "success"
        assert calls["delete"]["image_names"] == ["checkout-page.png"]
        assert calls["upload"]["filenames"] == ["replacement-page.png"]
        assert calls["generate"]["pages"] == "replacement_page"
        assert response["replaced"]["new_page_name"] == "replacement_page"
        assert response["replaced"]["generated"]["methods_file"] == "pages/replacement_page_page_methods.py"
    finally:
        db.close()


def test_replace_uploaded_image_returns_conservative_impacts(monkeypatch):
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        src_root = Path(project_paths["src_dir"])
        tests_dir = src_root / "tests" / "ui"
        tests_dir.mkdir(parents=True, exist_ok=True)
        script_rel = "tests/ui/test_checkout.py"
        script_path = src_root / script_rel
        script_path.write_text(
            "from pages.checkout_page_page_methods import CheckoutPage\n\n"
            "def test_checkout_flow(page):\n"
            "    CheckoutPage()\n",
            encoding="utf-8",
        )

        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[],
            )
        )
        db.add(
            TestCaseMetadata(
                project_id=project.id,
                case_uuid=uuid.uuid4().hex,
                test_name="checkout_flow",
                display_name="Checkout Flow",
                user_story="Checkout story",
                auto_testcase="auto",
                test_type="ui",
                script_path=script_rel,
                runner_script_path=None,
                markers=[],
                tags=[],
                priority="Low",
            )
        )
        db.commit()

        async def _fake_delete(project_id, payload, db, current_user):
            return {"status": "success", "deleted": [{"image_name": payload.image_names[0]}], "missing": []}

        async def _fake_upload(project_id, images, ordered_images, db, current_user):
            body = (
                b'{"status":"success","data":[{"image_name":"replacement-page.png","page_name":"replacement_page"}]}'
            )

            class _Response:
                def __init__(self, body):
                    self.body = body

            return _Response(body)

        def _fake_generate(project_id, pages, db, current_user):
            replacement_path = src_root / "pages" / "replacement_page_page_methods.py"
            replacement_path.parent.mkdir(parents=True, exist_ok=True)
            replacement_path.write_text("# replacement pom", encoding="utf-8")
            return {"replacement_page": {"methods_file": "pages/replacement_page_page_methods.py"}}

        monkeypatch.setattr("apis.image_text_api.delete_uploaded_images", _fake_delete)
        monkeypatch.setattr("apis.image_text_api.upload_image", _fake_upload)
        monkeypatch.setattr("apis.generate_page_methods.generate_page_methods", _fake_generate)

        upload = UploadFile(filename="replacement-page.png", file=open(__file__, "rb"))
        try:
            response = asyncio.run(
                replace_uploaded_image(
                    project_id=project.id,
                    old_image_name="checkout-page.png",
                    image=upload,
                    db=db,
                    current_user=user,
                )
            )
        finally:
            upload.file.close()

        assert response["impact"]["mode"] == "conservative"
        assert response["impact"]["affected_page"] == "checkout_page"
        assert response["impact"]["count"] == 1
        impacted = response["impact"]["impacted_testcases"][0]
        assert impacted["display_name"] == "Checkout Flow"
        assert impacted["script_path"] == script_rel
        assert impacted["reason"] == "page_missing_after_image_change"
        assert "checkout_page_page_methods" in impacted["impacted_page_modules"]
    finally:
        db.close()


def test_preview_image_change_impact_for_delete_returns_linked_testcases():
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        src_root = Path(project_paths["src_dir"])
        tests_dir = src_root / "tests" / "ui"
        tests_dir.mkdir(parents=True, exist_ok=True)
        script_rel = "tests/ui/test_checkout_preview.py"
        (src_root / script_rel).write_text(
            "from pages.checkout_page_page_methods import *\n\n"
            "def test_checkout_preview(page):\n"
            "    click_checkout(page)\n",
            encoding="utf-8",
        )
        (src_root / "pages").mkdir(parents=True, exist_ok=True)
        (src_root / "pages" / "checkout_page_page_methods.py").write_text("# generated pom", encoding="utf-8")

        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[],
            )
        )
        db.add(
            TestCaseMetadata(
                project_id=project.id,
                case_uuid=uuid.uuid4().hex,
                test_name="checkout_preview",
                display_name="Checkout Preview",
                user_story="Checkout preview story",
                auto_testcase="auto",
                test_type="ui",
                script_path=script_rel,
                runner_script_path=None,
                markers=[],
                tags=[],
                priority="Low",
            )
        )
        db.commit()

        response = asyncio.run(
            preview_image_change_impact(
                project_id=project.id,
                payload=PreviewImageImpactRequest(
                    image_name="checkout-page.png",
                    action_type="delete",
                ),
                db=db,
                current_user=user,
            )
        )

        assert response["status"] == "success"
        assert response["impact"]["change_type"] == "delete"
        assert response["impact"]["affected_page"] == "checkout_page"
        assert response["impact"]["count"] == 1
        assert response["impact"]["impacted_testcases"][0]["display_name"] == "Checkout Preview"
    finally:
        db.close()


def test_preview_image_change_impact_for_replace_includes_new_page_name():
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        src_root = Path(project_paths["src_dir"])
        (src_root / "pages").mkdir(parents=True, exist_ok=True)
        (src_root / "pages" / "checkout_page_page_methods.py").write_text("# generated pom", encoding="utf-8")

        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[],
            )
        )
        db.commit()

        response = asyncio.run(
            preview_image_change_impact(
                project_id=project.id,
                payload=PreviewImageImpactRequest(
                    image_name="checkout-page.png",
                    action_type="replace",
                    replacement_image_name="replacement-page.png",
                ),
                db=db,
                current_user=user,
            )
        )

        assert response["status"] == "success"
        assert response["impact"]["change_type"] == "replace"
        assert response["impact"]["affected_pages"] == ["checkout_page", normalize_page_name("replacement-page.png")]
        assert response["impact"]["new_image_name"] == "replacement-page.png"
        assert response["impact"]["new_page_name"] == normalize_page_name("replacement-page.png")
    finally:
        db.close()


def test_delete_uploaded_image_removes_metadata_so_page_methods_are_not_regenerated():
    db = db_session.SessionLocal()
    try:
        user, project = _create_user_and_project(db)
        project_paths = _ensure_project_structure(project)
        project_root = Path(project_paths["project_root"])
        src_root = Path(project_paths["src_dir"])

        root_storage = DatabaseBackedProjectStorage(project, project_root, db)
        root_storage.write_file("data/images/checkout-page.png", "ZmFrZS1pbWFnZQ==", "base64")

        src_storage = DatabaseBackedProjectStorage(project, src_root, db)
        src_storage.write_file("pages/checkout_page_page_methods.py", "# generated pom", "utf-8")
        src_storage.write_file("pages/checkout_page_page.py", "# legacy pom", "utf-8")
        src_storage.write_file(
            "metadata/after_enrichment_checkout_page.json",
            json.dumps([{"page_name": "checkout_page", "unique_name": "checkout_btn", "label_text": "Checkout", "ocr_type": "button"}]),
            "utf-8",
        )
        src_storage.write_file(
            "metadata/before_enrichment_checkout_page.json",
            json.dumps([{"page_name": "checkout_page", "unique_name": "checkout_btn", "label_text": "Checkout", "ocr_type": "button"}]),
            "utf-8",
        )

        db.add(
            ImageMetadata(
                project_id=project.id,
                page_name="checkout_page",
                image_name="checkout-page.png",
                metadata_json=[],
            )
        )
        db.commit()

        response = asyncio.run(
            delete_uploaded_images(
                project_id=project.id,
                payload=DeleteUploadedImagesRequest(image_names=["checkout-page.png"]),
                db=db,
                current_user=user,
            )
        )
        db.commit()

        assert response["status"] == "success"
        assert not (src_root / "pages" / "checkout_page_page_methods.py").exists()
        assert not (src_root / "pages" / "checkout_page_page.py").exists()
        assert not (src_root / "metadata" / "after_enrichment_checkout_page.json").exists()
        assert not (src_root / "metadata" / "before_enrichment_checkout_page.json").exists()
        assert "checkout_page" not in _page_entries_from_enrichment(src_root / "metadata", "after_enrichment")
        assert "checkout_page" not in _page_entries_from_enrichment(src_root / "metadata", "before_enrichment")
    finally:
        db.close()
