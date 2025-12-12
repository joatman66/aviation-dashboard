import os
from flask import Flask

def create_app():
    app = Flask(__name__)

    # Load ETA / Talon config from environment, with sensible defaults
    app.config.from_mapping(
        ETA_BASE_URL=os.getenv("ETA_BASE_URL", "https://apps3.talonsystems.com/tseta/servlet/Talonws"),
        ETA_CUSTOMER_CODE=os.getenv("ETA_CUSTOMER_CODE", ""),
        ETA_ACCESS_CODE=os.getenv("ETA_ACCESS_CODE", ""),
        ETA_USERNAME=os.getenv("ETA_USERNAME", ""),
        ETA_LOCATION=os.getenv("ETA_LOCATION", ""),
    )

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
