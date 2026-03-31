from datetime import datetime
from urllib.parse import urljoin
from flask import Blueprint, render_template, Response, url_for, current_app

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("home.html")


@main_bp.route("/planning")
def planning_home():
    return render_template("planning_home.html")


@main_bp.route("/planning-guide")
def planning_guide():
    return render_template("planning_guide.html")


@main_bp.route("/vow-renewals")
def vow_renewals():
    return render_template("vow_renewals.html")


@main_bp.route("/nearby-attractions")
def nearby_attractions():
    return render_template("nearby_attractions.html")


@main_bp.route("/lookbook")
def lookbook():
    return render_template("lookbook.html")


@main_bp.route("/services")
def services_home():
    return render_template("services_home.html")


@main_bp.route("/portal")
def portal_home():
    return render_template("portal_home.html")


@main_bp.route("/sitemap.xml")
def sitemap():
    public_endpoints = [
        "main.home",
        "main.planning_guide",
        "main.planning_home",
        "main.vow_renewals",
        "main.nearby_attractions",
        "main.lookbook",
        "main.services_home",
        "main.portal_home",
        "packages.index",
        "packages.elopement",
        "packages.circle_of_love",
        "packages.ocean_city",
        "venue.index",
        "venue.coastal_59",
        "venue.intimate_dinner",
        "venue.gazebo_weddings",
        "venue.gallery",
        "florals.florals",
        "catering.catering",
        "booking.book",
        "booking.service_request",
        "contact.contact",
        "about.index",
        "about.faq",
        "about.portfolio",
        "about.invitation_etiquette",
        "about.terms",
        "about.privacy",
    ]
    service_types = ["package", "venue", "catering", "florals"]

    now_iso = datetime.utcnow().date().isoformat()
    site_url = current_app.config.get("SITE_URL", "").rstrip("/")
    urls = []
    for endpoint in public_endpoints:
        if endpoint == "booking.service_request":
            for request_type in service_types:
                path = url_for(endpoint, request_type=request_type, _external=False)
                urls.append(urljoin(f"{site_url}/", path.lstrip("/")) if site_url else url_for(endpoint, request_type=request_type, _external=True))
            continue
        path = url_for(endpoint, _external=False)
        urls.append(urljoin(f"{site_url}/", path.lstrip("/")) if site_url else url_for(endpoint, _external=True))

    xml_items = []
    for location in urls:
        xml_items.append(
            f"<url><loc>{location}</loc><lastmod>{now_iso}</lastmod><changefreq>weekly</changefreq></url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(xml_items)
        + "</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@main_bp.route("/robots.txt")
def robots():
    site_url = current_app.config.get("SITE_URL", "").rstrip("/")
    sitemap_url = f"{site_url}/sitemap.xml" if site_url else url_for("main.sitemap", _external=True)
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /client/",
            f"Sitemap: {sitemap_url}",
        ]
    )
    return Response(body, mimetype="text/plain")
