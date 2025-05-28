"""FastAPI v1 API modules."""
from logger import get_logger
from .router import router as v1_router

# Initialize logger for the v1 package
logger = get_logger(__name__)
logger.info("Initializing v1 API package")
