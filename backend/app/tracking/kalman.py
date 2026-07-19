import numpy as np
from numpy.typing import NDArray

from app.detection.types import BoundingBox


FloatMatrix = NDArray[np.float64]


class BoundingBoxKalmanFilter:
    """
    Estimate bounding-box position and velocity.

    State vector:

    [center_x, center_y, width, height,
     velocity_x, velocity_y, velocity_width, velocity_height]
    """

    def __init__(
        self,
        *,
        bounding_box: BoundingBox,
        process_noise: float,
        measurement_noise: float,
    ) -> None:
        if process_noise <= 0:
            raise ValueError("Process noise must be greater than zero.")

        if measurement_noise <= 0:
            raise ValueError("Measurement noise must be greater than zero.")

        center_x, center_y = bounding_box.center

        self.state: FloatMatrix = np.zeros(
            (8, 1),
            dtype=np.float64,
        )

        self.state[
            0:4,
            0,
        ] = np.array(
            [
                center_x,
                center_y,
                bounding_box.width,
                bounding_box.height,
            ],
            dtype=np.float64,
        )

        self.covariance: FloatMatrix = np.eye(
            8,
            dtype=np.float64,
        )

        # Position is initially more certain than velocity.
        self.covariance[0:4, 0:4] *= 10.0
        self.covariance[4:8, 4:8] *= 100.0

        self.measurement_matrix: FloatMatrix = np.zeros(
            (4, 8),
            dtype=np.float64,
        )

        self.measurement_matrix[
            0:4,
            0:4,
        ] = np.eye(
            4,
            dtype=np.float64,
        )

        self.measurement_noise: FloatMatrix = (
            np.eye(
                4,
                dtype=np.float64,
            )
            * measurement_noise
        )

        self.process_noise_scale = process_noise

    def predict(
        self,
        *,
        delta_seconds: float,
    ) -> BoundingBox:
        """Predict where the object should be now."""

        delta_seconds = max(
            delta_seconds,
            0.001,
        )

        transition = np.eye(
            8,
            dtype=np.float64,
        )

        for index in range(4):
            transition[
                index,
                index + 4,
            ] = delta_seconds

        process_noise = np.eye(
            8,
            dtype=np.float64,
        )

        process_noise[0:4, 0:4] *= self.process_noise_scale * delta_seconds**2

        process_noise[4:8, 4:8] *= self.process_noise_scale * delta_seconds

        self.state = transition @ self.state

        self.covariance = transition @ self.covariance @ transition.T + process_noise

        self._enforce_valid_size()

        return self.bounding_box

    def update(
        self,
        bounding_box: BoundingBox,
    ) -> BoundingBox:
        """Correct the prediction using a YOLO measurement."""

        measurement = self._measurement_from_box(bounding_box)

        innovation = measurement - self.measurement_matrix @ self.state

        innovation_covariance = (
            self.measurement_matrix @ self.covariance @ self.measurement_matrix.T
            + self.measurement_noise
        )

        kalman_gain = (
            self.covariance
            @ self.measurement_matrix.T
            @ np.linalg.pinv(innovation_covariance)
        )

        self.state = self.state + kalman_gain @ innovation

        identity = np.eye(
            8,
            dtype=np.float64,
        )

        self.covariance = (
            identity - kalman_gain @ self.measurement_matrix
        ) @ self.covariance

        self._enforce_valid_size()

        return self.bounding_box

    @property
    def bounding_box(self) -> BoundingBox:
        """Convert the current state into box coordinates."""

        center_x = float(self.state[0, 0])
        center_y = float(self.state[1, 0])

        width = max(
            float(self.state[2, 0]),
            1.0,
        )

        height = max(
            float(self.state[3, 0]),
            1.0,
        )

        return BoundingBox(
            x1=center_x - width / 2.0,
            y1=center_y - height / 2.0,
            x2=center_x + width / 2.0,
            y2=center_y + height / 2.0,
        )

    @property
    def velocity(self) -> tuple[float, float]:
        """Return estimated center velocity in pixels/second."""

        return (
            float(self.state[4, 0]),
            float(self.state[5, 0]),
        )

    @staticmethod
    def _measurement_from_box(
        bounding_box: BoundingBox,
    ) -> FloatMatrix:
        center_x, center_y = bounding_box.center

        return np.array(
            [
                [center_x],
                [center_y],
                [bounding_box.width],
                [bounding_box.height],
            ],
            dtype=np.float64,
        )

    def _enforce_valid_size(self) -> None:
        self.state[2, 0] = max(
            self.state[2, 0],
            1.0,
        )

        self.state[3, 0] = max(
            self.state[3, 0],
            1.0,
        )
