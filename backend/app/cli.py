from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

import click
from sqlalchemy import inspect, text

from app.database import SessionLocal, engine
from app.models import Design, User

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def _run_alembic(args: Iterable[str]) -> subprocess.CompletedProcess[str]:
    command = ["alembic", "-c", str(ALEMBIC_INI), *args]
    try:
        result = subprocess.run(command, capture_output=True, text=True, cwd=PROJECT_ROOT)
    except FileNotFoundError as exc:
        raise click.ClickException("No se encontró el comando alembic. ¿Está el entorno virtual activo?") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip() or "El comando de Alembic terminó con errores."
        raise click.ClickException(stderr)

    return result


def _print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    stdout = result.stdout.strip()
    if stdout:
        click.echo(stdout)


@click.group()
def cli() -> None:
    """Sistema de utilidades para la base de datos del proyecto."""


@cli.command("list-tables")
def list_tables() -> None:
    """Lista todas las tablas registradas en la base de datos."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            click.echo("No hay tablas en la base de datos.")
            return

        click.echo("Tablas detectadas:")
        click.echo("-" * 50)
        for index, table in enumerate(tables, start=1):
            columns = inspector.get_columns(table)
            column_names = [column["name"] for column in columns]
            preview = ", ".join(column_names[:5]) if column_names else "sin columnas"
            if len(column_names) > 5:
                preview += f" (+{len(column_names) - 5} columnas)"

            click.echo(f"{index}. {table}")
            click.echo(f"   Columnas: {preview}")
        click.echo("-" * 50)
    except Exception as exc:  # pragma: no cover - CLI feedback
        raise click.ClickException(f"Error al listar tablas: {exc}") from exc


@cli.command("drop-tables")
@click.option("--force", "-f", is_flag=True, help="Elimina sin pedir confirmación.")
@click.option("--exclude-alembic", is_flag=True, help="Mantiene la tabla alembic_version.")
def drop_tables(force: bool, exclude_alembic: bool) -> None:
    """Elimina las tablas de la base de datos (solo uso de desarrollo)."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if exclude_alembic:
        tables = [table for table in tables if table != "alembic_version"]

    if not tables:
        click.echo("No hay tablas para eliminar.")
        return

    click.echo("Se eliminarán las siguientes tablas:")
    for table in tables:
        click.echo(f"- {table}")

    if not force and not click.confirm("¿Confirma que desea continuar?"):
        click.echo("Operación cancelada por el usuario.")
        return

    is_postgres = engine.dialect.name == "postgresql"
    try:
        with engine.begin() as conn:
            if is_postgres:
                conn.execute(text("SET session_replication_role = 'replica';"))

            for table in tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))

            if is_postgres:
                conn.execute(text("SET session_replication_role = 'origin';"))
        click.echo(f"Se eliminaron {len(tables)} tablas.")
    except Exception as exc:  # pragma: no cover - CLI feedback
        raise click.ClickException(f"Error al eliminar tablas: {exc}") from exc


@cli.command("migrate")
@click.option("--revision", default="head", show_default=True, help="Revisión objetivo (ej. head, +1, -1).")
def migrate(revision: str) -> None:
    """Aplica migraciones de Alembic."""
    click.echo(f"Aplicando migraciones hasta {revision}...")
    result = _run_alembic(["upgrade", revision])
    _print_process_output(result)
    click.echo("Migración completada.")


@cli.command("downgrade")
@click.option("--revision", default="base", show_default=True, help="Revisión objetivo (ej. base, -1).")
def downgrade(revision: str) -> None:
    """Revierte migraciones de Alembic."""
    if not click.confirm(f"Esto revertirá migraciones hasta {revision}. ¿Desea continuar?"):
        click.echo("Operación cancelada.")
        return

    click.echo(f"Revirtiendo migraciones hasta {revision}...")
    result = _run_alembic(["downgrade", revision])
    _print_process_output(result)
    click.echo("Reversión completada.")


@cli.command("create-migration")
@click.option("--message", "-m", required=True, help="Descripción para la migración.")
def create_migration(message: str) -> None:
    """Genera una nueva migración automática."""
    click.echo(f"Creando migración: {message}")
    result = _run_alembic(["revision", "--autogenerate", "-m", message])
    _print_process_output(result)
    click.echo("Migración creada.")


@cli.command("reset-db")
def reset_db() -> None:
    """Elimina las tablas y ejecuta de nuevo todas las migraciones."""
    click.echo("Reseteando la base de datos...")
    ctx = click.get_current_context()
    ctx.invoke(drop_tables, force=True, exclude_alembic=False)
    ctx.invoke(migrate, revision="head")
    click.echo("Base de datos reseteada.")


@cli.command("check-db")
def check_db() -> None:
    """Verifica la conexión y ofrece estadísticas básicas."""
    try:
        with engine.connect() as conn:
            version_row = conn.execute(text("SELECT version();")).fetchone()
            version_info = version_row[0] if version_row else "versión desconocida"

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        click.echo("Conexión exitosa a la base de datos.")
        click.echo(f"Versión del motor: {version_info}")
        click.echo(f"Total de tablas: {len(tables)}")

        if "alembic_version" in tables:
            with engine.connect() as conn:
                alembic_row = conn.execute(text("SELECT version_num FROM alembic_version;"))
                current_version = alembic_row.scalar()
            click.echo(f"Versión Alembic: {current_version}")

        with SessionLocal() as db:
            for model, table_name in ((User, "users"), (Design, "designs")):
                if table_name in tables:
                    count = db.query(model).count()
                    click.echo(f"Registros en {table_name}: {count}")
    except Exception as exc:  # pragma: no cover - CLI feedback
        raise click.ClickException(f"Error al verificar la base de datos: {exc}") from exc


@cli.command("run-sql")
@click.argument("sql_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def run_sql(sql_file: Path) -> None:
    """Ejecuta un archivo SQL sobre la base de datos."""
    try:
        sql_content = sql_file.read_text(encoding="utf-8")
        statements = [statement.strip() for statement in sql_content.split(";") if statement.strip()]

        if not statements:
            click.echo("El archivo no contiene sentencias SQL ejecutables.")
            return

        click.echo(f"Ejecutando {len(statements)} sentencias desde {sql_file}...")
        with engine.begin() as conn:
            for statement in statements:
                preview = statement.replace("\n", " ")
                if len(preview) > 60:
                    preview = f"{preview[:57]}..."
                click.echo(f"- {preview}")
                conn.execute(text(statement))
        click.echo("Archivo SQL ejecutado satisfactoriamente.")
    except Exception as exc:  # pragma: no cover - CLI feedback
        raise click.ClickException(f"Error al ejecutar SQL: {exc}") from exc


@cli.command("export-schema")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Archivo de salida opcional.")
def export_schema(output: Path | None) -> None:
    """Exporta el esquema actual de la base de datos."""
    try:
        inspector = inspect(engine)
        tables = [table for table in inspector.get_table_names() if table != "alembic_version"]

        schema_lines: list[str] = ["-- Esquema exportado", f"-- Total de tablas: {len(tables)}", ""]
        for table in tables:
            schema_lines.append(f"-- Tabla: {table}")
            schema_lines.append(f"CREATE TABLE {table} (")

            columns = inspector.get_columns(table)
            pk_info = inspector.get_pk_constraint(table)
            pk_columns = set(pk_info.get("constrained_columns", []))

            column_lines = []
            for column in columns:
                line = f"    {column['name']} {column['type']}"
                if not column.get("nullable", True):
                    line += " NOT NULL"
                default_value = column.get("default")
                if default_value is not None:
                    line += f" DEFAULT {default_value}"
                if column["name"] in pk_columns:
                    line += " PRIMARY KEY"
                column_lines.append(line)

            schema_lines.append(",\n".join(column_lines))
            schema_lines.append(");\n")

        schema_text = "\n".join(schema_lines)

        if output:
            output.write_text(schema_text, encoding="utf-8")
            click.echo(f"Esquema exportado a {output}.")
        else:
            click.echo(schema_text)
    except Exception as exc:  # pragma: no cover - CLI feedback
        raise click.ClickException(f"Error al exportar esquema: {exc}") from exc


if __name__ == "__main__":
    cli()
