# Database and Migrations

The Repository uses PostgreSQL as its primary data store, with Alembic for database migration management. This setup provides a robust foundation for storing and processing events while maintaining schema flexibility through JSON columns.

## Database Architecture

### Event Storage Model

The core of our database design is the Event model, which implements a flexible schema for storing both incoming events and their processing results:

```python
class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid1)
    data = Column(JSON)              # Raw event data
    task_context = Column(JSON)      # Processing results
    created_at = Column(DateTime)    # Event creation timestamp
    updated_at = Column(DateTime)    # Last update timestamp
```
This design provides:

- Unique identification of each event through UUID
- Flexible storage of any event type through JSON columns
- Automatic timestamp tracking
- Convenient querying of both raw data and processing results

## Repository Pattern

We implement the repository pattern to abstract database operations and provide a clean interface for data access:

```python
class GenericRepository(Generic[T]):
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model

    def create(self, obj: T) -> T:
        self.session.add(obj)
        self.session.commit()
        return obj
```
This pattern ensures:

- Type-safe database operations
- Consistent error handling
- Transaction management
- Reusable CRUD operations

## Session Management

Database sessions are managed through the dependency injection pattern:

```python
def db_session() -> Generator:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```
This ensures:

- Proper connection handling
- Automatic transaction management
- Resource cleanup
- Connection pooling

## Database Migrations with Alembic

Alembic is a lightweight database migration tool for Python, designed to work with SQLAlchemy, a popular SQL toolkit and Object-Relational Mapping (ORM) library.

- Schema Version Control: Alembic tracks different versions of your database schema, allowing you to upgrade or roll back to any version as needed.
- Migration Script Generation: It can automatically generate migration scripts by comparing your current database schema with your SQLAlchemy models. These scripts describe the changes that need to be applied, such as adding a new table or modifying a column.
- Consistent Migration Application: Using Alembic ensures that all developers in the project apply database changes in the same order and manner, reducing discrepancies between development environments.
- CI/CD Pipeline Integration: Alembic can be included in continuous integration and deployment workflows to automate database migrations during deployment.

### Key Components

- Migration Scripts: Python files detailing specific changes to the database schema.
- Command Line Interface: Tools for creating new migrations, applying existing ones, and managing migration history.
- Configuration File: Defines connection strings and Alembic settings, typically called alembic.ini.

### Migration Architecture

Alembic manages database schema evolution through versioned migration scripts. Our setup uses autogeneration to maintain migrations based on SQLAlchemy models.

### Migration Configuration

The Alembic environment is configured in `env.py`:

```python
from database.session import Base
from database.event import *  # Required for autogeneration

target_metadata = Base.metadata

config.set_main_option(
    "sqlalchemy.url", 
    DatabaseUtils.get_connection_string()
)
```

### Migration Process

1. **Creating Migrations**
   ```bash
   ./makemigration.sh
   ```
   This script:
   - Detects changes in models
   - Generates a new migration file
   - Adds it to version control

2. **Applying Migrations**
   ```bash
   ./migrate.sh
   ```
   This script:
   - Checks current database version
   - Applies pending migrations
   - Updates version tracking

### Migration Best Practices

1. **Version Control**
   - All migrations are under version control
   - Migration files are treated as code
   - Never modify existing migrations

2. **Testing**
   - Test migrations on production data copies
   - Include upgrade and downgrade paths
   - Verify data integrity after migration

3. **Deployment**
   - Run migrations before deploying new code
   - Backup database before migration
   - Use transaction wrappers for safety

## Database Utilities

The DatabaseUtils class provides centralized database configuration:

```python
class DatabaseUtils:
    @staticmethod
    def get_connection_string():
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
```
This ensures:

- Consistent connection string formatting
- Environment-based configuration
- Single source of truth for database settings

## Security Considerations

1. **Connection Security**
   - SSL/TLS encryption for connections
   - Strict password policies
   - Connection pool limits

2. **Data Security**
   - JSON validation before storage
   - Input sanitization
   - Access control through repository layer

3. **Operational Security**
   - Regular backups
   - Migration rollback capabilities
   - Transaction isolation

## Performance Optimization

1. **Indexing Strategy**
   - Optimize UUID primary key
   - Index JSON columns for frequent queries
   - Index timestamps for time-based queries

2. **Query Optimization**
   - Efficient JSON operators
   - Prepared statements
   - Connection pooling

## Extending the Database

To add new models:

1. Create a new model class:

```python
class CustomModel(Base):
    __tablename__ = "custom_models"
    id = Column(UUID(as_uuid=True), primary_key=True)
    # Add custom fields
```

2. Create a migration:

```bash
./makemigration.sh "add_custom_model"
```

3. Apply the migration:

```bash
./migrate.sh
```

The modular design makes database extension straightforward while maintaining data integrity and migration history. 