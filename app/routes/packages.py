from flask import Blueprint, render_template

packages_bp = Blueprint("packages", __name__)

PACKAGES = {
    "package-a": {
        "title": "Ceremony Package A",
        "slug": "package-a",
        "template": "packages/elopement.html",
    },
    "package-b": {
        "title": "Ceremony Package B",
        "slug": "package-b",
        "template": "packages/circle_of_love.html",
    },
    "package-c": {
        "title": "Ceremony Package C",
        "slug": "package-c",
        "template": "packages/ocean_city.html",
    },
}


@packages_bp.route("/")
def index():
    return render_template("packages/index.html", packages=PACKAGES)


@packages_bp.route("/package-a")
def elopement():
    return render_template("packages/elopement.html", package=PACKAGES["package-a"])


@packages_bp.route("/package-b")
def circle_of_love():
    return render_template(
        "packages/circle_of_love.html", package=PACKAGES["package-b"]
    )


@packages_bp.route("/package-c")
def ocean_city():
    return render_template(
        "packages/ocean_city.html", package=PACKAGES["package-c"]
    )


