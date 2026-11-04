"""Parse-level guardrails for LLM-written SQL (sqlglot), applied before anything executes.

Layer 1 (here): exactly one statement, read-only SELECT, only known marts tables, no risky
functions, LIMIT added if missing.
Layer 2 (database, sql/postgres/roles.sql): runs as crickql_reader, a read-only role with
SELECT on marts only and a 10 second statement timeout.
Either layer alone should stop a bad query. Both exist because each can have a gap.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
SCHEMA = "marts"

# Functions that read files, sleep, touch other databases, change settings or leak server info.
BLOCKED_FUNCTIONS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until", "pg_read_file", "pg_read_binary_file",
    "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export", "dblink", "dblink_exec",
    "set_config", "current_setting", "pg_terminate_backend", "pg_cancel_backend",
    "pg_reload_conf", "query_to_xml", "version", "inet_server_addr",
}
WRITE_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Grant, exp.Copy, exp.Into, exp.Set, exp.Transaction,
    exp.Commit, exp.Rollback, exp.Lock,
)


class GuardrailError(ValueError):
    """The SQL was refused before execution. The message is safe to show the model."""


def check_sql(sql: str, allowed_tables: set[str], dialect: str = "postgres") -> str:
    """Return a safe, normalised version of `sql` or raise GuardrailError."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise GuardrailError("Empty SQL.")
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as e:
        raise GuardrailError(f"SQL does not parse: {str(e).splitlines()[0]}") from e
    if len(statements) != 1:
        raise GuardrailError(f"Exactly one statement allowed, got {len(statements)}.")
    tree = statements[0]

    if not isinstance(tree, exp.Query):
        raise GuardrailError(f"Only SELECT queries are allowed, got {tree.key.upper()}.")
    for node in tree.walk():
        if isinstance(node, WRITE_NODES):
            raise GuardrailError(f"{node.key.upper()} is not allowed, read-only queries only.")
        if isinstance(node, exp.Func):
            name = (node.sql_name() if not isinstance(node, exp.Anonymous) else node.name).lower()
            if name in BLOCKED_FUNCTIONS:
                raise GuardrailError(f"Function {name}() is not allowed.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        db = (table.db or "").lower()
        if not name:  # e.g. a table function like generate_series in FROM
            raise GuardrailError("Only marts tables can appear in FROM / JOIN.")
        if not db and name in cte_names:
            continue
        if db and db != SCHEMA:
            raise GuardrailError(f"Schema '{db}' is not allowed. Use marts tables only.")
        if name not in allowed_tables:
            raise GuardrailError(
                f"Unknown table '{name}'. Allowed: {', '.join(sorted(allowed_tables))}."
            )
        table.set("db", exp.to_identifier(SCHEMA))

    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(DEFAULT_LIMIT)
    else:
        try:
            n = int(limit.expression.this)
        except (AttributeError, TypeError, ValueError):
            raise GuardrailError("LIMIT must be a plain number.") from None
        if n > MAX_LIMIT:
            tree = tree.limit(MAX_LIMIT)
    return tree.sql(dialect=dialect)
