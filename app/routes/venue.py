from flask import Blueprint, render_template

venue_bp = Blueprint("venue", __name__)


@venue_bp.route("/")
def index():
    return render_template("venue/index.html")


@venue_bp.route("/option-a")
def coastal_59():
    return render_template("venue/coastal_59.html")


@venue_bp.route("/option-b")
def intimate_dinner():
    return render_template("venue/intimate_dinner.html")


@venue_bp.route("/gallery")
def gallery():
    return render_template("venue/gallery.html")


@venue_bp.route("/option-c")
def gazebo_weddings():
    return render_template("venue/gazebo_weddings.html")
