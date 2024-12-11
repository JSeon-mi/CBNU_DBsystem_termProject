from flask import Flask, render_template, request, abort
import pymysql

app = Flask(__name__)

# MySQL 연결 #
def get_db_connection():
    try:
        conn = pymysql.connect(
            host="192.168.56.109",
            port=4567,
            user="root",
            password="1234",
            db="SWclub",
            charset="utf8"
        )
        return conn
    except pymysql.MySQLError as e:
        print("Database connection error:", e)
        return None

### 메인 페이지 ###
@app.route('/')
def index():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    cur = conn.cursor()
    sql = "SELECT club_name, club_type FROM Club"
    cur.execute(sql)
    clubs = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', clubs=clubs)

### 동아리 세부 페이지 ###
@app.route('/club/<string:club_name>')
def club(club_name):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    cur = conn.cursor()

    # 동아리 기본 정보
    sql_club = "SELECT club_name, club_type, club_location, club_prof, estab_date FROM Club WHERE club_name = %s"
    cur.execute(sql_club, (club_name,))
    club = cur.fetchone()

    # 동아리 임원 정보 (이름, 학번 포함)
    sql_executive = """
        SELECT E.position, E.term_year, E.student_id, CM.name
        FROM Executive E
        JOIN ClubMember CM ON E.student_id = CM.student_id
        WHERE E.club_name = %s
    """
    cur.execute(sql_executive, (club_name,))
    executives = cur.fetchall()

    # 동아리 활동
    sql_activity = "SELECT activity_name, date, activity_type, location FROM Activity WHERE club_name = %s"
    cur.execute(sql_activity, (club_name,))
    activities = cur.fetchall()

    # 동아리 예산
    sql_budget = "SELECT budget_name, date, amount, details FROM Budget WHERE club_name = %s"
    cur.execute(sql_budget, (club_name,))
    budgets = cur.fetchall()

    # 참여 기록
    sql_record = """
        SELECT CM.name, AP.activity_name, AP.participation_date 
        FROM ActivityParticipant AP
        JOIN ClubMember CM ON AP.student_id = CM.student_id
        WHERE AP.activity_name IN (SELECT activity_name FROM Activity WHERE club_name = %s)
    """
    cur.execute(sql_record, (club_name,))
    records = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'club.html',
        club=club,
        executives=executives,
        activities=activities,
        budgets=budgets,
        records=records
    )


### 동아리 활동 세부 정보 ###
@app.route('/club/<string:club_name>/<string:category>')
def club_category(club_name, category):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    cur = conn.cursor()

    if category == 'activity':
        sql = "SELECT activity_name, date, activity_type, location FROM Activity WHERE club_name = %s"
        cur.execute(sql, (club_name,))
    elif category == 'member':
        sql = "SELECT student_id, name, major, contact, status, role FROM ClubMember WHERE club_name = %s"
        cur.execute(sql, (club_name,))
    elif category == 'budget':
        sql = "SELECT budget_name, date, amount, details FROM Budget WHERE club_name = %s"
        cur.execute(sql, (club_name,))
    elif category == 'award':
        sql = "SELECT award_name, prize, date, student_id FROM Award WHERE club_name = %s"
        cur.execute(sql, (club_name,))
    else:
        cur.close()
        conn.close()
        return "Invalid category", 400

    results = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('category.html', category=category, results=results)

### 활동 참여 정보 ###
@app.route('/activity/<string:activity_name>/participants')
def activity_participants(activity_name):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    cur = conn.cursor()
    sql = """
        SELECT AP.student_id, CM.name, AP.participation_date 
        FROM ActivityParticipant AP
        JOIN ClubMember CM ON AP.student_id = CM.student_id
        WHERE AP.activity_name = %s
    """
    cur.execute(sql, (activity_name,))
    participants = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('participants.html', activity_name=activity_name, participants=participants)

### 수상 참여 정보 ###
@app.route('/award/<string:award_name>/participants')
def award_participants(award_name):
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500

    cur = conn.cursor()
    sql = """
        SELECT AP.student_id, CM.name, AP.award_date
        FROM AwardParticipant AP
        JOIN ClubMember CM ON AP.student_id = CM.student_id
        WHERE AP.award_name = %s
    """
    cur.execute(sql, (award_name,))
    participants = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('award_participants.html', award_name=award_name, participants=participants)

if __name__ == "__main__":
    app.run(debug=True)
