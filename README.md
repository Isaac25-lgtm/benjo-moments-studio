<div align="center">

# 📸 Benjo Moments Studio

### *Professional Photography Business Management System*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7.svg)](https://render.com)

<img src="https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=800" alt="Benjo Moments Studio" width="600">

**A complete, modern web application for managing a photography business — from stunning portfolio showcase to comprehensive financial tracking.**

[Live Demo](#) • [Features](#-features) • [Quick Start](#-quick-start) • [Deployment](#-deployment) • [Admin Access](#-admin-access)

</div>

---

## ✨ Features

### 🌐 **Public Website**
- **Hero Slider** — Stunning fullscreen image carousel with Ken Burns effect
- **Portfolio Gallery** — Lightbox-enabled photo gallery with album filtering
- **Pricing Packages** — Beautiful, editable service packages display
- **Contact Form** — Client inquiry system with database storage
- **WhatsApp Integration** — Floating chat button for instant communication
- **Mobile Responsive** — Perfect experience on all devices

### 🔐 **Manager's Portal**
- **Dashboard** — Business overview with key metrics at a glance
- **Financial Management**
  - 💰 Income tracking
  - 📊 Expense management
  - 📄 Invoice generation
  - 📈 Financial reports

- **Website Management**
  - 🖼️ Gallery Manager — Upload and organize photos by album
  - 🏷️ Pricing Editor — Adjust packages without touching code
  - ⚙️ Website Settings — Update content, contact info, and more
  - 📬 Client Messages — View and manage inquiries

- **Business Tools**
  - 👥 Customer database
  - 📷 Asset tracking (cameras, equipment)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Local Development

```bash
# Clone the repository
git clone https://github.com/Isaac25-lgtm/benjo-moments-studio.git
cd benjo-moments-studio

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The server will start at: **http://127.0.0.1:5000**

---

## 🔑 Admin Access

Access the Manager's Portal at: `/admin/login`

**Default Credentials:**
| Field | Value |
|-------|-------|
| Email | `admin@benjomoments.com` |
| Password | `admin123` |

> ⚠️ **Important:** Change these credentials immediately in production by updating `config.py`

---

## 🌍 Deployment

### Deploy to Render (Recommended)

This project is configured for one-click deployment on Render.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Manual Deployment Steps:**

1. **Create a Render Account** at [render.com](https://render.com)

2. **Create New Web Service**
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration

3. **Configure Environment Variables** (auto-generated):
   - `SECRET_KEY` — Auto-generated secure key
   - `FLASK_ENV` — Set to `production`

4. **Add Persistent Disk** (already configured in render.yaml):
   - Mount path: `/data`
   - Size: 1GB (for database and uploads)

5. **Deploy!** — Render will build and deploy automatically

### Alternative: Manual Server Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn (production)
gunicorn app:create_app() --bind 0.0.0.0:8000 --workers 4
```

---

## 📁 Project Structure

```
benjo-moments-studio/
├── 📄 app.py              # Application entry point
├── 📄 config.py           # Configuration settings
├── 📄 database.py         # Database models & queries
├── 📄 admin.py            # Admin routes & logic
├── 📄 public.py           # Public website routes
├── 📄 auth.py             # Authentication system
├── 📄 requirements.txt    # Python dependencies
├── 📄 render.yaml         # Render deployment config
├── 📁 static/
│   ├── 📁 css/            # Stylesheets
│   ├── 📁 js/             # JavaScript files
│   └── 📁 uploads/        # User-uploaded images
└── 📁 templates/
    ├── 📁 admin/          # Admin panel templates
    ├── 📁 auth/           # Login templates
    └── 📁 public/         # Public website templates
```

---

## 🎨 Screenshots

<div align="center">

| Homepage | Gallery | Admin Dashboard |
|:--------:|:-------:|:---------------:|
| ![Homepage](https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=300) | ![Gallery](https://images.unsplash.com/photo-1519741497674-611481863552?w=300) | ![Admin](https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=300) |

</div>

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python 3.11, Flask 3.0 |
| **Database** | SQLite (file-based) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **UI Framework** | Custom CSS with modern animations |
| **Icons** | Font Awesome 6 |
| **Fonts** | Google Fonts (Manrope) |
| **Production Server** | Gunicorn |
| **Hosting** | Render |

---

## 🔧 Configuration

Edit `config.py` to customize:

```python
# Admin Credentials
DEFAULT_ADMIN_EMAIL = 'your-email@example.com'
DEFAULT_ADMIN_PASSWORD = 'secure-password'

# Security
SECRET_KEY = 'your-secret-key-here'

# File Uploads
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
```

---

## 📱 Features Showcase

### ✅ Lightbox Gallery
Click any photo to view fullscreen with navigation arrows and keyboard support.

### ✅ Scroll Animations
Beautiful fade-in effects as sections come into view.

### ✅ Dynamic Pricing
Edit packages directly from the admin panel — no code changes needed.

### ✅ Download Protection
Images are protected from right-click downloading.

### ✅ WhatsApp Integration
Floating button connects visitors directly to WhatsApp chat.

### ✅ Responsive Design
Perfect experience across desktop, tablet, and mobile devices.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Benjo Moments Studio**

- Website: [benjomoments.com](#)
- GitHub: [@Isaac25-lgtm](https://github.com/Isaac25-lgtm)

---

<div align="center">

**Made with ❤️ for photographers who want to focus on their craft, not code.**

⭐ Star this repo if you find it useful!

</div>
