from flask import Blueprint, render_template

florals_bp = Blueprint("florals", __name__)


@florals_bp.route("/florals")
def florals():
    return render_template("florals.html")
