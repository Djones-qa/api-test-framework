"""
Performance tests — assert that endpoints respond within acceptable thresholds.

These are not load tests (use Locust/k6 for that). They verify that individual
endpoints don't regress into unacceptably slow response times during development.

Thresholds are intentionally generous for a test environment running on SQLite.
"""
import time
import statistics
import pytest

# Response time thresholds (seconds)
FAST_THRESHOLD = 0.5      # Simple reads
MEDIUM_THRESHOLD = 1.0    # Writes with hashing / DB inserts
SLOW_THRESHOLD = 2.0      # Complex queries or auth flows
ITERATIONS = 5            # Number of samples per endpoint


def measure_response_time(fn) -> float:
    """Return elapsed time in seconds for a single call."""
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def assert_p95_under(times: list[float], threshold: float, label: str) -> None:
    """Assert that the 95th-percentile response time is under the threshold."""
    sorted_times = sorted(times)
    p95_index = max(0, int(len(sorted_times) * 0.95) - 1)
    p95 = sorted_times[p95_index]
    avg = statistics.mean(times)
    print(f"\n[{label}] avg={avg:.3f}s  p95={p95:.3f}s  threshold={threshold}s")
    assert p95 < threshold, (
        f"[{label}] p95 response time {p95:.3f}s exceeds threshold {threshold}s"
    )


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthPerformance:
    def test_health_response_time(self, client):
        times = [
            measure_response_time(lambda: client.get("/health"))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, "GET /health")

    def test_health_consistent_response(self, client):
        """Health endpoint should have low variance."""
        times = [
            measure_response_time(lambda: client.get("/health"))
            for _ in range(ITERATIONS)
        ]
        if len(times) > 1:
            stdev = statistics.stdev(times)
            assert stdev < 0.5, f"High variance in /health response times: stdev={stdev:.3f}s"


# ── Book read endpoints ───────────────────────────────────────────────────────

class TestBookReadPerformance:
    def test_list_books_response_time(self, client, sample_books):
        times = [
            measure_response_time(lambda: client.get("/books"))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, "GET /books")

    def test_get_single_book_response_time(self, client, sample_book):
        book_id = sample_book.id
        times = [
            measure_response_time(lambda: client.get(f"/books/{book_id}"))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, f"GET /books/{book_id}")

    def test_list_books_with_filter_response_time(self, client, sample_books):
        times = [
            measure_response_time(lambda: client.get("/books?genre=Programming"))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, "GET /books?genre=Programming")

    def test_list_books_with_pagination_response_time(self, client, sample_books):
        times = [
            measure_response_time(lambda: client.get("/books?page=1&page_size=5"))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, "GET /books (paginated)")


# ── Auth endpoints ────────────────────────────────────────────────────────────

class TestAuthPerformance:
    def test_login_response_time(self, client, test_user):
        """Login involves bcrypt verification — allow more time."""
        times = [
            measure_response_time(
                lambda: client.post(
                    "/auth/token",
                    data={"username": "testuser", "password": "password123"},
                )
            )
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, SLOW_THRESHOLD, "POST /auth/token")

    def test_get_me_response_time(self, client, auth_headers):
        times = [
            measure_response_time(lambda: client.get("/auth/me", headers=auth_headers))
            for _ in range(ITERATIONS)
        ]
        assert_p95_under(times, FAST_THRESHOLD, "GET /auth/me")


# ── Write endpoints ───────────────────────────────────────────────────────────

class TestBookWritePerformance:
    def test_create_book_response_time(self, client, auth_headers):
        """Each iteration uses a unique ISBN to avoid duplicate errors."""
        import random

        def create_book():
            isbn = f"978{random.randint(1000000000, 9999999999)}"
            client.post(
                "/books",
                json={
                    "title": "Perf Test Book",
                    "author": "Perf Author",
                    "isbn": isbn,
                    "price": 9.99,
                },
                headers=auth_headers,
            )

        times = [measure_response_time(create_book) for _ in range(ITERATIONS)]
        assert_p95_under(times, MEDIUM_THRESHOLD, "POST /books")
