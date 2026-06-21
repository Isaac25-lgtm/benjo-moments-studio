"""Contextual instructions for the manager portal."""


PAGE_GUIDES = {
    "admin.dashboard": {
        "title": "Dashboard guide",
        "summary": "Use this page for a quick check of the business before opening detailed records.",
        "steps": (
            "Review unpaid expenses and pending client balances that need attention.",
            "Compare total income, expenses, and net profit for the current position.",
            "Check recent transactions, then open the matching section to add or correct details.",
        ),
        "note": "Dashboard figures come from Income, Expenses, Customers, Invoices, and Assets.",
    },
    "admin.income": {
        "title": "Income guide",
        "summary": "Record money received outside the automatic invoice-payment process.",
        "steps": (
            "Enter the date the money was received.",
            "Choose a category or type a clear custom category.",
            "Enter the amount and identify who paid and what the payment covered.",
            "Use Edit to correct a record; delete only when the entry should not exist.",
        ),
        "note": "Do not add income again after marking an invoice paid. The system creates it automatically.",
    },
    "admin.expenses": {
        "title": "Expenses guide",
        "summary": "Record paid costs and unpaid bills, including costs attached to studio assets.",
        "steps": (
            "Enter the date, category, amount, supplier, and a useful description.",
            "Set Pending for an unpaid bill, Paid for completed payment, or Cancelled when no longer owed.",
            "Choose a related asset when the cost is for equipment maintenance, purchase, or repair.",
            "Add the due date for pending bills and the paid date when payment is completed.",
        ),
        "note": "A linked expense is included in that asset's expense total. Pending expenses appear first.",
    },
    "admin.invoices": {
        "title": "Invoices guide",
        "summary": "Create charges for customers and settle them when payment is confirmed.",
        "steps": (
            "Create the customer first if they are not already in the customer list.",
            "Choose the customer and confirm the invoice number, date, and amount.",
            "Click Mark Paid only after receiving the payment.",
            "Confirm the customer balance and Income page after settlement.",
        ),
        "note": "Mark Paid updates the balance and creates one linked income record automatically.",
    },
    "admin.customers": {
        "title": "Customers guide",
        "summary": "Track each client, booking, location, total price, and remaining balance.",
        "steps": (
            "Enter the client's name, contact, service, and venue or location.",
            "Enter the full agreed price and the amount already paid.",
            "Follow up clients with unpaid balances, which are shown first.",
            "Use Edit when payment or booking details change.",
        ),
        "note": "Balance is total amount minus amount paid. Invoice settlement also updates it.",
    },
    "admin.assets": {
        "title": "Assets guide",
        "summary": "Maintain the inventory of cameras, lighting, computers, and other property.",
        "steps": (
            "Add the asset name, category, current value, and supplier.",
            "For repairs or other costs, open Expenses and select this asset.",
            "Return here to review its value and accumulated linked expenses.",
            "Edit details when the value or supplier information changes.",
        ),
        "note": "Record asset costs through Expenses so reports and asset totals stay consistent.",
    },
    "admin.reports": {
        "title": "Reports guide",
        "summary": "Review income, expenses, and profit for a selected period.",
        "steps": (
            "Choose the first and last date of the period.",
            "Click Generate Report to calculate totals.",
            "Compare the summary with the detailed rows below it.",
            "Correct wrong entries in Income or Expenses, then generate the report again.",
        ),
        "note": "Reports use the transaction dates inside the selected range.",
    },
    "admin_extended.client_collections": {
        "title": "Client delivery guide",
        "summary": "Create and find private collections before opening one to manage its photos.",
        "steps": (
            "Click New Collection and enter the event and client details.",
            "Use a custom code and PIN or let the system generate them.",
            "Copy the PIN from the success message immediately, then open the collection.",
            "Use Search and status filters to find active, locked, or expired collections.",
        ),
        "note": "Give every client a separate collection and PIN. PINs cannot be displayed again.",
    },
    "admin_extended.client_collection_detail": {
        "title": "Collection setup guide",
        "summary": "Prepare this collection, upload photos, and monitor client activity.",
        "steps": (
            "Use the left collection rail to open Add Photos, Client Share Link, Settings and PIN, or Client Activity.",
            "Choose Add Photos and upload up to 25 JPG, PNG, or WebP photos per batch; repeat as needed.",
            "Review the Highlights grid, select several photos when needed, and choose Delete Selected.",
            "Use the image control on a photo to make it the cover shown behind the PIN form and after login.",
            "Open Preview Gallery to check the layout and confirm that the full cover photo is framed correctly.",
            "Use Copy Link in Client Share Link and send it to the client, then send the PIN separately.",
            "Use Test PIN as Client to verify the PIN screen, cover introduction, and gallery without logging out.",
            "Open Settings and PIN to update client details, deactivate access, or replace the PIN.",
            "Open Client Activity to review visitors, likes, download qualities, and comments.",
        ),
        "note": "Deleting a collection permanently removes its photos and activity.",
    },
    "admin_extended.download_notifications": {
        "title": "Download alerts guide",
        "summary": "See who downloaded client photos and which quality they selected.",
        "steps": (
            "Check the red bell badge for the number of new client downloads.",
            "Open an alert to identify the client, collection, quality, and download time.",
            "Choose Collection when you need to inspect that client's full activity.",
            "Mark one alert as read, or use Mark All Read after reviewing the list.",
        ),
        "note": "Both administrators share the same alerts and read status.",
    },
    "admin.messages": {
        "title": "Messages guide",
        "summary": "Manage inquiries submitted through the public contact page.",
        "steps": (
            "Open unread messages and review the client's contact details and request.",
            "Reply using the supplied phone number or email address.",
            "Mark the message as read after it has been handled.",
            "Delete only messages that no longer need to be retained.",
        ),
        "note": "The unread count helps both administrators avoid overlooking inquiries.",
    },
    "admin.gallery_manager": {
        "title": "Public gallery guide",
        "summary": "Control portfolio photos visible to every visitor on the Gallery page.",
        "steps": (
            "Select the correct album and choose up to 25 photos per batch; repeat uploads as needed.",
            "Add a short caption that describes the work.",
            "Use Publish or Hide to control whether each photo appears publicly.",
            "Preview the public Gallery after making changes.",
        ),
        "note": "Public Gallery photos are separate from private Client Delivery collections.",
    },
    "admin_extended.services": {
        "title": "Services guide",
        "summary": "Organize professional services shown on the public Services page.",
        "steps": (
            "Create a category such as Social Events, Corporate, or Studio.",
            "Choose its name, icon, image, display order, and visibility.",
            "Add individual services inside the correct category.",
            "Save each change, then preview the public website.",
        ),
        "note": "Lower order numbers appear first. Hidden categories and services are not public.",
    },
    "admin.pricing": {
        "title": "Pricing guide",
        "summary": "Manage packages and prices offered on the public Pricing page.",
        "steps": (
            "Review package details and Active or Hidden status.",
            "Choose Add Package for a new offer or Edit for an existing one.",
            "Use Show or Hide to control visibility without deleting.",
            "Preview the website after changing prices.",
        ),
        "note": "Hide is safer than Delete for temporary or seasonal offers.",
    },
    "admin.pricing_form": {
        "title": "Package form guide",
        "summary": "Enter the information clients will see for this package.",
        "steps": (
            "Enter a clear package name, description, price, and price label.",
            "Separate package benefits with the vertical bar character: |.",
            "Choose an icon, display order, and whether it should be featured.",
            "Save, then confirm it on the Pricing list and public website.",
        ),
        "note": "Use an icon such as fa-camera. Lower order numbers appear first.",
    },
    "admin.website_settings": {
        "title": "Website settings guide",
        "summary": "Update public text, contacts, social links, and homepage images.",
        "steps": (
            "Review the site name, homepage headline, About text, and contacts.",
            "Use complete https:// social links and WhatsApp with country code.",
            "Click Save Changes before leaving the page.",
            "Upload hero images and use display order to choose which appears first.",
            "Preview the website and check the result.",
        ),
        "note": "Saved text changes appear immediately on the public website.",
    },
    "admin_extended.users": {
        "title": "Administrator guide",
        "summary": "Manage the people allowed to open the manager portal.",
        "steps": (
            "Create a separate administrator account for each manager.",
            "Use a unique email and strong password for every account.",
            "Deactivate an account immediately when access should end.",
            "Reset a password from the account controls when necessary.",
        ),
        "note": "Administrators have equal power. Never share one password between people.",
    },
    "admin.manager_guide": {
        "title": "Manager guide",
        "summary": "Use this page as the starting point for the complete business workflow.",
        "steps": (
            "Choose a workflow based on the job you are handling.",
            "Follow its links in order and use Page guide inside each window.",
            "Preview public changes before sharing them with clients.",
        ),
        "note": "Both administrators use one database, so saved changes are shared immediately.",
    },
}

PAGE_GUIDES["admin.add_pricing"] = PAGE_GUIDES["admin.pricing_form"]
PAGE_GUIDES["admin.edit_pricing"] = PAGE_GUIDES["admin.pricing_form"]


SYSTEM_WORKFLOWS = (
    {
        "icon": "fa-calendar-check", "title": "New client booking",
        "steps": (
            "Add the client with the service, total amount, deposit, and venue.",
            "Create an invoice when the client needs a formal charge record.",
            "Record separate receipts in Income only when they did not come from Mark Paid.",
        ),
        "links": (("Customers", "admin.customers"), ("Invoices", "admin.invoices"), ("Income", "admin.income")),
    },
    {
        "icon": "fa-lock", "title": "Deliver client photos",
        "steps": (
            "Create a separate collection and copy its PIN from the success message.",
            "Upload the finished photos, choose the cover, and preview the gallery.",
            "Copy the client link from the collection page and send the PIN separately.",
            "Monitor visitors, likes, comments, and download quality choices.",
        ),
        "links": (("Client Delivery", "admin_extended.client_collections"),),
    },
    {
        "icon": "fa-wallet", "title": "Pay a bill or asset cost",
        "steps": (
            "Enter unpaid bills as Pending expenses with a due date.",
            "Link equipment-related costs to the matching asset.",
            "Change the expense to Paid and add the paid date after payment.",
        ),
        "links": (("Expenses", "admin.expenses"), ("Assets", "admin.assets")),
    },
    {
        "icon": "fa-globe", "title": "Update the public website",
        "steps": (
            "Use Gallery Manager for public photos and Client Delivery for private work.",
            "Update services, prices, homepage text, contacts, and hero images.",
            "Open View Website and check every changed page.",
        ),
        "links": (("Gallery", "admin.gallery_manager"), ("Services", "admin_extended.services"), ("Pricing", "admin.pricing"), ("Settings", "admin.website_settings")),
    },
    {
        "icon": "fa-chart-line", "title": "Weekly or monthly review",
        "steps": (
            "Check the Dashboard for unpaid bills, balances, and recent activity.",
            "Generate a Report for the exact review period.",
            "Correct the original Income or Expense entry when a line is wrong.",
        ),
        "links": (("Dashboard", "admin.dashboard"), ("Reports", "admin.reports")),
    },
)


def get_page_guide(endpoint):
    return PAGE_GUIDES.get(endpoint)
