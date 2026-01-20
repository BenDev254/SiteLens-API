import logging
import sys
import contextvars

# Context var for correlation id
request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Attach request_id (or 'none') so formatters can display it
        record.request_id = request_id_ctx_var.get() or "none"
        return True


def configure_logging(level: str | None = None) -> None:
    """Configure root logger with a simple formatter that includes request id."""
    level = (level or None)
    root = logging.getLogger()
    if root.handlers:
        # keep existing handlers but ensure our filter is attached
        for h in root.handlers:
            h.addFilter(RequestIdFilter())
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(level or logging.INFO)
