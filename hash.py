import hashlib
import sqlite3
from typing import TypedDict

from flask import jsonify


def setup_db():
    conn = sqlite3.connect("mpesa_hashes.db")
    cursor = conn.cursor()
    # "WITHOUT ROWID" makes the database smaller and faster for primary key lookups
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rainbow_table (
            hash TEXT PRIMARY KEY,
            msisdn TEXT
        ) WITHOUT ROWID
    """)
    conn.commit()
    return conn


def populate_range(conn, prefix, start=0, end=999999):
    cursor = conn.cursor()
    batch = []
    print(f"Generating hashes for prefix {prefix}...")

    for i in range(start, end + 1):
        # Format: 254 + prefix + 6 digits (e.g., 254 722 000001)
        msisdn = f"254{prefix}{i:06d}"
        msisdn_hash = hashlib.sha256(msisdn.encode()).hexdigest()
        batch.append((msisdn_hash, msisdn))

        # Insert in batches of 50,000 for high performance
        if len(batch) >= 50000:
            cursor.executemany(
                "INSERT OR IGNORE INTO rainbow_table VALUES (?, ?)", batch
            )
            conn.commit()
            batch = []
            print(f"Progress: {i}/{end}")

    # Final commit for remaining items
    if batch:
        cursor.executemany("INSERT OR IGNORE INTO rainbow_table VALUES (?, ?)", batch)
        conn.commit()


def execute_sql(sql: str, params: str | int | None, multiple: bool = True):
    """Provide a query, its parameters if the query is dynamic,
    and the multiple tag which is true or false to fetch as many records as possible"""
    conn = sqlite3.connect("mpesa_hashes.db")
    cursor = conn.cursor()
    cursor.execute(sql, (params,))
    return cursor.fetchmany() if multiple else cursor.fetchone()


def decode(target_hash: str):
    query = "SELECT msisdn FROM rainbow_table WHERE hash = ?"
    result = execute_sql(query, target_hash, False)
    return result[0] if result else jsonify(
        {"error": "Hash not found in local DB"}
    ), 400


class TableDataSize(TypedDict):
    limit: int
    page_size: int | None
    input_search: str | None


# Collect the decoded number as a hashed number and then reuse it.
def define_table_data(params: TableDataSize):
    # extract the parameters from the dictionary
    limit = params["limit"] if params["limit"] > 0 else 20
    page_size = params["page_size"] if params["page_size"] else 50
    input_search = params["input_search"]
    search_text = None if not input_search else f"where hash ={input_search}"

    query = f"select msisdn, hash from rainbow_table {search_text} limit {limit} offet {page_size} "
    execute_sql(query, None, True)


def data_table_size():
    query = "select count(msisdn) as `no_of_values` from rainbow_table"
    execute_sql(query, None, True)
