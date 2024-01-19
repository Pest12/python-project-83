from datetime import date
from psycopg2.extras import NamedTupleCursor


def create_url(connection, name):
    current_date = date.today()
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """INSERT INTO urls (name, created_at)
                VALUES (%s, %s) RETURNING id;
            """, (name, current_date)
        )
        return cursor.fetchone()[0]


def get_all_urls_and_last_check(connection):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT urls.id, urls.name,
                url_checks.created_at,
                url_checks.status_code
                FROM urls
                LEFT OUTER JOIN url_checks
                ON urls.id = url_checks.url_id
                AND url_checks.id = (
                    SELECT MAX(id)
                    FROM url_checks
                    WHERE url_checks.url_id = urls.id
                )
                ORDER BY urls.id DESC;
            """
        )
        return cursor.fetchall()


def get_url_by_name(connection, name):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE name = %s;
            """, (name,)
        )
        return cursor.fetchone()


def get_url_by_id(connection, id):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE id = %s;
            """, (id,)
        )
        return cursor.fetchone()


def create_check(connection, id, status_code, h1, title, description):
    current_date = date.today()
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """INSERT INTO url_checks (
                url_id, status_code, h1, title, description, created_at)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (id, status_code, h1, title, description, current_date,)
        )


def get_all_checks(connection, id):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM url_checks
                WHERE url_id = %s
                ORDER BY id DESC;
            """, (id,)
        )
        return cursor.fetchall()
