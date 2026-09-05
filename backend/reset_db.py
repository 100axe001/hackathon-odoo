"""Drop every table, recreate from the models, reseed.

Safe to run repeatedly and expected to be: the demo depends on starting from a
known state. It takes seconds.
"""

# Importing the models registers them on Base.metadata.
import app.models  # noqa: F401  registers every model on Base.metadata
from app.database.connection import Base, engine
from app.logging.setup_logging import get_logger, setup_logging
from seed import main as seed_main

setup_logging()
logger = get_logger(__name__)


def main() -> None:
    logger.info("Dropping tables")
    Base.metadata.drop_all(bind=engine)

    logger.info("Creating tables")
    Base.metadata.create_all(bind=engine)

    seed_main()
    logger.info("Database reset complete")


if __name__ == "__main__":
    main()
