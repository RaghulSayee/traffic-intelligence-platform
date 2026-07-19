import asyncio
import logging
import os
import signal
import socket
from uuid import uuid4

from app.core.config import get_settings
from app.storage.local import LocalVideoStorage
from app.workers.video_worker import (
    VideoProcessingWorker,
)


logging.basicConfig(
    level=logging.INFO,
    format=("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
)


async def run_worker() -> None:
    """Create and run one video-processing worker."""

    settings = get_settings()
    stop_event = asyncio.Event()

    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"

    storage = LocalVideoStorage(
        root=settings.video_storage_path,
        maximum_bytes=settings.max_video_upload_bytes,
        chunk_size_bytes=(settings.upload_chunk_size_bytes),
    )

    worker = VideoProcessingWorker(
        worker_id=worker_id,
        settings=settings,
        storage=storage,
        stop_event=stop_event,
    )

    loop = asyncio.get_running_loop()

    for signal_name in (
        signal.SIGINT,
        signal.SIGTERM,
    ):
        loop.add_signal_handler(
            signal_name,
            stop_event.set,
        )

    await worker.run_forever()


def main() -> None:
    """Run the worker process."""

    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
