# Smoke Tests — Benjo Moments Photography System

Run these checks after every migration phase to confirm nothing is broken.
Mark each ✅ pass / ❌ fail with notes.

---

## Public Pages

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| P1 | `/` | GET | Homepage loads; hero slider, gallery, pricing all visible |
| P2 | `/gallery` | GET | Gallery page loads with all published images |
| P3 | `/gallery?album=weddings` | GET | Filters to weddings album only |
| P4 | `/services` | GET | Services page loads without errors |
| P5 | `/about` | GET | About page loads without errors |
| P6 | `/contact` | GET | Contact form renders |
| P7 | `/contact` POST valid data | POST | Flash "Thank you" and redirect back |
| P8 | `/contact` POST missing name | POST | Flash validation error, no DB write |
| P9 | `/submit-contact` POST valid | POST | Redirects to `/#contact` with success flash |
| P10 | `/uploads/weddings/<filename>` | GET | Serves uploaded image or 404 for missing |
| P11 | `/uploads/hero/<filename>` | GET | Serves hero image or 404 for missing |

---

## Admin — Authentication

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| A1 | `/login` GET | GET | Login form renders |
| A2 | `/admin/login` GET | GET | Same login form (alias route) |
| A3 | Login with any email+pass (`TEST_AUTH_MODE=true`) | POST | Redirect to `/admin/` dashboard |
| A4 | Login with valid credentials (`TEST_AUTH_MODE=false`) | POST | Redirect to `/admin/` dashboard |
| A5 | Login with wrong password (`TEST_AUTH_MODE=false`) | POST | Flash "Invalid email or password" |
| A6 | `/admin/` without session | GET | Redirect to `/login` |
| A7 | `/logout` | POST | Session cleared, redirect to login |

---

## Admin — Dashboard

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| D1 | `/admin/` | GET | Dashboard with income/expense/profit/pending/asset totals |
| D2 | Recent transactions visible | GET | Up to 10 rows shown |

---

## Admin — Income

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| I1 | `/admin/income` | GET | Lists all income records with total |
| I2 | Add income (valid) | POST | Record appears in list |
| I3 | Add income (no description) | POST | Flash error, no record added |
| I4 | Add income (negative amount) | POST | Flash error |
| I5 | Delete income record | POST | Record removed from list |

---

## Admin — Expenses

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| E1 | `/admin/expenses` | GET | Lists all expense records with total |
| E2 | Add expense (valid) | POST | Record appears in list |
| E3 | Add expense (missing category) | POST | Flash error |
| E4 | Delete expense record | POST | Record removed |

---

## Admin — Assets

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| AS1 | `/admin/assets` | GET | Lists all assets with total value |
| AS2 | Add asset (valid) | POST | Asset appears in list |
| AS3 | Delete asset | POST | Asset removed |

---

## Admin — Customers

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| C1 | `/admin/customers` | GET | Lists customers with pending balance |
| C2 | Add customer (valid) | POST | Customer appears in list |
| C3 | Add customer (amount_paid > total_amount) | POST | Flash validation error |
| C4 | Delete customer | POST | Customer and their invoices removed |

---

## Admin — Invoices

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| IN1 | `/admin/invoices` | GET | Lists invoices with customer names |
| IN2 | Create invoice (valid) | POST | Invoice appears, auto-number generated |
| IN3 | Create invoice (duplicate number) | POST | Flash error |
| IN4 | Mark invoice paid | POST | Status changes to "Paid" |
| IN5 | Delete invoice | POST | Invoice removed |

---

## Admin — Reports

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| R1 | `/admin/reports` | GET | Empty state (no date range) |
| R2 | Reports with valid date range | GET | Income + expense records shown with totals |
| R3 | Reports with start > end | GET | Flash error, no data |

---

## Admin — Gallery

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| G1 | `/admin/gallery` | GET | Lists all gallery images |
| G2 | Upload image (valid jpg/png/webp) | POST | Image appears in list |
| G3 | Upload image (invalid type e.g. .exe) | POST | Flash error, no upload |
| G4 | Toggle image publish | POST | Published status flips |
| G5 | Delete image | POST | Image removed from list (file deleted from disk) |

---

## Admin — Website Settings

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| WS1 | `/admin/settings` | GET | Settings form populated with current values |
| WS2 | Save settings (valid) | POST | Flash success, values updated |
| WS3 | Save settings (no site name) | POST | Flash error |
| WS4 | Upload hero image | POST | Image appears in hero slider list |
| WS5 | Delete hero image | POST | Image removed from list |

---

## Admin — Pricing Packages

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| PP1 | `/admin/pricing` | GET | Lists all pricing packages |
| PP2 | Add package (valid) | POST/GET | Package appears in list |
| PP3 | Edit package | POST/GET | Updated values saved |
| PP4 | Delete package | POST | Package removed |
| PP5 | Toggle package active/inactive | POST | Status changes |

---

## Admin — Messages

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| M1 | `/admin/messages` | GET | Lists all contact messages |
| M2 | Mark message as read | POST | Message marked read |
| M3 | Delete message | POST | Message removed from list |

---

## Environment / Config Checks

| # | Check | Expected |
|---|-------|----------|
| ENV1 | `SECRET_KEY` not set in production | App raises `RuntimeError` at startup |
| ENV2 | `TEST_AUTH_MODE=true` | Any email/password logs in |
| ENV3 | `TEST_AUTH_MODE=false` | Only valid DB users log in |
| ENV4 | `DATABASE_URL` set to Postgres | App connects to Postgres |
| ENV5 | `DATABASE_URL` unset (local dev) | Falls back to SQLite (if `USE_SQLITE_FALLBACK=true`) |
| ENV6 | `alembic upgrade head` on fresh DB | All tables created successfully |
