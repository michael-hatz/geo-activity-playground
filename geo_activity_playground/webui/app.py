import datetime
import importlib
import json
import os
import pathlib
import secrets
import shutil
import urllib.parse

from flask import Flask
from flask import request
from flask_alembic import Alembic

from ..core.activities import ActivityRepository
from ..core.config import ConfigAccessor
from ..core.config import import_old_config
from ..core.config import import_old_strava_config
from ..core.datamodel import DB
from ..core.heart_rate import HeartRateZoneComputer
from ..core.raster_map import GrayscaleImageTransform
from ..core.raster_map import IdentityImageTransform
from ..core.raster_map import PastelImageTransform
from ..core.raster_map import TileGetter
from ..explorer.tile_visits import TileVisitAccessor
from .authenticator import Authenticator
from .blueprints.activity_blueprint import make_activity_blueprint
from .blueprints.auth_blueprint import make_auth_blueprint
from .blueprints.bubble_chart_blueprint import make_bubble_chart_blueprint
from .blueprints.eddington_blueprint import register_eddington_blueprint
from .blueprints.entry_views import register_entry_views
from .blueprints.equipment_blueprint import make_equipment_blueprint
from .blueprints.heatmap_blueprint import make_heatmap_blueprint
from .blueprints.search_blueprint import make_search_blueprint
from .blueprints.square_planner_blueprint import make_square_planner_blueprint
from .blueprints.summary_blueprint import make_summary_blueprint
from .blueprints.tile_blueprint import make_tile_blueprint
from .blueprints.upload_blueprint import make_upload_blueprint
from .blueprints.upload_blueprint import scan_for_activities
from .calendar.blueprint import make_calendar_blueprint
from .calendar.controller import CalendarController
from .explorer.blueprint import make_explorer_blueprint
from .explorer.controller import ExplorerController
from .flasher import FlaskFlasher
from .search_util import SearchQueryHistory
from .settings.blueprint import make_settings_blueprint


def get_secret_key():
    secret_file = pathlib.Path("Cache/flask-secret.json")
    if secret_file.exists():
        with open(secret_file) as f:
            secret = json.load(f)
    else:
        secret = secrets.token_hex()
        with open(secret_file, "w") as f:
            json.dump(secret, f)
    return secret


def web_ui_main(
    basedir: pathlib.Path,
    skip_reload: bool,
    host: str,
    port: int,
) -> None:
    os.chdir(basedir)

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{basedir.absolute()}/database.sqlite"
    )
    app.config["ALEMBIC"] = {"script_location": "../alembic/versions"}
    DB.init_app(app)

    alembic = Alembic()
    alembic.init_app(app)

    with app.app_context():
        alembic.upgrade()
        DB.session.commit()
        # DB.create_all()

    repository = ActivityRepository()
    tile_visit_accessor = TileVisitAccessor()
    config_accessor = ConfigAccessor()
    import_old_config(config_accessor)
    import_old_strava_config(config_accessor)

    if not skip_reload:
        with app.app_context():
            scan_for_activities(repository, tile_visit_accessor, config_accessor())

    app.config["UPLOAD_FOLDER"] = "Activities"
    app.secret_key = get_secret_key()

    @app.template_filter()
    def dt(value: datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    @app.template_filter()
    def td(v: datetime.timedelta):
        seconds = v.total_seconds()
        h = int(seconds // 3600)
        m = int(seconds // 60 % 60)
        s = int(seconds // 1 % 60)
        return f"{h}:{m:02d}:{s:02d}"

    authenticator = Authenticator(config_accessor())
    search_query_history = SearchQueryHistory(config_accessor, authenticator)
    config = config_accessor()
    calendar_controller = CalendarController(repository)
    explorer_controller = ExplorerController(
        repository, tile_visit_accessor, config_accessor
    )
    tile_getter = TileGetter(config.map_tile_url)
    image_transforms = {
        "color": IdentityImageTransform(),
        "grayscale": GrayscaleImageTransform(),
        "pastel": PastelImageTransform(),
    }
    flasher = FlaskFlasher()
    heart_rate_zone_computer = HeartRateZoneComputer(config)

    register_entry_views(app, repository, config)

    blueprints = {
        "/activity": make_activity_blueprint(
            repository,
            authenticator,
            tile_visit_accessor,
            config,
            heart_rate_zone_computer,
        ),
        "/auth": make_auth_blueprint(authenticator),
        "/bubble-chart": make_bubble_chart_blueprint(repository),
        "/calendar": make_calendar_blueprint(calendar_controller),
        "/eddington": register_eddington_blueprint(repository, search_query_history),
        "/equipment": make_equipment_blueprint(repository, config),
        "/explorer": make_explorer_blueprint(explorer_controller, authenticator),
        "/heatmap": make_heatmap_blueprint(
            repository, tile_visit_accessor, config_accessor(), search_query_history
        ),
        "/settings": make_settings_blueprint(config_accessor, authenticator, flasher),
        "/square-planner": make_square_planner_blueprint(tile_visit_accessor),
        "/search": make_search_blueprint(
            repository, search_query_history, authenticator, config_accessor
        ),
        "/summary": make_summary_blueprint(repository, config, search_query_history),
        "/tile": make_tile_blueprint(image_transforms, tile_getter),
        "/upload": make_upload_blueprint(
            repository, tile_visit_accessor, config_accessor(), authenticator
        ),
    }

    for url_prefix, blueprint in blueprints.items():
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    base_dir = pathlib.Path("Open Street Map Tiles")
    dir_for_source = base_dir / urllib.parse.quote_plus(config_accessor().map_tile_url)
    if base_dir.exists() and not dir_for_source.exists():
        subdirs = base_dir.glob("*")
        dir_for_source.mkdir()
        for subdir in subdirs:
            shutil.move(subdir, dir_for_source)

    @app.context_processor
    def inject_global_variables() -> dict:
        variables = {
            "version": _try_get_version(),
            "num_activities": len(repository),
            "map_tile_attribution": config_accessor().map_tile_attribution,
            "search_query_favorites": search_query_history.prepare_favorites(),
            "search_query_last": search_query_history.prepare_last(),
            "request_url": urllib.parse.quote_plus(request.url),
        }
        if len(repository):
            variables["equipments_avail"] = sorted(
                repository.meta["equipment"].unique()
            )
            variables["kinds_avail"] = sorted(repository.meta["kind"].unique())
        return variables

    app.run(host=host, port=port)


def _try_get_version():
    try:
        return importlib.metadata.version("geo-activity-playground")
    except importlib.metadata.PackageNotFoundError:
        pass
