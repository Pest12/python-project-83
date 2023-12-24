import psycopg2
import validators
import os
from flask import Flask, render_template, request, flash, redirect, url_for, get_flashed_messages
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import date
from psycopg2.extras import NamedTupleCursor
from contextlib import contextmanager


load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@contextmanager
def connect_database(url):
    try:
        connection = psycopg2.connect(url)
        yield connection
    except Exception:
        if connection:
            connection.rollback()
        raise
    else:
        if connection:
            connection.commit()
    finally:
        if connection:
            connection.close()


def create_url(connection, name):
    current_date = date.today()
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
           """INSERT INTO urls (name, created_at)
              VALUES (%s, %s) RETURNING id;
              """, (name, current_date)
        )
        return cursor.fetchone()[0]


def get_all_urls(connection):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT id, name, created_at
               FROM urls
               ORDER BY created_at DESC;"""
        )
        return cursor.fetchall()


def get_url_by_name(connection, name):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE name = %s;
               """, (name,))
        return cursor.fetchone()


def get_url_by_id(connection, id):
    with connection.cursor(cursor_factory=NamedTupleCursor) as cursor:
        cursor.execute(
            """SELECT * FROM urls
               WHERE id = %s;
               """, (id,))
        return cursor.fetchone()


@app.errorhandler(404)
def not_found(error):
    return 'Oops!', 404


@app.route("/")
def index():
    return render_template('index.html')


def validate(url):
    errors = {}
    if len(url) > 255:
        errors['url'] = "URL превышает 255 символов"
    if validators.url(url):
        errors['url'] = "Некорректный URL"
    if not url:
        errors['url'] = "Введите URL"
    return errors


@app.route("/urls")
def urls():
    with connect_database(DATABASE_URL) as conn:
        urls = get_all_urls(conn)
    return render_template(
        '/urls.html',
        urls=urls,
    )


@app.post("/urls")
def add_url():
    url_name = request.form.get('url')
    errors = validate(url_name)
    if errors:
        return render_template(
            'index.html',
        ), 422
    parsed_url = urlparse(url_name)
    normalized_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
    with connect_database(DATABASE_URL) as conn:
        check_url = get_url_by_name(conn, normalized_url)
        if check_url:
            flash('Страница уже существует', 'info')
            return redirect(url_for('url_info', id=check_url[0]))
        url_id = create_url(conn, normalized_url)
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('url_info', id=url_id))


@app.route("/urls/int:<id>")
def url_info(id):
    messages = get_flashed_messages(with_categories=True)
    with connect_database(DATABASE_URL) as conn:
        url = get_url_by_id(conn, id)
    return render_template(
        'url_id.html',
        messages=messages,
        url=url,
    )
