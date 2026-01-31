from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:sn5IF7(#uDyv#tj$G@localhost:5432/design_tools_core"

def drop_core_tables() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS designs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))


if __name__ == "__main__":
    drop_core_tables()
