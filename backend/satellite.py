from datetime import datetime, timezone


def satellite_layer_config() -> dict[str, str]:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {
        "name": "NASA GIBS MODIS Terra True Color",
        "url_template": (
            "https://gibs-a.earthdata.nasa.gov/wmts/epsg3857/best/"
            "MODIS_Terra_CorrectedReflectance_TrueColor/default/"
            f"{date}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg"
        ),
        "attribution": "NASA GIBS / Earthdata",
        "max_zoom": "9",
        "role": "visual satellite context layer; not used as a validated risk input",
    }
