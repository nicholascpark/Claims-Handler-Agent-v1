"""API Routes."""
from .chat import router as chat_router
from .health import router as health_router
from .forms import router as forms_router
from .settings import router as settings_router

__all__ = ["chat_router", "health_router", "forms_router", "settings_router"]
