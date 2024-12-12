from flask import Flask, render_template, request, redirect, url_for, jsonify
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

    # 동아리원 목록
    sql_members = "SELECT student_id, name, major, contact, status, role FROM ClubMember WHERE club_name = %s"
    cur.execute(sql_members, (club_name,))
    members = cur.fetchall()

    # 동아리 활동
    sql_activity = "SELECT activity_name, date, activity_type, location FROM Activity WHERE club_name = %s"
    cur.execute(sql_activity, (club_name,))
    activities = cur.fetchall() or [] 

    # 동아리 수상 이력 쿼리 수정
    sql_award = """
    SELECT A.award_name, A.prize, A.date, CM.name 
    FROM Award A
    JOIN ClubMember CM ON A.student_id = CM.student_id
    WHERE A.club_name = %s
    """
    cur.execute(sql_award, (club_name,))
    awards = cur.fetchall() or []
    
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
    
    # 활동 참여자 목록 추가
    sql_ac_participants = """
        SELECT AP.activity_name, CM.name, AP.participation_date
        FROM ActivityParticipant AP
        JOIN ClubMember CM ON AP.student_id = CM.student_id
        WHERE AP.activity_name IN (SELECT activity_name FROM Activity WHERE club_name = %s)
    """
    cur.execute(sql_ac_participants, (club_name,))
    ac_participants = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'club.html',
        club=club,
        club_name=club_name,
        executives=executives,
        activities=activities,
        awards=awards,
        budgets=budgets,
        records=records,
        members=members,
        ac_participants=ac_participants
    )

@app.route('/add_member', methods=['POST'])
def add_member():
    try:
        # 데이터 수집
        student_id = request.form['student_id']
        name = request.form['name']
        major = request.form['major']
        contact = request.form['contact']
        status = request.form['status']
        club_name = request.form['club_name']
        role = request.form['role']  # 직책 정보 추가
        term_year = request.form.get('term_year')  # 임원 임기를 선택적으로 수집 (없으면 None)

        # 데이터베이스 연결
        conn = get_db_connection()
        cur = conn.cursor()

        # ClubMember 테이블에 데이터 삽입
        sql_insert_member = """
        INSERT INTO ClubMember (student_id, name, major, contact, status, club_name, role)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql_insert_member, (student_id, name, major, contact, status, club_name, role))

        # 만약 직책이 '회장', '부회장', '임원'이라면 Executive 테이블에 추가
        if role in ['회장', '부회장', '임원']:
            if not term_year:  # 임기 연도가 누락된 경우 기본값 설정 (현재 연도)
                from datetime import datetime
                term_year = datetime.now().year

            sql_insert_executive = """
            INSERT INTO Executive (position, term_year, student_id, club_name)
            VALUES (%s, %s, %s, %s)
            """
            cur.execute(sql_insert_executive, (role, term_year, student_id, club_name))

        # 변경 사항 커밋 및 연결 종료
        conn.commit()
        cur.close()
        conn.close()

        # 동아리 상세 페이지로 리다이렉트
        return redirect(url_for('club', club_name=club_name))

    except pymysql.MySQLError as e:
        # 데이터베이스 오류 처리
        conn.rollback()  # 트랜잭션 롤백
        return jsonify({"message": f"데이터베이스 오류 발생: {str(e)}"}), 500

    except Exception as e:
        # 일반적인 오류 처리
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/delete_member', methods=['POST'])
def delete_member():
    try:
        student_id = request.json.get('student_id')
        if not student_id:
            return jsonify({"message": "student_id가 전달되지 않았습니다!"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "DB 연결 실패!"}), 500

        cur = conn.cursor()
        sql = "DELETE FROM ClubMember WHERE student_id = %s"
        cur.execute(sql, (student_id,))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "동아리원이 성공적으로 삭제되었습니다!"})
    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/add_activity', methods=['POST'])
def add_activity():
    try:     
        
        activity_name = request.form['activity_name']
        date = request.form['date']
        activity_type = request.form['activity_type']
        location = request.form['location']
        club_name = request.form['club_name']

        if not all([activity_name, date, activity_type, location, club_name]):
            return jsonify({"message": "필수 항목이 누락되었습니다!"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        sql_check = "SELECT COUNT(*) FROM Activity WHERE activity_name = %s AND club_name = %s"
        cur.execute(sql_check, (activity_name, club_name))
        if cur.fetchone()[0] > 0:
            return jsonify({"message": "이미 존재하는 활동입니다!"}), 400

        sql = """
        INSERT INTO Activity (activity_name, date, activity_type, location, club_name)
        VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(sql, (activity_name, date, activity_type, location, club_name))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "활동이 성공적으로 추가되었습니다!"}), 200

    except pymysql.MySQLError as e:
        conn.rollback()  # 트랜잭션 롤백
        return jsonify({"message": f"데이터베이스 오류 발생: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500



@app.route('/delete_activity', methods=['POST'])
def delete_activity():
    try:
        activity_name = request.json.get('activity_name')
        if not activity_name:
            return jsonify({"message": "activity_name가 전달되지 않았습니다!"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "DB 연결 실패!"}), 500

        cur = conn.cursor()

        # 참여 인원 데이터 먼저 삭제
        sql_del_participant = "DELETE FROM ActivityParticipant  WHERE activity_name = %s"
        cur.execute(sql_del_participant, (activity_name,))
        # 이후 행사 데이터 삭제
        sql_del_activity = "DELETE FROM Activity WHERE activity_name = %s"
        cur.execute(sql_del_activity, (activity_name,))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "동아리 활동이 성공적으로 삭제되었습니다!"})
    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/add_budget', methods=['POST'])
def add_budget():
    try:
        budget_name = request.form['budget_name']
        budget_date = request.form['date']
        amount = request.form['amount']
        details = request.form['details']
        club_name = request.form['club_name']

        conn = get_db_connection()
        cur = conn.cursor()

        sql = """
        INSERT INTO Budget (budget_name, date, amount, details, club_name)
        VALUES (%s, %s, %s, %s, %s)
        """
        cur.execute(sql, (budget_name, budget_date, amount, details, club_name))
        conn.commit()

        cur.close()
        conn.close()

        return redirect(url_for('club', club_name=club_name))

    except pymysql.MySQLError as e:
        conn.rollback() 
        return jsonify({"message": f"데이터베이스 오류 발생: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/delete_budget', methods=['POST'])
def delete_budget():
    try:
        # 요청 데이터 수집
        budget_name = request.json.get('budget_name')
        date = request.json.get('date')
        
        # 필수 데이터 확인
        if not budget_name or not date:
            return jsonify({"message": "budget_name과 date가 모두 전달되어야 합니다!"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "DB 연결 실패!"}), 500

        cur = conn.cursor()

        # 예산과 관련된 데이터 먼저 삭제 (예: 예산 사용 내역)
        sql_del_budget_details = "DELETE FROM BudgetDetails WHERE budget_name = %s AND date = %s"
        cur.execute(sql_del_budget_details, (budget_name, date))

        # 이후 예산 내역 삭제
        sql_del_budget = "DELETE FROM Budget WHERE budget_name = %s AND date = %s"
        cur.execute(sql_del_budget, (budget_name, date))

        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "예산 내역이 성공적으로 삭제되었습니다!"})
    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500


@app.route('/delete_award', methods=['POST'])
def delete_award():
    try:
        award_name = request.json.get('award_name')
        if not award_name:
            return jsonify({"message": "award_name가 전달되지 않았습니다!"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"message": "DB 연결 실패!"}), 500

        cur = conn.cursor()

        # 대회 참여 인원 데이터 먼저 삭제
        sql_del_participant = "DELETE FROM AwardParticipant WHERE award_name = %s"
        cur.execute(sql_del_participant, (award_name,))
        # 이후 대회 데이터 삭제
        sql_del_award = "DELETE FROM Award WHERE award_name = %s"
        cur.execute(sql_del_award, (award_name,))
        conn.commit()

        cur.close()
        conn.close()
        return jsonify({"message": "동아리 활동이 성공적으로 삭제되었습니다!"})
    except Exception as e:
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/add_ac_participation', methods=['POST'])
def add_ac_participation():
    try:
        # 요청 데이터 수집
        activity_name = request.form['activity_name']
        student_id = request.form['student_id']
        participation_date = request.form['ac_participation_date']  # 수정된 필드 이름
        club_name = request.form['club_name']

        # 데이터베이스 연결
        conn = get_db_connection()
        cur = conn.cursor()

        # ActivityParticipant 테이블에 데이터 삽입
        sql = """
        INSERT INTO ActivityParticipant (activity_name, student_id, participation_date)
        VALUES (%s, %s, %s)
        """
        cur.execute(sql, (activity_name, student_id, participation_date))
        conn.commit()

        # 연결 종료
        cur.close()
        conn.close()

        # 클럽 세부 페이지로 리다이렉트
        return redirect(url_for('club', club_name=club_name))

    except pymysql.MySQLError as e:
        # 데이터베이스 오류 처리
        conn.rollback()  # 트랜잭션 롤백
        return jsonify({"message": f"데이터베이스 오류 발생: {str(e)}"}), 500

    except Exception as e:
        # 일반적인 오류 처리
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500

@app.route('/delete_ac_participation', methods=['POST'])
def delete_ac_participation():
    try:
        # 요청 데이터 수집
        activity_name = request.json.get('activity_name')
        student_id = request.json.get('student_id')
        participation_date = request.json.get('participation_date')

        # 필수 데이터 확인
        if not activity_name or not student_id or not participation_date:
            return jsonify({"message": "activity_name, student_id, participation_date가 모두 전달되어야 합니다!"}), 400

        # 데이터베이스 연결
        conn = get_db_connection()
        cur = conn.cursor()

        # ActivityParticipant 테이블에서 해당 참여자 삭제
        sql = """
        DELETE FROM ActivityParticipant
        WHERE activity_name = %s AND student_id = %s AND participation_date = %s
        """
        cur.execute(sql, (activity_name, student_id, participation_date))
        conn.commit()  # 트랜잭션 커밋

        # 삭제 후 해당 참여 기록이 존재하는지 확인 (삭제 확인용)
        cur.execute("""
        SELECT * FROM ActivityParticipant WHERE activity_name = %s AND student_id = %s AND participation_date = %s
        """, (activity_name, student_id, participation_date))
        
        deleted_record = cur.fetchone()
        if deleted_record:
            return jsonify({"message": "삭제 실패, 데이터가 여전히 존재합니다."}), 500

        # 연결 종료
        cur.close()
        conn.close()

        return jsonify({"message": "활동 참여자가 성공적으로 삭제되었습니다!"})

    except pymysql.MySQLError as e:
        # 데이터베이스 오류 처리
        conn.rollback()  # 트랜잭션 롤백
        return jsonify({"message": f"데이터베이스 오류 발생: {str(e)}"}), 500

    except Exception as e:
        # 일반적인 오류 처리
        return jsonify({"message": f"오류 발생: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
