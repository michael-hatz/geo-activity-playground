import functools

from geo_activity_playground.core.activities import ActivityRepository
from geo_activity_playground.explorer.converters import get_tile_history
from geo_activity_playground.explorer.grid_file import get_border_tiles
from geo_activity_playground.explorer.grid_file import get_explored_geojson
from geo_activity_playground.explorer.grid_file import get_explored_tiles
from geo_activity_playground.explorer.grid_file import get_three_color_tiles
from geo_activity_playground.explorer.grid_file import make_grid_file_geojson
from geo_activity_playground.explorer.grid_file import make_grid_file_gpx


class ExplorerController:
    def __init__(self, repository: ActivityRepository) -> None:
        self._repository = repository

    @functools.cache
    def render(self) -> dict:
        tiles = get_tile_history(self._repository)

        explored_geojson = get_three_color_tiles(tiles, self._repository)

        points = get_border_tiles(tiles)
        missing_tiles_geojson = make_grid_file_geojson(points, "missing_tiles")
        make_grid_file_gpx(points, "missing_tiles")

        points = get_explored_tiles(tiles)
        explored_tiles_geojson = make_grid_file_geojson(points, "explored")
        make_grid_file_gpx(points, "explored")

        return {
            "explored_geojson": explored_geojson,
            "missing_tiles_geojson": missing_tiles_geojson,
        }