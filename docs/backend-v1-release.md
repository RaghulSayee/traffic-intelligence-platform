# Traffic Intelligence Backend 1.0

## Release versions

- Pipeline version: `1.0.0`
- Detection artifact schema: `1.7`

## Supported analysis

The backend performs:

- General object detection and multi-object tracking
- Motorcycle and rider association
- Triple-riding detection
- Helmet and no-helmet detection
- Wrong-way vehicle detection
- Lane occupancy and lane-violation detection
- Traffic-light state classification and temporal stabilization
- Red-light stop-line crossing detection

## Violation lifecycle

Stateful violations emit lifecycle transitions:

- `started` after temporal confirmation
- `ended` after the violation disappears
- `ended` during end-of-video flushing when an active violation remains at the final frame

The following violations use lifecycle finalization:

- Triple riding
- No helmet
- Wrong way
- Lane violation

Red-light violations are instantaneous stop-line crossing events and emit a single `started` event.

## Persistence and evidence

Violation events are persisted with deterministic event keys so worker retries do not create duplicate records.

Each event may include:

- Detection confidence
- Rule confidence
- Track identifiers
- Violation geometry
- Transition history
- Evidence image
- Annotated preview video
- Review status

## Scene configuration

Camera scenes can define:

- Monitoring zones
- Lane polygons
- Allowed lane directions
- Traffic-light regions
- Stop lines
- Stop-line-to-lane relationships
- Stop-line-to-signal relationships
- Enabled violation rules

## Validation

Run the complete backend test suite:

```bash
cd backend
uv run ruff check .
uv run python -m pytest -q
