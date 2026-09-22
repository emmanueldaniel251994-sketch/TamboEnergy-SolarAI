from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alert import Alert
from app.models.solar_system import SolarSystem
from app.models.telemetry import Telemetry
from app.models.user import User
from app.security import get_current_user
from app.services.health_score import calculate_health_score


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # ALERT QUERY
    # ========================================================

    alert_query = db.query(Alert)

    # Customers should only see alerts belonging
    # to their own solar systems.
    if current_user.role == "customer":

        if current_user.customer_id is None:

            return {
                "total_alerts": 0,
                "open_alerts": 0,
                "acknowledged_alerts": 0,
                "resolved_alerts": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "high_alerts": 0,
                "medium_alerts": 0,
                "needs_review": 0,
                "total_solar_systems": 0,
                "system_health": [],
                "recent_alerts": [],
            }

        customer_system_ids = [
            system.id
            for system in (
                db.query(SolarSystem)
                .filter(
                    SolarSystem.customer_id
                    == current_user.customer_id
                )
                .all()
            )
        ]

        if not customer_system_ids:

            return {
                "total_alerts": 0,
                "open_alerts": 0,
                "acknowledged_alerts": 0,
                "resolved_alerts": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "high_alerts": 0,
                "medium_alerts": 0,
                "needs_review": 0,
                "total_solar_systems": 0,
                "system_health": [],
                "recent_alerts": [],
            }

        alert_query = alert_query.filter(
            Alert.solar_system_id.in_(
                customer_system_ids
            )
        )

    # ========================================================
    # ALERT COUNTS
    # ========================================================

    total_alerts = alert_query.count()

    open_alerts = (
        alert_query
        .filter(
            Alert.status == "open"
        )
        .count()
    )

    acknowledged_alerts = (
        alert_query
        .filter(
            Alert.status == "acknowledged"
        )
        .count()
    )

    resolved_alerts = (
        alert_query
        .filter(
            Alert.status == "resolved"
        )
        .count()
    )

    active_alerts = (
        alert_query
        .filter(
            Alert.status.in_(
                ["open", "acknowledged"]
            )
        )
        .count()
    )

    critical_alerts = (
        alert_query
        .filter(
            Alert.status.in_(
                ["open", "acknowledged"]
            ),
            Alert.severity == "critical",
        )
        .count()
    )

    high_alerts = (
        alert_query
        .filter(
            Alert.status.in_(
                ["open", "acknowledged"]
            ),
            Alert.severity == "high",
        )
        .count()
    )

    medium_alerts = (
        alert_query
        .filter(
            Alert.status.in_(
                ["open", "acknowledged"]
            ),
            Alert.severity == "medium",
        )
        .count()
    )

    needs_review = (
        alert_query
        .filter(
            Alert.status.in_(
                ["open", "acknowledged"]
            ),
            Alert.needs_review == 1,
        )
        .count()
    )

    # ========================================================
    # RECENT ALERTS
    # ========================================================

    recent_alert_records = (
        alert_query
        .order_by(
            Alert.created_at.desc()
        )
        .limit(5)
        .all()
    )

    recent_alerts = []

    for alert in recent_alert_records:

        recent_alerts.append({
            "id": alert.id,
            "solar_system_id": alert.solar_system_id,
            "telemetry_id": alert.telemetry_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "status": alert.status,
            "needs_review": alert.needs_review,
            "created_at": alert.created_at,
        })

    # ========================================================
    # SOLAR SYSTEM QUERY
    # ========================================================

    system_query = db.query(SolarSystem)

    if current_user.role == "customer":

        system_query = system_query.filter(
            SolarSystem.customer_id
            == current_user.customer_id
        )

    systems = system_query.all()

    # ========================================================
    # SYSTEM HEALTH
    # ========================================================

    system_health = []

    for system in systems:

        latest_telemetry = (
            db.query(Telemetry)
            .filter(
                Telemetry.solar_system_id
                == system.id
            )
            .order_by(
                Telemetry.created_at.desc()
            )
            .first()
        )

        if latest_telemetry:

            health = calculate_health_score(
                status=latest_telemetry.status,
                battery_soc=latest_telemetry.battery_soc,
                temperature=latest_telemetry.temperature,
                fault_type=latest_telemetry.fault_type,
                final_diagnosis=latest_telemetry.final_diagnosis,
                needs_review=latest_telemetry.needs_review,
            )

            system_health.append({
                "solar_system_id":
                    system.id,

                "status":
                    latest_telemetry.status,

                "battery_soc":
                    latest_telemetry.battery_soc,

                "battery_voltage":
                    latest_telemetry.battery_voltage,

                "pv_power":
                    latest_telemetry.pv_power,

                "load_power":
                    latest_telemetry.load_power,

                "temperature":
                    latest_telemetry.temperature,

                "fault_type":
                    latest_telemetry.fault_type,

                "final_diagnosis":
                    latest_telemetry.final_diagnosis,

                "ml_confidence":
                    latest_telemetry.ml_confidence,

                "needs_review":
                    latest_telemetry.needs_review,

                "health_score":
                    health["score"],

                "health_status":
                    health["health_status"],

                "last_update":
                    latest_telemetry.created_at,
            })

        else:

            system_health.append({
                "solar_system_id": system.id,
                "status": "no_data",
                "battery_soc": None,
                "battery_voltage": None,
                "pv_power": None,
                "load_power": None,
                "temperature": None,
                "fault_type": None,
                "final_diagnosis": None,
                "ml_confidence": None,
                "needs_review": 0,
                "health_score": None,
                "health_status": "no_data",
                "last_update": None,
            })

    # ========================================================
    # DASHBOARD SUMMARY RESPONSE
    # ========================================================

    return {
        "total_alerts":
            total_alerts,

        "open_alerts":
            open_alerts,

        "acknowledged_alerts":
            acknowledged_alerts,

        "resolved_alerts":
            resolved_alerts,

        "active_alerts":
            active_alerts,

        "critical_alerts":
            critical_alerts,

        "high_alerts":
            high_alerts,

        "medium_alerts":
            medium_alerts,

        "needs_review":
            needs_review,

        "total_solar_systems":
            len(systems),

        "system_health":
            system_health,

        "recent_alerts":
            recent_alerts,
    }


# ============================================================
# HISTORICAL TELEMETRY ANALYTICS
# ============================================================

@router.get("/analytics/{solar_system_id}")
def get_system_analytics(
    solar_system_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # CHECK SOLAR SYSTEM
    # ========================================================

    solar_system = (
        db.query(SolarSystem)
        .filter(
            SolarSystem.id
            == solar_system_id
        )
        .first()
    )

    if not solar_system:

        raise HTTPException(
            status_code=404,
            detail="Solar system not found",
        )

    # ========================================================
    # CUSTOMER ACCESS CONTROL
    # ========================================================

    if current_user.role == "customer":

        if (
            current_user.customer_id is None
            or solar_system.customer_id
            != current_user.customer_id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You do not have permission "
                    "to access this solar system"
                ),
            )

    # ========================================================
    # SAFE RECORD LIMIT
    # ========================================================

    limit = max(
        1,
        min(limit, 500)
    )

    # ========================================================
    # GET TELEMETRY HISTORY
    # ========================================================

    records = (
        db.query(Telemetry)
        .filter(
            Telemetry.solar_system_id
            == solar_system_id
        )
        .order_by(
            Telemetry.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    # Frontend charts should receive
    # oldest data first and newest data last.
    records.reverse()

    # ========================================================
    # BUILD TELEMETRY DATA
    # ========================================================

    data = []

    for record in records:

        data.append({
            "telemetry_id":
                record.id,

            "timestamp":
                record.created_at,

            "pv_voltage":
                record.pv_voltage,

            "pv_current":
                record.pv_current,

            "pv_power":
                record.pv_power,

            "battery_voltage":
                record.battery_voltage,

            "battery_current":
                record.battery_current,

            "battery_soc":
                record.battery_soc,

            "load_power":
                record.load_power,

            "temperature":
                record.temperature,

            "status":
                record.status,

            "fault_type":
                record.fault_type,

            "fault_severity":
                record.fault_severity,

            "final_diagnosis":
                record.final_diagnosis,

            "ml_prediction":
                record.ml_prediction,

            "ml_confidence":
                record.ml_confidence,

            "needs_review":
                record.needs_review,
        })

    # ========================================================
    # VALUES FOR PERFORMANCE ANALYTICS
    # ========================================================

    pv_values = [
        record.pv_power
        for record in records
        if record.pv_power is not None
    ]

    load_values = [
        record.load_power
        for record in records
        if record.load_power is not None
    ]

    battery_soc_values = [
        record.battery_soc
        for record in records
        if record.battery_soc is not None
    ]

    temperature_values = [
        record.temperature
        for record in records
        if record.temperature is not None
    ]

    # ========================================================
    # STATUS COUNTS
    # ========================================================
    #
    # IMPORTANT:
    # Each telemetry record belongs to only ONE
    # status category.
    #
    # Therefore:
    #
    # fault_count
    # + warning_count
    # + normal_count
    # should equal record_count.
    # ========================================================

    fault_records = [
        record
        for record in records
        if record.status == "fault"
    ]

    warning_records = [
        record
        for record in records
        if record.status == "warning"
    ]

    normal_records = [
        record
        for record in records
        if record.status == "normal"
    ]

    review_records = [
        record
        for record in records
        if record.needs_review == 1
    ]

    # ========================================================
    # AVERAGE HELPER
    # ========================================================

    def average(values):

        if not values:
            return None

        return round(
            sum(values) / len(values),
            2
        )

    # ========================================================
    # PERFORMANCE ANALYTICS
    # ========================================================

    analytics = {

        "average_pv_power":
            average(pv_values),

        "peak_pv_power":
            round(
                max(pv_values),
                2
            )
            if pv_values
            else None,

        "average_load_power":
            average(load_values),

        "peak_load_power":
            round(
                max(load_values),
                2
            )
            if load_values
            else None,

        "average_battery_soc":
            average(
                battery_soc_values
            ),

        "minimum_battery_soc":
            round(
                min(battery_soc_values),
                2
            )
            if battery_soc_values
            else None,

        "maximum_battery_soc":
            round(
                max(battery_soc_values),
                2
            )
            if battery_soc_values
            else None,

        "average_temperature":
            average(
                temperature_values
            ),

        "maximum_temperature":
            round(
                max(temperature_values),
                2
            )
            if temperature_values
            else None,

        "fault_count":
            len(fault_records),

        "warning_count":
            len(warning_records),

        "normal_count":
            len(normal_records),

        "needs_review_count":
            len(review_records),
    }

    # ========================================================
    # FINAL ANALYTICS RESPONSE
    # ========================================================

    return {
        "solar_system_id":
            solar_system_id,

        "record_count":
            len(data),

        "analytics":
            analytics,

        "data":
            data,
    }