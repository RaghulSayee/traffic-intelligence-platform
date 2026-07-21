from __future__ import annotations

import cv2
import numpy as np

from app.pipelines.base import VideoFrame
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)
from app.reasoning.traffic_light_temporal import (
    StableTrafficLightSnapshot,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.scene.geometry import (
    normalized_polygon_to_pixels,
)


STATE_COLORS = {
    TrafficLightState.RED: (
        0,
        0,
        255,
    ),
    TrafficLightState.YELLOW: (
        0,
        255,
        255,
    ),
    TrafficLightState.GREEN: (
        0,
        255,
        0,
    ),
    TrafficLightState.UNKNOWN: (
        180,
        180,
        180,
    ),
}


def annotate_traffic_light_states(
    frame: VideoFrame,
    *,
    scene: CameraSceneConfiguration | None,
    states: tuple[
        StableTrafficLightSnapshot,
        ...,
    ],
) -> VideoFrame:
    """Draw stable traffic-light states over configured regions."""

    annotated = frame.copy()

    if scene is None or not states:
        return annotated

    regions_by_id = {region.region_id: region for region in scene.traffic_light_regions}

    image_height, image_width = annotated.shape[:2]

    for state in states:
        region = regions_by_id.get(state.region_id)

        if region is None:
            continue

        polygon = normalized_polygon_to_pixels(
            region.polygon,
            image_width=image_width,
            image_height=image_height,
        )

        polygon_array = np.array(
            polygon,
            dtype=np.int32,
        ).reshape(
            (
                -1,
                1,
                2,
            )
        )

        color = STATE_COLORS[state.stable_state]

        cv2.polylines(
            annotated,
            [
                polygon_array,
            ],
            isClosed=True,
            color=color,
            thickness=3,
            lineType=cv2.LINE_AA,
        )

        x_coordinates = [point[0] for point in polygon]

        y_coordinates = [point[1] for point in polygon]

        label_x = min(x_coordinates)

        label_y = max(
            min(y_coordinates) - 10,
            24,
        )

        stable_label = state.stable_state.value.upper()

        raw_label = state.raw_state.value.upper()

        label = f"{state.region_id}: {stable_label} {state.stable_confidence:.2f}"

        if state.raw_state != state.stable_state:
            label += f" raw={raw_label}"

        if state.consecutive_candidate_frames > 0:
            label += (
                " candidate="
                f"{state.candidate_state.value}"
                ":"
                f"{state.consecutive_candidate_frames}"
            )

        cv2.putText(
            annotated,
            label,
            (
                label_x,
                label_y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return annotated
