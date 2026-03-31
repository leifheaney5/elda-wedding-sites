from flask import Blueprint, render_template, redirect, url_for
from app.utils.faq_rag import get_faq_entries

about_bp = Blueprint("about", __name__)


@about_bp.route("/")
def index():
    return render_template("about/index.html")


@about_bp.route("/faq")
def faq():
    return render_template("about/faq.html", faqs=get_faq_entries())


@about_bp.route("/terms")
def terms():
    return render_template("about/terms.html")


@about_bp.route("/privacy")
def privacy():
    return render_template("about/privacy.html")


@about_bp.route("/creative-partner")
def studio_40():
    return redirect(url_for("about.index"), code=302)


@about_bp.route("/portfolio")
def portfolio():
    return render_template("about/portfolio.html")


@about_bp.route("/invitation-etiquette")
def invitation_etiquette():
    return render_template("about/invitation_etiquette.html")
