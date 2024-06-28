from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import datetime

app = Flask(__name__)
app.secret_key = '07b07178cffdec6daa9619b079793ea5c13ec01ba65b777d'  # Add a secret key for session management

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'library_db'

mysql = MySQL(app)

#welcome page
@app.route('/')
def index():
    return render_template('welcome.html')


#dashboard(admin or student)
@app.route('/dashboard', methods=['POST'])
def dashboard():
    role = request.form['role']
    session['role'] = role
    if role == 'admin':
        return redirect(url_for('admin_login'))
    elif role == 'student':
        return redirect(url_for('student_login'))
    return render_template('dashboard.html', role=role)


#admin_login page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s AND role = %s', (username, password, 'admin'))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['role'] = 'admin'
            flash('Admin login successful!')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password!')
    return render_template('admin_login.html')


#admin_dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'loggedin' in session and session['role'] == 'admin':
        return render_template('dashboard.html', role='admin')
    return redirect(url_for('admin_login'))

#student_login page
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s AND role = %s', (username, password, 'student'))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['user_id'] = account['id']  # Ensure user_id is stored in the session
            session['role'] = 'student'
            flash('Student login successful!')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password!')
    return render_template('student_login.html')


#student_dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'loggedin' in session and session['role'] == 'student':
        return render_template('dashboard.html', role='student')
    return redirect(url_for('student_login'))


#add_book functionality
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        isbn = request.form['isbn']
        available_copies = request.form['available_copies']
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO books (title, author, genre, isbn, available_copies) VALUES (%s, %s, %s, %s,%s)', (title, author, genre, isbn, available_copies))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('view_books'))
    return render_template('add_book.html')


#view_books functionality
@app.route('/view_books')
def view_books():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    cursor.close()
    return render_template('view_books.html', books=books, role=session.get('role'))

#issue_book functionality
@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        book_id = request.form['book_id']
        user_id = request.form['user_id']
        return_date = request.form['return_date']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        #  to fetch available copies before issuing the book
        cursor.execute('SELECT available_copies FROM books WHERE id = %s', (book_id,))
        book = cursor.fetchone()
        if not book:
            flash('Book not found!')
            return redirect(url_for('issue_book'))
        
        available_copies = book['available_copies']
        
        #  to check if the book is available
        if available_copies <= 0:
            flash('This book is not available for issuance!')
            return redirect(url_for('issue_book'))

        
        cursor.execute('UPDATE books SET available_copies = %s WHERE id = %s', (available_copies - 1, book_id))
        cursor.execute('INSERT INTO issues (book_id, user_id, issue_date, return_date) VALUES (%s, %s, NOW(), %s)', (book_id, user_id, return_date))
        mysql.connection.commit()
        
        cursor.close()
        flash('Book issued successfully!')
        return redirect(url_for('view_issues'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, title FROM books')
    books = cursor.fetchall()
    cursor.execute('SELECT id, username AS name FROM users')
    users = cursor.fetchall()
    cursor.close()
    return render_template('issue_book.html', books=books, users=users)


#view_issues functionality in admin page
@app.route('/view_issues')
def view_issues():
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT issues.id, books.title, users.username, issues.issue_date, issues.return_date, issues.returned
                      FROM issues 
                      JOIN books ON issues.book_id = books.id 
                      JOIN users ON issues.user_id = users.id''')
    issues = cursor.fetchall()

    cursor.execute('''SELECT reservations.id, books.title, users.username, reservations.issue_date, reservations.return_date 
                      FROM reservations 
                      JOIN books ON reservations.book_id = books.id 
                      JOIN users ON reservations.user_id = users.id''')
    reservations = cursor.fetchall()

    cursor.close()
    return render_template('view_issues.html', issues=issues, reservations=reservations)


#search_book functionality
@app.route('/search_books', methods=['GET', 'POST'])
def search_books():
    if session.get('role') != 'student' or 'loggedin' not in session:
        return redirect(url_for('index'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        genre = request.form['genre']
        search_query = request.form['search_query']
        
        if genre and search_query:
            cursor.execute('SELECT * FROM books WHERE genre = %s AND (title LIKE %s OR author LIKE %s)', 
                           (genre, '%' + search_query + '%', '%' + search_query + '%'))
        elif genre:
            cursor.execute('SELECT * FROM books WHERE genre = %s', (genre,))
        elif search_query:
            cursor.execute('SELECT * FROM books WHERE title LIKE %s OR author LIKE %s', 
                           ('%' + search_query + '%', '%' + search_query + '%'))
        else:
            cursor.execute('SELECT * FROM books')
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    cursor.close()

    books_by_genre = {}
    genres = set()
    for book in books:
        genre = book['genre']
        genres.add(genre)
        if genre not in books_by_genre:
            books_by_genre[genre] = []
        books_by_genre[genre].append(book)

    return render_template('search_books.html', books_by_genre=books_by_genre, genres=sorted(genres))


#reserve_book functionality
@app.route('/reserve_book/<int:book_id>', methods=['GET', 'POST'])
def reserve_book(book_id):
    if 'loggedin' not in session:
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()

    if not book:
        flash('Book not found!')
        return redirect(url_for('search_books'))

    if request.method == 'POST' and session.get('role') == 'student':
       
        if book.get('available_copies', 0) > 0:
            #  to decrease available copies and mark book as reserved
            cursor.execute('UPDATE books SET available_copies = available_copies - 1 WHERE id = %s', (book_id,))
            mysql.connection.commit()

            
            issue_date = datetime.datetime.now().date()
            return_date = request.form['return_date']
            user_id = session['user_id']  

            cursor.execute('INSERT INTO reservations (book_id, user_id, issue_date, return_date) VALUES (%s, %s, %s, %s)',
                           (book_id, user_id, issue_date, return_date))
            mysql.connection.commit()

            flash('Book reserved successfully!')
            return redirect(url_for('search_books'))
        else:
            flash('Book is not available for reservation!')
            return redirect(url_for('search_books'))

    return render_template('reserve_book.html', book=book)


#delete_book functionality in admin
@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
    mysql.connection.commit()
    cursor.close()

    flash('Book deleted successfully!')
    return redirect(url_for('view_books'))


#view_student_issue details in student page
@app.route('/view_student_issues')
def view_student_issues():
    if 'loggedin' not in session or session['role'] != 'student':
        return redirect(url_for('index'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    
    cursor.execute('''SELECT issues.id, books.title, issues.issue_date, issues.return_date 
                      FROM issues 
                      JOIN books ON issues.book_id = books.id 
                      WHERE issues.user_id = %s AND issues.returned = 0''', (user_id,))
    issues = cursor.fetchall()

    
    cursor.execute('''SELECT books.title, reservations.issue_date, reservations.return_date 
                      FROM reservations 
                      JOIN books ON reservations.book_id = books.id 
                      WHERE reservations.user_id = %s''', (user_id,))
    reservations = cursor.fetchall()

    cursor.close()
    return render_template('view_student_issues.html', issues=issues, reservations=reservations)



#overdue_books in admin page
@app.route('/overdue_books')
def overdue_books():
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))

   
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT issues.id, issues.book_id, books.title, users.username, issues.issue_date, issues.return_date 
                      FROM issues 
                      JOIN books ON issues.book_id = books.id 
                      JOIN users ON issues.user_id = users.id 
                      WHERE issues.return_date < CURDATE()''')
    overdue_books = cursor.fetchall()
    cursor.close()

    return render_template('overdue_books.html', overdue_books=overdue_books)

#send_reminder page 
@app.route('/send_reminder/<int:issue_id>', methods=['POST'])
def send_reminder(issue_id):
    if session.get('role') != 'admin' or 'loggedin' not in session:
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT issues.*, users.username, books.title 
        FROM issues 
        JOIN users ON issues.user_id = users.id 
        JOIN books ON issues.book_id = books.id 
        WHERE issues.id = %s
    ''', (issue_id,))
    issue = cursor.fetchone()

    if not issue:
        flash('Issue not found!')
        return redirect(url_for('overdue_books'))

    due_date = issue['return_date']
    days_overdue = (datetime.datetime.now().date() - due_date).days
    fine_amount = days_overdue  

    message = f"Dear {issue['username']},\n\nThis is a reminder that your book '{issue['title']}' was due on {due_date}. " \
              f"Please return it at your earliest convenience. Your fine amount is ${fine_amount}."

    # Debug: Print the reminder message
    print(f"Message: {message}")

    # Save the reminder message to the database
    cursor.execute('INSERT INTO reminders (user_id, message) VALUES (%s, %s)', (issue['user_id'], message))
    mysql.connection.commit()

    flash('Reminder sent successfully!')
    return redirect(url_for('overdue_books'))



#view_message functionality
@app.route('/view_messages')
def view_messages():
    if 'loggedin' not in session or session.get('role') != 'student':
        flash('You need to log in as a student to view messages.')
        return redirect(url_for('index'))
    
    user_id = session.get('id')
    if not user_id:
        flash('User ID not found in session!')
        return redirect(url_for('index'))

    # Debug: Print the user ID and session info
    print(f"User ID: {user_id}")
    print(f"Session Info: {session}")

    # Fetch messages for the user
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM reminders WHERE user_id = %s', (user_id,))
    messages = cursor.fetchall()
    cursor.close()

    # Debug: Print the fetched messages
    print(f"Messages: {messages}")

    return render_template('view_messages.html', messages=messages)

#return_book functionality
@app.route('/return_book/<int:issue_id>', methods=['POST'])
def return_book(issue_id):
    if 'loggedin' not in session or session['role'] != 'student':
        flash('You are not authorized to return books.')
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor()
    
   
    cursor.execute('SELECT * FROM issues WHERE id = %s', (issue_id,))
    issue = cursor.fetchone()

    if not issue:
        flash('Issue not found!')
        return redirect(url_for('view_student_issues'))

    cursor.execute('UPDATE issues SET returned = TRUE WHERE id = %s', (issue_id,))
    mysql.connection.commit()
    cursor.close()

    flash('Book returned successfully!')
    return redirect(url_for('view_student_issues'))

@app.route('/debug_session')
def debug_session():
    return f"Session Data: {session}"


if __name__ == '__main__':
    app.run(debug=True)
