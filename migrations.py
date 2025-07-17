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
    - add description
    - add remembers
    - add extras
    - drop secret
    """
    await db.execute("ALTER TABLE paywall.paywalls RENAME TO paywalls_m001")

    await db.execute(
        f"""
        CREATE TABLE paywall.paywalls (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            url TEXT NOT NULL,
            memo TEXT NOT NULL,
            description TEXT NULL,
            amount {db.big_int} DEFAULT 0,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            remembers INTEGER DEFAULT 0,
            extras TEXT NULL
        );
        """
    )

    await db.execute(
        """
        INSERT INTO paywall.paywalls
        SELECT id, wallet, url, memo, NULL, amount, time, 0, NULL
        FROM paywall.paywalls_m001
        """
    )
    await db.execute("DROP TABLE paywall.paywalls_m001")


async def m003_add_fiat_amount(db: Connection):
    """
    Add currency to paywalls to allow fiat denomination and make amount a float.
    """
    await db.execute("ALTER TABLE paywall.paywalls RENAME TO paywalls_m002")
    await db.execute(
        f"""
        CREATE TABLE paywall.paywalls (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            url TEXT NOT NULL,
            memo TEXT NOT NULL,
            description TEXT NULL,
            amount FLOAT DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'sat',
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            remembers INTEGER DEFAULT 0,
            extras TEXT NULL
        );
        """
    )
    await db.execute(
        """
        INSERT INTO paywall.paywalls
        SELECT
            id,
            wallet,
            url,
            memo,
            description,
            amount,
            'sat',
            time,
            remembers,
            extras
        FROM paywall.paywalls_m002
        """
    )
    await db.execute("DROP TABLE paywall.paywalls_m002")
