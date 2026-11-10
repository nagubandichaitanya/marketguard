from backend.app.database import Base, engine
from backend.app import models


def initialize_database():
    print("Creating MarketGuard database tables...")

    Base.metadata.create_all(bind=engine)

    print("\nDatabase tables created successfully!")
    print(f"Total tables registered: {len(Base.metadata.tables)}")

    for table_name in Base.metadata.tables:
        print(f" - {table_name}")


if __name__ == "__main__":
    initialize_database()