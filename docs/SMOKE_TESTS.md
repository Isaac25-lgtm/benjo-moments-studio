# Smoke Tests — Benjo Moments Photography System

Run these checks after every migration phase to confirm nothing is broken.
Mark each ✅ pass / ❌ fail with notes.

---

## Public Pages

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| P1 | `/` | GET | Homepage loads; hero, committee inquiry, about, pricing, and contact are visible; duplicate Services and Featured Work sections are absent |
| P2 | `/gallery` | GET | Gallery page loads published images in a natural-aspect masonry layout |
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
| A4 | Login with environment credentials (`TEST_AUTH_MODE=false`) | POST | Redirect to `/admin/` dashboard |
| A5 | Login with any other email/password (`TEST_AUTH_MODE=false`) | POST | Flash "Invalid email or password" |
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
| E5 | Enter a round amount such as UGX 5,000 | Browser | Amount is accepted without a step-mismatch warning |

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
| R2 | Reports with valid date range containing an asset-linked expense | GET | Income + expense records shown with database-calculated totals |
| R3 | Reports with start > end | GET | Flash error, no data |
| R4 | Reports with more than 500 matching records | GET | Summary includes every record while detail is limited to the newest 500 |

---

## Admin — Gallery

| # | URL / Action | Method | Expected Result |
|---|-------------|--------|-----------------|
| G1 | `/admin/gallery` | GET | Lists all gallery images |
| G2 | Upload up to 25 valid jpg/png/webp images | POST | Images appear in list; another batch can be added afterward |
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
| ENV3 | `TEST_AUTH_MODE=false` | Only `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD` log in |
| ENV4 | `DATABASE_URL` set to PostgreSQL | App connects to PostgreSQL |
| ENV5 | `DATABASE_URL` unset | App raises `RuntimeError` at startup |
| ENV6 | `alembic upgrade head` on fresh DB | All tables created successfully |

---

## Administrators

| # | Action | Expected Result |
|---|--------|-----------------|
| U1 | Create a second administrator | New account can log in separately |
| U2 | Open all manager sections as Admin 2 | Same access as Admin 1 |
| U3 | Reset an administrator password | Old sessions are invalidated |
| U4 | Disable an administrator | Account can no longer log in |
| U5 | Disable the last active administrator | Request is rejected |

---

## Private Client Delivery

| # | Action | Expected Result |
|---|--------|-----------------|
| CG1 | Create collection without a code/PIN | Unique code and PIN are generated and shown once |
| CG2 | Upload valid photos | Photos appear in the private collection only |
| CG3 | Open collection with wrong PIN | Access is rejected |
| CG4 | Open collection with email and correct PIN | Client first sees the selected full-screen cover, then chooses View Gallery to see only that collection |
| CG5 | Search inside collection | Caption/filename results are filtered |
| CG6 | Download one photo | Original downloads and activity is logged |
| CG7 | Download all | ZIP downloads and activity is logged |
| CG8 | Leave a photo comment | Comment appears in gallery and admin activity |
| CG9 | Lock or expire collection | Client access is denied |
| CG10 | Reset collection PIN | Old PIN stops working |
| CG11 | Manager opens Preview Gallery | Gallery layout opens without a PIN and creates no visitor record |
| CG12 | Manager selects Set Cover on a photo | Selected photo becomes the collection card, unlock background, and gallery hero |
| CG13 | Paste the correct PIN with surrounding spaces | Access succeeds after safe whitespace normalization |
| CG14 | Open a photo in the collection | Full-screen preview opens with previous/next controls |
| CG15 | Upload more than one batch | All batches remain in the same collection; up to 25 or 100 MB are accepted per batch |
| CG16 | Like, unlike, and re-like a photo | Heart state and count update; manager activity shows the visitor and photo once |
| CG17 | Download one photo in Original, High, and Web quality | Original is unchanged; High is at most 3000px; Web is at most 1600px |
| CG18 | Download all with a selected quality | ZIP contains every available photo at the selected quality and activity records that quality |
| CG19 | Copy Client Share Link and open it in a private browser | The collection PIN page opens directly; the correct PIN leads only to that collection |
| CG20 | Use a portrait photo as the cover on desktop and mobile | The complete photo stays visible over the full-width background without cropping the face |
| CG21 | Use Copy or WhatsApp on a manager collection card | The client-specific PIN link is copied or opened for sharing |
| CG22 | Choose and save a custom PIN | The manager-chosen PIN unlocks the collection and the previous PIN stops working |
| CG23 | Choose Test PIN as Client while logged in as manager | The PIN screen, cover introduction, and full client interaction flow open without logging out |
| CG24 | View the client photo grid and lightbox | Photo numbers, captions, and filenames stay hidden; downloaded files retain their names |
| CG25 | Download a photo as a client | A red manager bell badge appears and the alert shows client, collection, quality, and time |
| CG26 | Mark one or all download alerts as read | The unread count updates for both administrators |
| CG27 | Select several photos and choose Delete Selected | Only selected photos and stored files are removed; a deleted cover is replaced when another photo remains |
| CG28 | Submit the correct PIN and revisit the private link | The full-screen collection cover appears before the photo grid without asking for the PIN again |
| CG29 | Open Client Delivery and select a collection | The visual collection library opens a cover-led workspace with Highlights, Add Photos, share, settings, activity, and bulk controls |

---

## Operations Additions

| # | Action | Expected Result |
|---|--------|-----------------|
| O1 | Type a custom income category | Custom text is saved |
| O2 | Type a custom expense category | Custom text is saved |
| O3 | Add pending expense | It appears above paid expenses |
| O4 | Link expense to asset | Expense total appears on that asset |
| O5 | Add unpaid and paid customers | Unpaid customer appears first |
| O6 | Add customer venue/location | Location appears in customer list |
| O7 | Edit service category/icon | Services page and booking forms update |
| O8 | Open committee inquiry | WhatsApp targets `0759 189 861` |
