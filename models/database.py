import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from config import get_config
import logging

logger = logging.getLogger(__name__)

# Global variables for lazy initialization
_engine = None
_SessionFactory = None
_Session = None
_lock = threading.Lock()

def _get_engine():
    """Lazy initialization of database engine"""
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:  # Double-check locking
                config = get_config()
                _engine = create_engine(
                    config.DATABASE_URL,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo=config.DEBUG,  # Log SQL queries in debug mode
                    connect_args={"check_same_thread": False} if 'sqlite' in config.DATABASE_URL else {}
                )
    return _engine

def _get_session_factory():
    """Lazy initialization of session factory"""
    global _SessionFactory, _Session
    if _SessionFactory is None:
        with _lock:
            if _SessionFactory is None:  # Double-check locking
                engine = _get_engine()
                _SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
                _Session = scoped_session(_SessionFactory)
    return _Session

@contextmanager
def get_db_session():
    """
    Thread-safe database session context manager
    Ensures proper session cleanup and error handling
    """
    Session = _get_session_factory()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()
        Session.remove()  # Remove thread-local session

def init_db():
    """Initialize database tables"""
    try:
        engine = _get_engine()
        from models.base import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def check_db_connection():
    """Check database connection health"""
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        logger.debug("Database connection check passed")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}")
        return False

def get_db_stats():
    """Get database connection pool statistics"""
    engine = _get_engine()
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'invalid': pool.invalid()
    }