from collections import Counter
from flask import Blueprint, render_template, current_app
from . import eta_client

bp = Blueprint("main", __name__)


def get_aircraft_stub():
    return [
        {"tail": "N101SIU", "aircraft_type": "C172", "hobbs": 1234.5},
        {"tail": "N102SIU", "aircraft_type": "C172", "hobbs": 980.2},
    ]


def get_fleet():
    """
    One source of truth for the filtered fleet used everywhere.
    """
    try:
        aircraft_list = eta_client.get_aircraft_summary(current_app.config)
        error = None
    except Exception as exc:
        current_app.logger.exception("ETA aircraft summary failed; using stub. Error: %s", exc)
        aircraft_list = get_aircraft_stub()
        error = str(exc)

    aircraft_list = sorted(aircraft_list, key=lambda a: (a.get("tail") or ""))
    return aircraft_list, error


@bp.route("/")
def index():
    dashboards = [
        {"name": "Overview", "path": "/overview", "description": "At-a-glance fleet summary."},
        {"name": "Aircraft Status", "path": "/aircraft", "description": "Tail, aircraft type, Hobbs."},
    ]
    return render_template("index.html", dashboards=dashboards)


@bp.route("/overview")
def overview():
    aircraft_list, error = get_fleet()

    total_aircraft = len(aircraft_list)
    total_hobbs = sum(float(a.get("hobbs") or 0.0) for a in aircraft_list)

    type_counter = Counter((a.get("aircraft_type") or "—") for a in aircraft_list)
    type_breakdown = sorted(type_counter.items(), key=lambda x: x[0])

    sample_aircraft = aircraft_list[:12]

    return render_template(
        "overview.html",
        total_aircraft=total_aircraft,
        total_hobbs=total_hobbs,
        type_breakdown=type_breakdown,
        sample_aircraft=sample_aircraft,
        error=error,
    )


@bp.route("/aircraft")
def aircraft():
    aircraft_list, error = get_fleet()
    return render_template("aircraft.html", aircraft=aircraft_list, error=error)


@bp.route("/debug/aircraft-types")
def aircraft_types_debug():
    """
    Debug page shows raw types/counts from ETA (unfiltered).
    """
    try:
        aircraft_list = eta_client.get_aircraft_raw(current_app.config)
        error = None
    except Exception as exc:
        current_app.logger.exception("ETA raw aircraft fetch failed: %s", exc)
        aircraft_list = []
        error = str(exc)

    counts = Counter((a.get("aircraft_type") or "(blank)") for a in aircraft_list)
    type_counts = sorted(counts.items(), key=lambda x: x[0])

    return render_template("aircraft_types.html", type_counts=type_counts, error=error)
