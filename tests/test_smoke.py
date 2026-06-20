"""PostgreSQL-backed smoke tests for the Benjo Moments release."""

import io
import os
import shutil
import unittest
import uuid
import zipfile

from PIL import Image
from sqlalchemy import delete, select

import config
import database
from app import create_app
from db import SessionLocal
from extensions import limiter
from models import Asset, AuditLog, Customer, Expense, ServiceCategory, User


class ReleaseSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.suffix = uuid.uuid4().hex[:10]

    def setUp(self):
        limiter.reset()
        self.client = self.app.test_client()
        self.client.get("/login")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        response = self.client.post(
            "/login",
            data={
                "email": config.DEFAULT_ADMIN_EMAIL,
                "password": config.DEFAULT_ADMIN_PASSWORD,
                "csrf_token": token,
            },
        )
        self.assertEqual(response.status_code, 302)

    def csrf(self, client=None):
        client = client or self.client
        with client.session_transaction() as session:
            return session["_csrf_token"]

    def test_public_and_admin_pages(self):
        for path in ("/", "/gallery?q=wedding", "/services", "/about", "/contact", "/client-gallery", "/healthz"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                if path == "/":
                    self.assertNotIn(b"Featured Work", response.data)
                    self.assertNotIn(b"Our Services", response.data)
                if path.startswith("/gallery"):
                    self.assertIn(b"portfolio-masonry", response.data)
        for path in (
            "/admin/", "/admin/guide", "/admin/income", "/admin/expenses",
            "/admin/invoices", "/admin/customers", "/admin/assets", "/admin/reports",
            "/admin/client-collections", "/admin/messages", "/admin/gallery",
            "/admin/services", "/admin/pricing", "/admin/pricing/add",
            "/admin/settings", "/admin/users",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Page guide", response.data)
        guide = self.client.get("/admin/guide")
        self.assertIn(b"Deliver client photos", guide.data)
        self.assertIn(b"Weekly or monthly review", guide.data)
        self.assertEqual(self.client.post("/logout").status_code, 400)

    def test_multi_admin_equal_access(self):
        email = f"admin-{self.suffix}@example.com"
        password = f"Secure-{self.suffix}-Pass"
        database.create_user(f"Admin {self.suffix}", email, password)
        try:
            other = self.app.test_client()
            other.get("/login")
            with other.session_transaction() as session:
                token = session["_csrf_token"]
            response = other.post(
                "/login",
                data={"email": email, "password": password, "csrf_token": token},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(other.get("/admin/users").status_code, 200)
            self.assertEqual(other.get("/admin/client-collections").status_code, 200)
        finally:
            with SessionLocal() as session:
                session.execute(delete(User).where(User.email == email))
                session.commit()

    def test_services_finance_assets_and_unpaid_sorting(self):
        category_name = f"Smoke Services {self.suffix}"
        database.add_service_category(category_name, "Temporary smoke category", "fa-camera", "", 999)
        catalogue = database.get_service_catalogue(active_only=False)
        self.assertTrue(any(item["name"] == category_name for item in catalogue))

        asset_name = f"Smoke Camera {self.suffix}"
        database.add_asset(asset_name, "Camera", 1000000, "Smoke Supplier")
        with SessionLocal() as session:
            asset_id = session.scalar(select(Asset.id).where(Asset.name == asset_name))
        database.add_expense(
            "2026-06-19", f"Repair {self.suffix}", f"Custom {self.suffix}", 50000,
            asset_id, "pending", "Repair Shop", "2026-06-30", None,
        )
        assets = database.get_all_assets()
        asset = next(item for item in assets if item["id"] == asset_id)
        self.assertEqual(asset["expense_total"], 50000.0)
        self.assertGreaterEqual(database.get_outstanding_expenses_total(), 50000.0)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        expenses_page = self.client.get("/admin/expenses")
        self.assertIn(b'name="amount" min="1" step="1"', expenses_page.data)
        report = self.client.get(
            "/admin/reports",
            query_string={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        self.assertEqual(report.status_code, 200)
        self.assertIn(f"Repair {self.suffix}".encode(), report.data)
        self.assertIn(b"expense record", report.data)
        bounded_report = database.get_financial_report(
            "2026-06-01", "2026-06-30", detail_limit=1
        )
        self.assertLessEqual(len(bounded_report["expense_records"]), 1)
        self.assertGreaterEqual(bounded_report["total_expenses"], 50000)

        paid_name = f"Paid {self.suffix}"
        unpaid_name = f"Unpaid {self.suffix}"
        database.add_customer(paid_name, "Portrait", 100000, 100000, "", "Studio")
        database.add_customer(unpaid_name, "Wedding", 0, 200000, "", "Kampala")
        customers = database.get_all_customers()
        self.assertLess(
            next(i for i, row in enumerate(customers) if row["name"] == unpaid_name),
            next(i for i, row in enumerate(customers) if row["name"] == paid_name),
        )

        with SessionLocal() as session:
            session.execute(delete(Expense).where(Expense.description == f"Repair {self.suffix}"))
            session.execute(delete(Asset).where(Asset.id == asset_id))
            session.execute(delete(Customer).where(Customer.name.in_([paid_name, unpaid_name])))
            session.execute(delete(ServiceCategory).where(ServiceCategory.name == category_name))
            session.commit()

    def test_private_collection_pin_download_and_comments(self):
        pin = f"{self.suffix}42"
        collection = database.add_client_collection(
            f"Smoke Collection {self.suffix}", f"Client {self.suffix}",
            f"client-{self.suffix}@example.com", "Smoke delivery", "Studio",
            "2026-06-19", None, pin, None, None,
        )
        collection_id = collection["id"]
        code = collection["collection_code"]
        directory = os.path.join(config.UPLOAD_FOLDER, "client_collections", str(collection_id))
        try:
            first_image = io.BytesIO()
            second_image = io.BytesIO()
            Image.new("RGB", (2000, 1200), color=(220, 45, 80)).save(first_image, format="JPEG")
            Image.new("RGB", (1200, 2000), color=(30, 120, 210)).save(second_image, format="JPEG")
            first_image.seek(0)
            second_image.seek(0)
            response = self.client.post(
                f"/admin/client-collections/{collection_id}/upload",
                data={
                    "csrf_token": self.csrf(),
                    "caption": f"Smoke photo {self.suffix}",
                    "images": [
                        (first_image, f"smoke-first-{self.suffix}.jpg"),
                        (second_image, f"smoke-cover-{self.suffix}.jpg"),
                    ],
                },
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 302)
            stored_collection = database.get_client_collection(collection_id)
            image = stored_collection["images"][0]
            selected_cover = stored_collection["images"][1]
            self.assertEqual(stored_collection["cover_image_id"], image["id"])
            response = self.client.post(
                f"/admin/client-collections/{collection_id}/images/{selected_cover['id']}/cover",
                data={"csrf_token": self.csrf()},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                database.get_client_collection(collection_id)["cover_image_id"],
                selected_cover["id"],
            )

            public_directory = self.client.get(
                "/client-gallery",
                query_string={"q": f"Smoke Collection {self.suffix}"},
            )
            self.assertEqual(public_directory.status_code, 200)
            self.assertIn(f"Smoke Collection {self.suffix}".encode(), public_directory.data)
            admin_directory = self.client.get(
                "/admin/client-collections",
                query_string={"q": f"Client {self.suffix}", "status": "active"},
            )
            self.assertEqual(admin_directory.status_code, 200)
            self.assertIn(f"Smoke Collection {self.suffix}".encode(), admin_directory.data)
            detail = self.client.get(f"/admin/client-collections/{collection_id}")
            self.assertEqual(detail.status_code, 200)
            self.assertIn(b"Collection setup guide", detail.data)
            self.assertIn(b"Preview Gallery", detail.data)
            self.assertIn(b"Set Cover", detail.data)
            self.assertIn(b"Client Share Link", detail.data)
            self.assertIn(f"/client-gallery/{code}".encode(), detail.data)
            preview = self.client.get(f"/client-gallery/{code}/photos")
            self.assertEqual(preview.status_code, 200)
            self.assertIn(b"Manager Preview", preview.data)
            self.assertIn(b"client-photo-masonry", preview.data)
            self.assertEqual(len(database.get_collection_activity(collection_id)["visitors"]), 0)

            visitor = self.app.test_client()
            cover = visitor.get(f"/client-gallery/{code}/cover")
            self.assertEqual(cover.status_code, 200)
            rendered_cover = Image.open(io.BytesIO(cover.data)).convert("RGB")
            red, green, blue = rendered_cover.getpixel((0, 0))
            self.assertGreater(blue, red)
            cover.close()
            unlock_page = visitor.get(f"/client-gallery/{code}")
            self.assertIn(f"v={selected_cover['id']}".encode(), unlock_page.data)
            self.assertIn(b"collection-cover-image", unlock_page.data)
            with visitor.session_transaction() as session:
                token = session["_csrf_token"]
            rejected = visitor.post(
                f"/client-gallery/{code}",
                data={
                    "csrf_token": token,
                    "name": "Smoke Visitor",
                    "email": f"visitor-{self.suffix}@example.com",
                    "pin": "wrong-pin",
                },
            )
            self.assertEqual(rejected.status_code, 200)
            self.assertIn(b"collection PIN was not accepted", rejected.data)
            self.assertEqual(len(database.get_collection_activity(collection_id)["visitors"]), 0)
            response = visitor.post(
                f"/client-gallery/{code}",
                data={
                    "csrf_token": token,
                    "name": "Smoke Visitor",
                    "email": f"visitor-{self.suffix}@example.com",
                    "pin": f"  {pin}  ",
                },
            )
            self.assertEqual(response.status_code, 302)
            client_gallery = visitor.get(f"/client-gallery/{code}/photos")
            self.assertEqual(client_gallery.status_code, 200)
            self.assertIn(b"client-photo-masonry", client_gallery.data)
            self.assertIn(b"collection-cover-image", client_gallery.data)
            self.assertNotIn(b"Manager Preview", client_gallery.data)
            self.assertIn(b"Web / Social", client_gallery.data)
            like_url = f"/client-gallery/{code}/photo/{image['id']}/like"
            self.assertEqual(
                visitor.post(like_url, data={"csrf_token": token}).status_code,
                302,
            )
            self.assertEqual(len(database.get_collection_activity(collection_id)["likes"]), 1)
            visitor.post(like_url, data={"csrf_token": token})
            self.assertEqual(len(database.get_collection_activity(collection_id)["likes"]), 0)
            visitor.post(like_url, data={"csrf_token": token})
            self.assertEqual(len(database.get_collection_activity(collection_id)["likes"]), 1)
            download = visitor.get(f"/client-gallery/{code}/download/{image['id']}")
            self.assertEqual(download.status_code, 200)
            download.close()
            web_download = visitor.get(
                f"/client-gallery/{code}/download/{image['id']}?quality=web"
            )
            self.assertEqual(web_download.status_code, 200)
            web_image = Image.open(io.BytesIO(web_download.data))
            self.assertEqual(max(web_image.size), 1600)
            self.assertIn("-web.jpg", web_download.headers["Content-Disposition"])
            web_download.close()
            self.assertEqual(
                visitor.get(
                    f"/client-gallery/{code}/download/{image['id']}?quality=unknown"
                ).status_code,
                400,
            )
            download_all = visitor.get(
                f"/client-gallery/{code}/download-all?quality=web"
            )
            self.assertEqual(download_all.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(download_all.data)) as archive:
                names = archive.namelist()
                self.assertEqual(len(names), 2)
                self.assertTrue(all(name.endswith("-web.jpg") for name in names))
                with archive.open(names[0]) as member:
                    zipped_image = Image.open(io.BytesIO(member.read()))
                    self.assertLessEqual(max(zipped_image.size), 1600)
            download_all.close()
            response = visitor.post(
                f"/client-gallery/{code}/photo/{image['id']}/comment",
                data={"csrf_token": token, "comment": "Please retouch this image."},
            )
            self.assertEqual(response.status_code, 302)
            activity = database.get_collection_activity(collection_id)
            self.assertEqual(len(activity["visitors"]), 1)
            self.assertGreaterEqual(len(activity["downloads"]), 3)
            self.assertEqual(len(activity["likes"]), 1)
            self.assertEqual(len(activity["comments"]), 1)
            manager_activity = self.client.get(
                f"/admin/client-collections/{collection_id}"
            )
            self.assertIn(b"Client Likes", manager_activity.data)
            self.assertIn(b"Image Web", manager_activity.data)
        finally:
            database.delete_client_collection(collection_id)
            shutil.rmtree(directory, ignore_errors=True)

    def test_new_whatsapp_number(self):
        self.assertEqual(database.get_website_settings()["whatsapp_number"], "256759189861")

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as session:
            session.execute(
                delete(AuditLog).where(AuditLog.details_json.ilike(f"%{cls.suffix}%"))
            )
            session.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
