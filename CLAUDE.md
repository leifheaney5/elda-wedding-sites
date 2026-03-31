# CLAUDE.md — ELDA Wedding Sites Wedding Website

## Project Overview
Full-stack wedding services website for **ELDA Wedding Sites** located in
Your City, State (123 Example Avenue Suite 100). This replaces the legacy Squarespace site at
https://www.eldaweddingsites.com/ with a custom, modular, self-hosted application.

---

## Tech Stack

| Layer         | Technology                                      |
|---------------|-------------------------------------------------|
| Backend       | Python 3.11+ / Flask 3.x                        |
| ORM           | SQLAlchemy + Flask-SQLAlchemy                   |
| Migrations    | Flask-Migrate (Alembic)                         |
| Auth          | Flask-Login + Werkzeug password hashing         |
| Templates     | Jinja2 (server-rendered)                        |
| CSS Framework | Tailwind CSS v3 (CDN in dev, built in prod)     |
| JS            | Alpine.js v3 (reactivity), Vanilla JS           |
| Database      | SQLite (dev) / PostgreSQL (prod)                |
| Email         | Flask-Mail (SMTP)                               |
| Forms         | Flask-WTF + WTForms                             |
| Payments      | Stripe (planned integration)                    |
| Hosting       | TBD (Render / Railway / VPS)                    |

---

## Project Structure

```
elda-wedding-sites/
├── CLAUDE.md                   ← You are here
├── README.md
├── .gitignore
├── .env.example                ← Copy to .env and fill values
├── requirements.txt
├── run.py                      ← Dev entry point
├── config.py                   ← All configuration classes
│
├── app/
│   ├── __init__.py             ← Application factory (create_app)
│   │
│   ├── models/                 ← SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── admin_user.py       ← Admin/staff accounts
│   │   ├── contact.py          ← Contact form submissions
│   │   ├── booking.py          ← Wedding booking requests
│   │   └── payment.py          ← Payment records (Stripe)
│   │
│   ├── routes/                 ← Flask Blueprints (one per nav section)
│   │   ├── __init__.py
│   │   ├── main.py             ← Home page
│   │   ├── packages.py         ← Ceremony Packages folder + sub-pages
│   │   ├── venue.py            ← Venue folder + sub-pages
│   │   ├── florals.py          ← ELDA Florals stand-alone
│   │   ├── catering.py         ← Catering Menus stand-alone
│   │   ├── contact.py          ← Contact Us + form handling
│   │   ├── booking.py          ← Book Your Wedding funnel
│   │   ├── about.py            ← About folder + sub-pages
│   │   └── admin.py            ← Intranet / admin dashboard
│   │
│   ├── templates/              ← Jinja2 HTML templates
│   │   ├── base.html           ← Site-wide layout (nav, footer)
│   │   ├── home.html
│   │   ├── packages/
│   │   │   ├── index.html      ← Packages landing/folder page
│   │   │   ├── elopement.html
│   │   │   ├── circle_of_love.html
│   │   │   ├── ocean_city.html
│   │   │   └── sail_away.html
│   │   ├── venue/
│   │   │   ├── index.html      ← Venue landing/folder page
│   │   │   ├── coastal_59.html
│   │   │   ├── intimate_dinner.html
│   │   │   └── gallery.html
│   │   ├── florals.html
│   │   ├── catering.html
│   │   ├── contact.html
│   │   ├── booking.html
│   │   ├── about/
│   │   │   ├── index.html
│   │   │   ├── faq.html
│   │   │   ├── terms.html
│   │   │   ├── privacy.html
│   │   │   ├── studio_40.html
│   │   │   ├── portfolio.html
│   │   │   └── invitation_etiquette.html
│   │   ├── admin/
│   │   │   ├── base.html       ← Admin layout (sidebar nav)
│   │   │   ├── login.html
│   │   │   ├── dashboard.html
│   │   │   ├── contacts.html
│   │   │   ├── bookings.html
│   │   │   ├── payments.html
│   │   │   └── users.html
│   │   └── components/
│   │       ├── navbar.html
│   │       ├── footer.html
│   │       ├── hero.html
│   │       ├── cta_banner.html
│   │       └── contact_form.html
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css        ← Custom styles + Tailwind overrides
│   │   │   ├── admin.css       ← Admin-specific styles
│   │   │   └── components/     ← Per-component CSS if needed
│   │   ├── js/
│   │   │   ├── main.js         ← Global JS (nav, animations)
│   │   │   ├── booking.js      ← Booking form logic
│   │   │   ├── gallery.js      ← Lightbox / gallery
│   │   │   └── admin.js        ← Admin dashboard JS
│   │   └── images/             ← Organized by section
│   │       ├── logo/
│   │       ├── hero/
│   │       ├── gallery/
│   │       ├── packages/
│   │       ├── venue/
│   │       └── florals/
│   │
│   └── utils/
│       ├── __init__.py
│       ├── email.py            ← Flask-Mail helpers
│       ├── auth.py             ← Login decorators / helpers
│       └── stripe_helpers.py   ← Stripe webhook + payment helpers
│
└── migrations/                 ← Auto-generated by Flask-Migrate
```

---

## Site Architecture (Nav Map)

```
Home
├─ Ceremony Packages  (folder page)
│  ├─ Elopement Ceremony Package
│  ├─ Circle of Love Package
│  ├─ Your City Beach Package
│  └─ Sail Away & Say I Do
├─ Venue  (folder page)
│  ├─ Coastal 59 Venue
│  ├─ 2-Hour Intimate Dinner Package
│  └─ Coastal 59 Venue Gallery
├─ ELDA Florals  (stand-alone)
├─ Catering Menus  (stand-alone)
├─ Contact Us  (stand-alone + form CTA)
├─ Book Your Wedding  (booking funnel)
└─ About  (folder page)
   ├─ About
   ├─ FAQ
   ├─ Terms and Services
   ├─ Website Privacy Policy
   ├─ Studio 40
   ├─ Portfolio
   └─ Invitation Etiquette

/admin  (protected — Flask-Login required)
   ├─ Dashboard
   ├─ Contact Submissions
   ├─ Bookings
   ├─ Payments
   └─ Admin Users
```

---

## URL Routes

| URL                                    | Blueprint      | Template                          |
|----------------------------------------|----------------|-----------------------------------|
| `/`                                    | main           | home.html                         |
| `/packages/`                           | packages       | packages/index.html               |
| `/packages/elopement`                  | packages       | packages/elopement.html           |
| `/packages/circle-of-love`             | packages       | packages/circle_of_love.html      |
| `/packages/ocean-city`                 | packages       | packages/ocean_city.html          |
| `/packages/sail-away`                  | packages       | packages/sail_away.html           |
| `/venue/`                              | venue          | venue/index.html                  |
| `/venue/coastal-59`                    | venue          | venue/coastal_59.html             |
| `/venue/intimate-dinner`               | venue          | venue/intimate_dinner.html        |
| `/venue/gallery`                       | venue          | venue/gallery.html                |
| `/florals`                             | florals        | florals.html                      |
| `/catering`                            | catering       | catering.html                     |
| `/contact`                             | contact        | contact.html                      |
| `/book`                                | booking        | booking.html                      |
| `/about/`                              | about          | about/index.html                  |
| `/about/faq`                           | about          | about/faq.html                    |
| `/about/terms`                         | about          | about/terms.html                  |
| `/about/privacy`                       | about          | about/privacy.html                |
| `/about/studio-40`                     | about          | about/studio_40.html              |
| `/about/portfolio`                     | about          | about/portfolio.html              |
| `/about/invitation-etiquette`          | about          | about/invitation_etiquette.html   |
| `/admin/`                              | admin          | admin/dashboard.html              |
| `/admin/login`                         | admin          | admin/login.html                  |
| `/admin/contacts`                      | admin          | admin/contacts.html               |
| `/admin/bookings`                      | admin          | admin/bookings.html               |
| `/admin/payments`                      | admin          | admin/payments.html               |
| `/admin/users`                         | admin          | admin/users.html                  |

---

## Database Models

### AdminUser
- id, email, password_hash, name, role (owner/staff), created_at, last_login

### ContactSubmission
- id, name, email, phone, message, submitted_at, is_read, notes

### BookingRequest
- id, couple_name, email, phone, wedding_date, package_id, guest_count,
  venue_preference, message, status (new/confirmed/cancelled), submitted_at, notes

### Payment
- id, booking_id (FK), stripe_payment_intent_id, amount_cents, currency,
  status (pending/paid/refunded), paid_at, description

---

## Development Setup

```bash
# 1. Clone and enter repo
git clone https://github.com/leifheaney5/elda-wedding-sites.git
cd elda-wedding-sites

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your values

# 5. Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 6. Create first admin user
flask create-admin

# 7. Run dev server
python run.py
# Site: http://localhost:5000
# Admin: http://localhost:5000/admin
```

---

## Environment Variables (.env)

```
FLASK_ENV=development
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///bbb.db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your@email.com
CONTACT_RECIPIENT=admin@eldaweddingsites.com

STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## Design System

### Brand Colors (Tailwind custom config)
| Token           | Hex       | Usage                        |
|-----------------|-----------|------------------------------|
| `bbb-sand`      | `#F5EFE6` | Page backgrounds, cards      |
| `bbb-cream`     | `#FAF6F1` | Section backgrounds          |
| `bbb-teal`      | `#4A9B8E` | Primary CTA buttons, accents |
| `bbb-teal-dark` | `#2D7A6E` | Hover states                 |
| `bbb-navy`      | `#1A2E44` | Headings, footer background  |
| `bbb-coral`     | `#E07B6A` | Highlight accents, badges    |
| `bbb-gold`      | `#C9A96E` | Decorative elements          |
| `bbb-text`      | `#3D3D3D` | Body text                    |

### Typography
- **Headings**: Playfair Display (Google Fonts) — elegant serif
- **Body**: Lato or Inter — clean sans-serif
- **Accent/Script**: Great Vibes — romantic script for decorative use

---

## Key Conventions

- All blueprints registered with a URL prefix in `app/__init__.py`
- Templates extend `base.html` (public) or `admin/base.html` (admin)
- All form submissions are stored in the DB AND trigger an email notification
- Admin routes decorated with `@login_required` and `@admin_required`
- Static images go in `app/static/images/<section>/` — never inline base64
- CSS variables defined in `main.css` for brand colors; use Tailwind utilities
- Admin panel accessible at `/admin` — treat as separate "app within app"
- No client-side secrets; Stripe keys are server-side only
- All money values stored as integer cents (never floats)

---

## Deployment Notes (Future)

- Use `gunicorn` as WSGI server: `gunicorn "app:create_app()" -w 4`
- Set `FLASK_ENV=production` and `DATABASE_URL` to PostgreSQL
- Run `flask db upgrade` on deploy
- Serve static files via Nginx or CDN
- Configure SSL (Let's Encrypt / Cloudflare)
- Set all `.env` values as real environment variables on host

---

## Outstanding Items / Client Meeting Notes
_Add notes from client meetings here as they are collected._

- [ ] Confirm pricing for all packages
- [ ] Collect high-res photography assets
- [ ] Confirm booking calendar integration preference (Calendly / custom)
- [ ] Confirm payment schedule (deposit % / final balance timing)
- [ ] Confirm contact recipient email address
- [ ] Confirm Stripe account credentials
- [ ] Studio 40 — confirm relationship/description
- [ ] Confirm florals pricing and service offerings
- [ ] Confirm catering menu items and pricing
