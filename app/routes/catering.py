from flask import Blueprint, render_template

catering_bp = Blueprint("catering", __name__)


@catering_bp.route("/catering")
def catering():
    return render_template("catering.html")
