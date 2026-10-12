from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import Error


app = Flask(__name__)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="pranathi@123",
        database="movie_ticket_booking",
        port=3306
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# MOVIES
# =========================================================

@app.route("/movies")
def movies():

    search = request.args.get("search", "")
    genre = request.args.get("genre", "")
    language = request.args.get("language", "")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT *
        FROM movies
        WHERE 1=1
    """

    params = []

    # Search by movie title
    if search:
        query += " AND title LIKE %s"
        params.append(f"%{search}%")

    # Filter by genre
    if genre:
        query += " AND genre = %s"
        params.append(genre)

    # Filter by language
    if language:
        query += " AND language = %s"
        params.append(language)

    query += " ORDER BY title"

    cursor.execute(query, params)

    movies = cursor.fetchall()

    # Get genres
    cursor.execute("""
        SELECT DISTINCT genre
        FROM movies
        WHERE genre IS NOT NULL
        AND genre != ''
        ORDER BY genre
    """)

    genres = [row["genre"] for row in cursor.fetchall()]

    # Get languages
    cursor.execute("""
        SELECT DISTINCT language
        FROM movies
        WHERE language IS NOT NULL
        AND language != ''
        ORDER BY language
    """)

    languages = [row["language"] for row in cursor.fetchall()]

    cursor.close()
    connection.close()

    return render_template(
        "movies.html",
        movies=movies,
        search=search,
        genre=genre,
        language=language,
        genres=genres,
        languages=languages
    )


# =========================================================
# SHOWS
# =========================================================

@app.route("/shows/<int:movie_id>")
def shows(movie_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            s.show_id,
            s.show_date,
            s.show_time,
            s.theater,
            s.price,
            m.title
        FROM shows s
        JOIN movies m
            ON s.movie_id = m.movie_id
        WHERE m.movie_id = %s
        ORDER BY s.show_date, s.show_time
    """

    cursor.execute(query, (movie_id,))

    shows = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "shows.html",
        shows=shows
    )


# =========================================================
# BOOK TICKET
# =========================================================

@app.route("/book/<int:show_id>", methods=["GET", "POST"])
def book(show_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # -----------------------------------------------------
    # Get show information
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            s.show_id,
            s.show_date,
            s.show_time,
            s.theater,
            s.price,
            m.title
        FROM shows s
        JOIN movies m
            ON s.movie_id = m.movie_id
        WHERE s.show_id = %s
    """, (show_id,))

    show = cursor.fetchone()

    # If show does not exist
    if not show:
        cursor.close()
        connection.close()
        return "Show not found."


    # -----------------------------------------------------
    # Get already booked seats
    # -----------------------------------------------------

    cursor.execute("""
        SELECT seat_number
        FROM bookings
        WHERE show_id = %s
    """, (show_id,))

    booked_seats = [
        row["seat_number"]
        for row in cursor.fetchall()
    ]


    # -----------------------------------------------------
    # POST - Book Ticket
    # -----------------------------------------------------

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        seat = request.form["seat"]


        # -------------------------------------------------
        # Check if seat is already booked
        # -------------------------------------------------

        if seat in booked_seats:

            cursor.close()
            connection.close()

            return """
            <h2 style="text-align:center; margin-top:50px;">
                ❌ Sorry, this seat is already booked.
            </h2>

            <p style="text-align:center;">
                <a href="/book/{}">
                    ← Choose another seat
                </a>
            </p>
            """.format(show_id)


        # -------------------------------------------------
        # Check if user already exists
        # -------------------------------------------------

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()


        if user:

            user_id = user["user_id"]

        else:

            cursor.execute("""
                INSERT INTO users
                (name, email, phone)
                VALUES (%s, %s, %s)
            """, (
                name,
                email,
                phone
            ))

            user_id = cursor.lastrowid


        # -------------------------------------------------
        # Insert booking safely
        # -------------------------------------------------

        try:

            cursor.execute("""
                INSERT INTO bookings
                (user_id, show_id, seat_number, total_amount)
                VALUES (%s, %s, %s, %s)
            """, (
                user_id,
                show_id,
                seat,
                show["price"]
            ))

            connection.commit()

            booking_id = cursor.lastrowid

            cursor.close()
            connection.close()

            return redirect(
                url_for(
                    "booking_success",
                    booking_id=booking_id
                )
            )


        except Error:

            connection.rollback()

            cursor.close()
            connection.close()

            return """
            <h2 style="text-align:center; margin-top:50px;">
                ❌ Sorry, this seat has already been booked.
            </h2>

            <p style="text-align:center;">
                <a href="/book/{}">
                    ← Choose another seat
                </a>
            </p>
            """.format(show_id)


    # -----------------------------------------------------
    # GET - Show booking page
    # -----------------------------------------------------

    cursor.close()
    connection.close()

    return render_template(
        "book.html",
        show=show,
        booked_seats=booked_seats
    )


# =========================================================
# BOOKING SUCCESS
# =========================================================

@app.route("/booking-success/<int:booking_id>")
def booking_success(booking_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            b.booking_id,
            b.seat_number,
            b.booking_date,
            b.total_amount,
            u.name,
            u.email,
            u.phone,
            m.title,
            s.show_date,
            s.show_time,
            s.theater
        FROM bookings b
        JOIN users u
            ON b.user_id = u.user_id
        JOIN shows s
            ON b.show_id = s.show_id
        JOIN movies m
            ON s.movie_id = m.movie_id
        WHERE b.booking_id = %s
    """, (booking_id,))

    booking = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template(
        "booking_success.html",
        booking=booking
    )


# =========================================================
# BOOKING HISTORY
# =========================================================

@app.route("/bookings")
def bookings():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            b.booking_id,
            u.name,
            u.email,
            m.title,
            s.theater,
            s.show_date,
            s.show_time,
            b.seat_number,
            b.total_amount,
            b.booking_date
        FROM bookings b
        JOIN users u
            ON b.user_id = u.user_id
        JOIN shows s
            ON b.show_id = s.show_id
        JOIN movies m
            ON s.movie_id = m.movie_id
        ORDER BY b.booking_date DESC
    """

    cursor.execute(query)

    bookings = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "bookings.html",
        bookings=bookings
    )


# =========================================================
# CANCEL BOOKING
# =========================================================

@app.route(
    "/cancel-booking/<int:booking_id>",
    methods=["POST"]
)
def cancel_booking(booking_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM bookings WHERE booking_id = %s",
        (booking_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(
        url_for("bookings")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Total movies
    cursor.execute(
        "SELECT COUNT(*) AS total_movies FROM movies"
    )

    total_movies = cursor.fetchone()["total_movies"]


    # Total shows
    cursor.execute(
        "SELECT COUNT(*) AS total_shows FROM shows"
    )

    total_shows = cursor.fetchone()["total_shows"]


    # Total bookings
    cursor.execute(
        "SELECT COUNT(*) AS total_bookings FROM bookings"
    )

    total_bookings = cursor.fetchone()["total_bookings"]


    cursor.close()
    connection.close()

    return render_template(
        "admin.html",
        total_movies=total_movies,
        total_shows=total_shows,
        total_bookings=total_bookings
    )


# =========================================================
# ADD MOVIE
# =========================================================

@app.route(
    "/admin/add-movie",
    methods=["GET", "POST"]
)
def add_movie():

    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        title = request.form["title"]
        genre = request.form["genre"]
        language = request.form["language"]
        duration = request.form["duration"]
        release_date = request.form["release_date"]

        cursor.execute("""
            INSERT INTO movies
            (title, genre, language, duration, release_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            title,
            genre,
            language,
            duration,
            release_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for("movies")
        )


    cursor.close()
    connection.close()

    return render_template(
        "add_movie.html"
    )


# =========================================================
# ADD SHOW
# =========================================================

@app.route(
    "/admin/add-show",
    methods=["GET", "POST"]
)
def add_show():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        movie_id = request.form["movie_id"]
        show_date = request.form["show_date"]
        show_time = request.form["show_time"]
        theater = request.form["theater"]
        price = request.form["price"]

        cursor.execute("""
            INSERT INTO shows
            (movie_id, show_date, show_time, theater, price)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            movie_id,
            show_date,
            show_time,
            theater,
            price
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for("movies")
        )


    cursor.execute("""
        SELECT movie_id, title
        FROM movies
        ORDER BY title
    """)

    movies = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "add_show.html",
        movies=movies
    )


# =========================================================
# DELETE MOVIE
# =========================================================

@app.route(
    "/admin/delete-movie/<int:movie_id>",
    methods=["POST"]
)
def delete_movie(movie_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM movies WHERE movie_id = %s",
        (movie_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(
        url_for("movies")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
