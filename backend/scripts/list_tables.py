from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql://postgres:sn5IF7(#uDyv#tj$G@localhost:5432/design_tools_core"


def main() -> None:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    print(inspector.get_table_names())


if __name__ == "__main__":
    main()
