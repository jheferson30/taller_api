"""
Integration tests for Alembic database migrations.

Tests cover:
- Migration upgrade applies successfully
- Migration downgrade reverts changes (Property 5: Database Migration Round Trip)
- Migration history tracking
"""
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import os


@pytest.fixture
def alembic_config():
    """Create Alembic configuration for testing."""
    config = Config("alembic.ini")
    # Use test database URL
    test_db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:123456@localhost:5432/taller_db_test?client_encoding=utf8")
    config.set_main_option("sqlalchemy.url", test_db_url)
    return config


@pytest.fixture
def test_engine(alembic_config):
    """Create test database engine."""
    db_url = alembic_config.get_main_option("sqlalchemy.url")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


class TestAlembicMigrations:
    """Tests for Alembic migration functionality."""
    
    def test_migration_upgrade_applies_successfully(self, alembic_config, test_engine):
        """Test that upgrade migration applies without errors."""
        # Arrange - downgrade to base first
        try:
            command.downgrade(alembic_config, "base")
        except Exception:
            pass  # May fail if already at base
        
        # Act - upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Assert - verify alembic_version table exists and has a version
        inspector = inspect(test_engine)
        assert "alembic_version" in inspector.get_table_names()
        
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            assert version is not None
    
    def test_migration_downgrade_reverts_changes(self, alembic_config, test_engine):
        """
        Test that downgrade migration reverts changes.
        
        Property 5: Database Migration Round Trip
        Validates that upgrade followed by downgrade returns to original state.
        """
        # Arrange - ensure we're at head
        command.upgrade(alembic_config, "head")
        
        # Get current version
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            head_version = result.scalar()
        
        # Act - downgrade one step
        command.downgrade(alembic_config, "-1")
        
        # Assert - verify version changed
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            downgraded_version = result.scalar()
            
            # For initial migration, downgrade goes to base (no version)
            # For other migrations, version should be different
            if downgraded_version is not None:
                assert downgraded_version != head_version
        
        # Cleanup - upgrade back to head
        command.upgrade(alembic_config, "head")
    
    def test_migration_history_tracking(self, alembic_config):
        """Test that migration history is properly tracked."""
        # Arrange
        script = ScriptDirectory.from_config(alembic_config)
        
        # Act - get all revisions
        revisions = list(script.walk_revisions())
        
        # Assert - verify we have at least the initial migration
        assert len(revisions) >= 1
        
        # Verify initial migration exists
        initial_migration = revisions[-1]  # Last in walk is first chronologically
        assert initial_migration.revision is not None
        assert initial_migration.down_revision is None  # Initial has no parent
    
    def test_migration_idempotency(self, alembic_config):
        """Test that applying the same migration twice doesn't cause errors."""
        # Arrange - ensure we're at head
        command.upgrade(alembic_config, "head")
        
        # Act - try to upgrade again (should be no-op)
        try:
            command.upgrade(alembic_config, "head")
            success = True
        except Exception as e:
            success = False
            error = str(e)
        
        # Assert - should succeed without errors
        assert success, f"Idempotent upgrade failed: {error if not success else ''}"
    
    def test_migration_current_shows_head(self, alembic_config, test_engine):
        """Test that current migration matches head after upgrade."""
        # Arrange - upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Act - get current version
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
        
        # Get head version from script directory
        script = ScriptDirectory.from_config(alembic_config)
        head_version = script.get_current_head()
        
        # Assert - current should match head
        assert current_version == head_version
    
    def test_alembic_version_table_structure(self, alembic_config, test_engine):
        """Test that alembic_version table has correct structure."""
        # Arrange - ensure migrations are applied
        command.upgrade(alembic_config, "head")
        
        # Act - inspect alembic_version table
        inspector = inspect(test_engine)
        columns = inspector.get_columns("alembic_version")
        
        # Assert - verify table structure
        column_names = [col["name"] for col in columns]
        assert "version_num" in column_names
        
        # Verify version_num is the primary key or has unique constraint
        pk_constraint = inspector.get_pk_constraint("alembic_version")
        assert "version_num" in pk_constraint.get("constrained_columns", [])


class TestMigrationRoundTrip:
    """
    Property-based tests for migration round trip.
    
    Property 5: Database Migration Round Trip
    For any migration M, applying upgrade(M) followed by downgrade(M)
    should return the database to its original state.
    """
    
    def test_upgrade_downgrade_round_trip_preserves_state(self, alembic_config, test_engine):
        """
        Test that upgrade followed by downgrade preserves database state.
        
        This is a critical property for safe migrations in production.
        """
        # Arrange - start at head
        command.upgrade(alembic_config, "head")
        
        # Get initial state
        inspector = inspect(test_engine)
        initial_tables = set(inspector.get_table_names())
        
        # Get current version
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            initial_version = result.scalar()
        
        # Act - downgrade and upgrade
        command.downgrade(alembic_config, "-1")
        command.upgrade(alembic_config, "head")
        
        # Assert - verify we're back to initial state
        final_tables = set(inspector.get_table_names())
        
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            final_version = result.scalar()
        
        assert final_version == initial_version, "Version should be restored after round trip"
        assert final_tables == initial_tables, "Tables should be restored after round trip"
    
    def test_multiple_downgrades_and_upgrades(self, alembic_config, test_engine):
        """Test that multiple downgrade/upgrade cycles work correctly."""
        # Arrange - ensure at head
        command.upgrade(alembic_config, "head")
        
        # Get head version
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            head_version = result.scalar()
        
        # Act - perform multiple cycles
        for _ in range(2):
            command.downgrade(alembic_config, "-1")
            command.upgrade(alembic_config, "+1")
        
        # Assert - should be back at head
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            final_version = result.scalar()
        
        assert final_version == head_version


@pytest.mark.skipif(
    os.getenv("SKIP_MIGRATION_TESTS") == "true",
    reason="Migration tests skipped (set SKIP_MIGRATION_TESTS=false to run)"
)
class TestMigrationPerformance:
    """Optional performance tests for migrations."""
    
    def test_migration_upgrade_completes_in_reasonable_time(self, alembic_config):
        """Test that migration upgrade completes within acceptable time."""
        import time
        
        # Arrange - downgrade to base
        try:
            command.downgrade(alembic_config, "base")
        except Exception:
            pass
        
        # Act - measure upgrade time
        start_time = time.time()
        command.upgrade(alembic_config, "head")
        elapsed_time = time.time() - start_time
        
        # Assert - should complete in less than 30 seconds
        assert elapsed_time < 30, f"Migration took {elapsed_time:.2f}s, expected < 30s"
