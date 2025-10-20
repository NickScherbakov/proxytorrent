"""Async task queue for processing fetch requests."""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.database import FetchRequest
from app.models.schemas import RequestStatus
from app.services.fetcher import FetchError, FetchTimeoutError, get_fetcher
from app.services.packager import PackageError, get_packager
from app.services.seeder import SeederError, get_seeder

logger = logging.getLogger(__name__)


class TaskQueue:
    """Async task queue for processing fetch requests."""

    def __init__(self, max_workers: int = 5) -> None:
        """Initialize task queue."""
        self.max_workers = max_workers
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.running = False

    async def enqueue(self, request_id: str) -> None:
        """Add request to queue."""
        await self.queue.put(request_id)
        logger.info(f"Enqueued request {request_id}")

    async def _process_request(self, request_id: str) -> None:
        """
        Process a single fetch request.

        Args:
            request_id: Request ID to process
        """
        logger.info(f"Processing request {request_id}")

        async with async_session_maker() as session:
            try:
                # Load request
                result = await session.execute(
                    select(FetchRequest).where(FetchRequest.id == request_id)
                )
                request = result.scalar_one_or_none()

                if not request:
                    logger.error(f"Request {request_id} not found")
                    return

                if request.status == RequestStatus.CANCELLED.value:
                    logger.info(f"Request {request_id} was cancelled")
                    return

                # Update status to fetching
                request.status = RequestStatus.FETCHING.value
                request.progress = 10
                request.updated_at = datetime.utcnow()
                await session.commit()

                # Fetch content
                fetcher = await get_fetcher()
                fetch_result = await fetcher.fetch(
                    url=str(request.url),
                    method=request.method,
                    headers=request.headers,
                    body=request.body,
                )

                # Update progress
                request.progress = 40
                request.content_hash = fetch_result.content_hash
                request.content_size = fetch_result.content_size
                request.content_type = fetch_result.content_type
                request.updated_at = datetime.utcnow()
                await session.commit()

                # Package into torrent
                request.status = RequestStatus.PACKAGING.value
                request.progress = 50
                request.updated_at = datetime.utcnow()
                await session.commit()

                packager = get_packager()
                package = await packager.package(fetch_result, request_id)

                # Update with torrent info
                request.infohash = package.infohash
                request.torrent_path = str(package.torrent_path)
                request.progress = 70
                request.updated_at = datetime.utcnow()
                await session.commit()

                # Add to seeder
                request.status = RequestStatus.SEEDING.value
                request.progress = 80
                request.updated_at = datetime.utcnow()
                await session.commit()

                seeder = get_seeder()
                seeder.add_torrent(
                    package.torrent_path, package.content_path, package.infohash
                )

                # Mark as ready
                request.status = RequestStatus.READY.value
                request.progress = 100
                request.completed_at = datetime.utcnow()
                request.updated_at = datetime.utcnow()
                await session.commit()

                logger.info(
                    f"Request {request_id} completed successfully (infohash={package.infohash})"
                )

            except FetchTimeoutError as e:
                logger.error(f"Request {request_id} timed out: {e}")
                await self._mark_error(session, request_id, f"Timeout: {e}")

            except FetchError as e:
                logger.error(f"Request {request_id} fetch error: {e}")
                await self._mark_error(session, request_id, f"Fetch error: {e}")

            except PackageError as e:
                logger.error(f"Request {request_id} packaging error: {e}")
                await self._mark_error(session, request_id, f"Packaging error: {e}")

            except SeederError as e:
                logger.error(f"Request {request_id} seeding error: {e}")
                await self._mark_error(session, request_id, f"Seeding error: {e}")

            except Exception as e:
                logger.exception(f"Unexpected error processing request {request_id}")
                await self._mark_error(session, request_id, f"Unexpected error: {e}")

    async def _mark_error(
        self, session: AsyncSession, request_id: str, error_message: str
    ) -> None:
        """Mark request as failed."""
        try:
            result = await session.execute(
                select(FetchRequest).where(FetchRequest.id == request_id)
            )
            request = result.scalar_one_or_none()

            if request:
                request.status = RequestStatus.ERROR.value
                request.error_message = error_message
                request.updated_at = datetime.utcnow()
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to mark request {request_id} as error: {e}")

    async def _worker(self) -> None:
        """Worker task that processes requests from queue."""
        logger.info("Worker started")

        while self.running:
            try:
                # Get next request with timeout
                request_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                try:
                    await self._process_request(request_id)
                finally:
                    self.queue.task_done()

            except TimeoutError:
                # No items in queue, continue
                continue
            except Exception as e:
                logger.exception(f"Worker error: {e}")

        logger.info("Worker stopped")

    async def start(self) -> None:
        """Start the task queue workers."""
        if self.running:
            return

        logger.info(f"Starting task queue with {self.max_workers} workers")
        self.running = True

        self.workers = [
            asyncio.create_task(self._worker()) for _ in range(self.max_workers)
        ]

    async def stop(self) -> None:
        """Stop the task queue workers."""
        if not self.running:
            return

        logger.info("Stopping task queue")
        self.running = False

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("Task queue stopped")


# Global task queue instance
_task_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
