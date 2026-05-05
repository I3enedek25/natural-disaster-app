from __future__ import annotations

import pytest

from disaster_app.data_loader import extract_centroid, normalize_events


def test_extract_centroid_from_nested_polygon_coordinates() -> None:
    coordinates = [[[10.0, 20.0], [12.0, 22.0], [14.0, 24.0], [10.0, 20.0]]]
    centroid = extract_centroid(coordinates)
    assert centroid is not None
    lon, lat = centroid
    assert lon == pytest.approx(11.5)
    assert lat == pytest.approx(21.5)


def test_normalize_events_handles_point_geometry() -> None:
    events = [
        {
            "id": "EONET_TEST_1",
            "title": "Sample Earthquake",
            "closed": "2024-01-02T00:00:00Z",
            "geometry": [
                {
                    "date": "2024-01-01T00:00:00Z",
                    "coordinates": [19.0, 47.0],
                    "magnitudeValue": 5.2,
                    "magnitudeUnit": "Mw",
                }
            ],
        }
    ]

    frame = normalize_events(events, category_id="earthquakes", disaster_label="Földrengések")
    assert len(frame) == 1
    assert frame.loc[0, "event_id"] == "EONET_TEST_1"
    assert frame.loc[0, "event_title"] == "Sample Earthquake"
    assert frame.loc[0, "lon"] == pytest.approx(19.0)
    assert frame.loc[0, "lat"] == pytest.approx(47.0)
    assert frame.loc[0, "disaster_label"] == "Földrengések"

