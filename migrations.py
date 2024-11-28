from lnbits.db import Connection


async def m001_initial(db: Connection):
    """
    Initial paywalls table.
    """
    await db.execute(
        f"""
        CREATE TABLE paywall.paywalls (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            secret TEXT NOT NULL,
            url TEXT NOT NULL,
            memo TEXT NOT NULL,
            amount {db.big_int} NOT NULL,
            time TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """
        );
    """
    )


async def m002_redux(db: Connection):
    """
    Creates an improved paywalls table and migrates the existing data.
    """
    await db.execute("ALTER TABLE paywall.paywalls RENAME TO paywalls_old")

    await db.execute(
        f"""
        CREATE TABLE paywall.paywalls (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            url TEXT NOT NULL,
            memo TEXT NOT NULL,
            description TEXT NULL,
            amount {db.big_int} DEFAULT 0,
            time TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """,
            remembers INTEGER DEFAULT 0,
            extras TEXT NULL
        );
    """
    )

    await db.execute(
        "INSERT INTO paywall.paywalls "
        "SELECT id, wallet, url, memo, description, amount, time FROM paywall.paywalls_old"
    )
    await db.execute("DROP TABLE paywall.paywalls_old")
