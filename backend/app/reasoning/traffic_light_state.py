from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np

from app.models.enums import ViolationType
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
    TrafficLightRegionConfiguration,
)
from app.scene.geometry import (
    normalized_polygon_to_pixels,
)


class TrafficLightState(StrEnum):
    """Traffic-light states visible in a configured region."""

    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TrafficLightObservation:
    """Color-classification result for one signal region."""

    region_id: str
    region_name: str | None

    state: TrafficLightState
    confidence: float

    red_score: float
    yellow_score: float
    green_score: float
    active_pixel_ratio: float

    polygon_pixel_count: int
    active_pixel_count: int


@dataclass(frozen=True, slots=True)
class TrafficLightStateResult:
    """Traffic-light observations produced for one frame."""

    observations: tuple[
        TrafficLightObservation,
        ...,
    ]

    def count_by_state(
        self,
    ) -> dict[str, int]:
        """Count configured regions by classified state."""

        counts: dict[str, int] = {}

        for observation in self.observations:
            state = observation.state.value

            counts[state] = (
                counts.get(
                    state,
                    0,
                )
                + 1
            )

        return counts

    def get_region(
        self,
        region_id: str,
    ) -> TrafficLightObservation | None:
        """Return an observation by configured region ID."""

        for observation in self.observations:
            if observation.region_id == region_id:
                return observation

        return None


class TrafficLightStateClassifier:
    """
    Classify configured traffic-light regions using HSV color.

    OpenCV represents hue from 0 through 179:

    - Red wraps around both ends of the hue scale.
    - Yellow occupies the region around hue 15 through 40.
    - Green occupies the region around hue 40 through 95.

    Saturation and value thresholds suppress gray, white,
    black, shadows, and inactive signal lamps.
    """

    RED_LOW_MAX_HUE = 10
    RED_HIGH_MIN_HUE = 170

    YELLOW_MIN_HUE = 15
    YELLOW_MAX_HUE = 40

    GREEN_MIN_HUE = 40
    GREEN_MAX_HUE = 95

    def __init__(
        self,
        *,
        minimum_saturation: int,
        minimum_value: int,
        minimum_active_pixel_ratio: float,
        dominance_ratio: float,
    ) -> None:
        if not 0 <= minimum_saturation <= 255:
            raise ValueError("Minimum saturation must be between 0 and 255.")

        if not 0 <= minimum_value <= 255:
            raise ValueError("Minimum value must be between 0 and 255.")

        if not 0.0 < minimum_active_pixel_ratio <= 1.0:
            raise ValueError(
                "Minimum active pixel ratio must be greater than zero and at most one."
            )

        if dominance_ratio < 1.0:
            raise ValueError("Dominance ratio must be at least one.")

        self.minimum_saturation = minimum_saturation
        self.minimum_value = minimum_value

        self.minimum_active_pixel_ratio = minimum_active_pixel_ratio

        self.dominance_ratio = dominance_ratio

    def classify(
        self,
        *,
        frame: np.ndarray,
        scene: CameraSceneConfiguration | None,
    ) -> TrafficLightStateResult:
        """Classify all configured traffic-light regions."""

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                "Traffic-light classification requires a three-channel BGR image."
            )

        image_height, image_width = frame.shape[:2]

        if image_width <= 0 or image_height <= 0:
            raise ValueError("Image dimensions must be positive.")

        if (
            scene is None
            or ViolationType.RED_LIGHT not in scene.enabled_violations
            or not scene.traffic_light_regions
        ):
            return TrafficLightStateResult(
                observations=(),
            )

        observations = tuple(
            self._classify_region(
                frame=frame,
                region=region,
                image_width=image_width,
                image_height=image_height,
            )
            for region in scene.traffic_light_regions
        )

        return TrafficLightStateResult(
            observations=observations,
        )

    def _classify_region(
        self,
        *,
        frame: np.ndarray,
        region: TrafficLightRegionConfiguration,
        image_width: int,
        image_height: int,
    ) -> TrafficLightObservation:
        """Classify one configured polygonal signal region."""

        polygon = normalized_polygon_to_pixels(
            region.polygon,
            image_width=image_width,
            image_height=image_height,
        )

        polygon_array = np.array(
            polygon,
            dtype=np.int32,
        )

        x, y, width, height = cv2.boundingRect(
            polygon_array,
        )

        roi = frame[
            y : y + height,
            x : x + width,
        ]

        translated_polygon = polygon_array - np.array(
            [
                x,
                y,
            ],
            dtype=np.int32,
        )

        polygon_mask = np.zeros(
            (
                height,
                width,
            ),
            dtype=np.uint8,
        )

        cv2.fillPoly(
            polygon_mask,
            [
                translated_polygon,
            ],
            255,
        )

        polygon_pixels = polygon_mask > 0

        polygon_pixel_count = int(np.count_nonzero(polygon_pixels))

        if polygon_pixel_count == 0:
            return self._unknown_observation(
                region=region,
            )

        hsv = cv2.cvtColor(
            roi,
            cv2.COLOR_BGR2HSV,
        )

        hue = hsv[
            :,
            :,
            0,
        ]

        saturation = hsv[
            :,
            :,
            1,
        ]

        value = hsv[
            :,
            :,
            2,
        ]

        visible_color = (
            polygon_pixels
            & (saturation >= self.minimum_saturation)
            & (value >= self.minimum_value)
        )

        red_pixels = visible_color & (
            (hue <= self.RED_LOW_MAX_HUE) | (hue >= self.RED_HIGH_MIN_HUE)
        )

        yellow_pixels = (
            visible_color & (hue >= self.YELLOW_MIN_HUE) & (hue < self.YELLOW_MAX_HUE)
        )

        green_pixels = (
            visible_color & (hue >= self.GREEN_MIN_HUE) & (hue <= self.GREEN_MAX_HUE)
        )

        red_count = int(np.count_nonzero(red_pixels))

        yellow_count = int(np.count_nonzero(yellow_pixels))

        green_count = int(np.count_nonzero(green_pixels))

        red_score = red_count / polygon_pixel_count

        yellow_score = yellow_count / polygon_pixel_count

        green_score = green_count / polygon_pixel_count

        active_pixel_count = red_count + yellow_count + green_count

        active_pixel_ratio = active_pixel_count / polygon_pixel_count

        state, confidence = self._choose_state(
            red_score=red_score,
            yellow_score=yellow_score,
            green_score=green_score,
        )

        return TrafficLightObservation(
            region_id=region.region_id,
            region_name=region.name,
            state=state,
            confidence=confidence,
            red_score=red_score,
            yellow_score=yellow_score,
            green_score=green_score,
            active_pixel_ratio=(active_pixel_ratio),
            polygon_pixel_count=(polygon_pixel_count),
            active_pixel_count=(active_pixel_count),
        )

    def _choose_state(
        self,
        *,
        red_score: float,
        yellow_score: float,
        green_score: float,
    ) -> tuple[
        TrafficLightState,
        float,
    ]:
        """Choose a state from the three color scores."""

        scores = [
            (
                TrafficLightState.RED,
                red_score,
            ),
            (
                TrafficLightState.YELLOW,
                yellow_score,
            ),
            (
                TrafficLightState.GREEN,
                green_score,
            ),
        ]

        scores.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        winning_state, winning_score = scores[0]

        second_score = scores[1][1]

        if winning_score < self.minimum_active_pixel_ratio:
            return (
                TrafficLightState.UNKNOWN,
                0.0,
            )

        if second_score > 0.0 and winning_score < second_score * self.dominance_ratio:
            return (
                TrafficLightState.UNKNOWN,
                0.0,
            )

        total_score = red_score + yellow_score + green_score

        confidence = winning_score / total_score if total_score > 0.0 else 0.0

        return (
            winning_state,
            min(
                max(
                    confidence,
                    0.0,
                ),
                1.0,
            ),
        )

    @staticmethod
    def _unknown_observation(
        *,
        region: TrafficLightRegionConfiguration,
    ) -> TrafficLightObservation:
        """Create an empty unknown observation."""

        return TrafficLightObservation(
            region_id=region.region_id,
            region_name=region.name,
            state=TrafficLightState.UNKNOWN,
            confidence=0.0,
            red_score=0.0,
            yellow_score=0.0,
            green_score=0.0,
            active_pixel_ratio=0.0,
            polygon_pixel_count=0,
            active_pixel_count=0,
        )
