from app.services.rate_limit import RateLimiter
from app.services.trips import classify_error


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_rate_limit_per_minute_then_recovers():
    clock = Clock()
    limiter = RateLimiter(per_minute=2, per_day=100, clock=clock)

    assert limiter.check("u") is None and limiter.check("u") is None
    assert limiter.check("u") == 60.0
    clock.now = 30
    assert limiter.check("u") == 30.0
    clock.now = 60
    assert limiter.check("u") is None


def test_rate_limit_per_day():
    clock = Clock()
    limiter = RateLimiter(per_minute=100, per_day=3, clock=clock)
    for minute in range(3):
        clock.now = minute * 60
        assert limiter.check("u") is None

    clock.now = 3 * 60
    assert limiter.check("u") == 86_400 - 180
    clock.now = 86_400
    assert limiter.check("u") is None


def test_rate_limit_is_per_user():
    limiter = RateLimiter(per_minute=1, per_day=10, clock=Clock())
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None


class Coded(Exception):
    def __init__(self, code, text=""):
        super().__init__(text)
        self.code = code


def test_classify_error():
    assert classify_error(Coded(429))[0] == "ai_quota_exceeded"
    assert classify_error(Coded(503, "UNAVAILABLE"))[0] == "ai_unavailable"
    assert classify_error(RuntimeError("secret detail"))[0] == "internal_error"
    assert "secret detail" not in classify_error(RuntimeError("secret detail"))[1]


def test_classify_error_looks_inside_wrapper_exceptions():
    try:
        try:
            raise Coded(503, "503 UNAVAILABLE")
        except Coded as inner:
            raise RuntimeError("Dynamic node travel_coordinator failed") from inner
    except RuntimeError as wrapped:
        assert classify_error(wrapped)[0] == "ai_unavailable"
