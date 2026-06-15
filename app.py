import csv
import io
import sqlite3
from datetime import datetime, timezone
from flask import Flask, render_template, request, make_response

app = Flask(__name__)

DATABASE = "database.db"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """创建 answers 表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER,
            q5 INTEGER, q6 INTEGER, q7 INTEGER, q8 INTEGER, q9 INTEGER,
            total_score INTEGER,
            risk_level TEXT,
            time_start DATETIME,
            time_end DATETIME,
            valid_flag BOOLEAN
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gad7_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            g1 INTEGER, g2 INTEGER, g3 INTEGER, g4 INTEGER,
            g5 INTEGER, g6 INTEGER, g7 INTEGER,
            total_score INTEGER,
            risk_level TEXT,
            time_start DATETIME,
            time_end DATETIME,
            valid_flag BOOLEAN
        )
    """)
    conn.commit()
    conn.close()


def get_risk_level(score):
    """根据 PHQ-9 总分返回风险等级"""
    if score <= 4:
        return "正常"
    elif score <= 9:
        return "轻度"
    elif score <= 14:
        return "中度"
    elif score <= 19:
        return "中重度"
    else:
        return "重度"


def get_gad7_risk_level(score):
    """根据 GAD-7 总分返回风险等级"""
    if score <= 4:
        return "正常"
    elif score <= 9:
        return "轻度"
    elif score <= 14:
        return "中度"
    else:
        return "重度"


@app.route("/")
def index():
    return "YHDP 问卷系统 - 测试成功"


@app.route("/init_db")
def init_db_route():
    """初始化数据库"""
    init_db()
    return "Database initialized"


@app.route("/survey")
def survey():
    """问卷填写页面"""
    return render_template("survey.html")


@app.route("/submit", methods=["POST"])
def submit():
    """处理问卷提交"""
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    scores = []
    for i in range(1, 10):
        try:
            val = int(request.form.get(f"q{i}", "0"))
            scores.append(max(0, min(3, val)))
        except (ValueError, TypeError):
            scores.append(0)

    total_score = sum(scores)
    risk_level = get_risk_level(total_score)

    time_end = datetime.now(timezone.utc)
    time_end_str = time_end.isoformat()

    elapsed_seconds = 0
    time_start_dt = None
    if start_time_str:
        try:
            time_start_dt = datetime.fromisoformat(start_time_str)
            elapsed_seconds = int((time_end - time_start_dt).total_seconds())
        except (ValueError, TypeError):
            pass

    valid_flag = elapsed_seconds >= 10 if time_start_dt else False

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO answers
            (student_id, student_name, q1, q2, q3, q4, q5, q6, q7, q8, q9,
             total_score, risk_level, time_start, time_end, valid_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, student_name,
        scores[0], scores[1], scores[2], scores[3], scores[4],
        scores[5], scores[6], scores[7], scores[8],
        total_score, risk_level,
        start_time_str if time_start_dt else None,
        time_end_str,
        valid_flag
    ))
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        student_id=student_id,
        student_name=student_name,
        total_score=total_score,
        risk_level=risk_level,
        valid_flag=valid_flag
    )


@app.route("/gad7_survey")
def gad7_survey():
    """GAD-7 焦虑量表填写页面"""
    return render_template("gad7_survey.html")


@app.route("/gad7_submit", methods=["POST"])
def gad7_submit():
    """处理 GAD-7 问卷提交"""
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    scores = []
    for i in range(1, 8):
        try:
            val = int(request.form.get(f"g{i}", "0"))
            scores.append(max(0, min(3, val)))
        except (ValueError, TypeError):
            scores.append(0)

    total_score = sum(scores)
    risk_level = get_gad7_risk_level(total_score)

    time_end = datetime.now(timezone.utc)
    time_end_str = time_end.isoformat()

    elapsed_seconds = 0
    time_start_dt = None
    if start_time_str:
        try:
            time_start_dt = datetime.fromisoformat(start_time_str)
            elapsed_seconds = int((time_end - time_start_dt).total_seconds())
        except (ValueError, TypeError):
            pass

    valid_flag = elapsed_seconds >= 10 if time_start_dt else False

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO gad7_answers
            (student_id, student_name, g1, g2, g3, g4, g5, g6, g7,
             total_score, risk_level, time_start, time_end, valid_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, student_name,
        scores[0], scores[1], scores[2], scores[3], scores[4],
        scores[5], scores[6],
        total_score, risk_level,
        start_time_str if time_start_dt else None,
        time_end_str,
        valid_flag
    ))
    conn.commit()
    conn.close()

    return render_template(
        "gad7_result.html",
        student_id=student_id,
        student_name=student_name,
        total_score=total_score,
        risk_level=risk_level,
        valid_flag=valid_flag
    )


@app.route("/export")
def export_csv():
    """导出 CSV 文件"""
    conn = get_db()
    cursor = conn.cursor()

    output = io.StringIO()
    writer = csv.writer(output)

    # PHQ-9 数据
    cursor.execute("SELECT * FROM answers ORDER BY id")
    rows = cursor.fetchall()

    writer.writerow([
        "id", "student_id", "student_name",
        "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9",
        "total_score", "risk_level", "time_start", "time_end", "valid_flag"
    ])

    for row in rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"],
            row["q1"], row["q2"], row["q3"], row["q4"], row["q5"],
            row["q6"], row["q7"], row["q8"], row["q9"],
            row["total_score"], row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    # GAD-7 数据
    writer.writerow([])
    writer.writerow([
        "gad7_id", "gad7_student_id", "gad7_student_name",
        "g1", "g2", "g3", "g4", "g5", "g6", "g7",
        "gad7_total_score", "gad7_risk_level",
        "gad7_time_start", "gad7_time_end", "gad7_valid_flag"
    ])

    cursor.execute("SELECT * FROM gad7_answers ORDER BY id")
    gad7_rows = cursor.fetchall()

    for row in gad7_rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"],
            row["g1"], row["g2"], row["g3"], row["g4"], row["g5"],
            row["g6"], row["g7"],
            row["total_score"], row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    conn.close()
    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=yhdp_data.csv"
    return response


@app.route("/stats")
def stats():
    """统计页面"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM answers")
    total_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM answers WHERE valid_flag = 1")
    valid_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM answers WHERE valid_flag = 0")
    invalid_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(total_score) as avg_score FROM answers WHERE valid_flag = 1")
    avg_row = cursor.fetchone()
    avg_score = round(avg_row["avg_score"], 1) if avg_row["avg_score"] else 0

    # GAD-7 统计
    cursor.execute("SELECT COUNT(*) as cnt FROM gad7_answers")
    gad7_total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM gad7_answers WHERE valid_flag = 1")
    gad7_valid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM gad7_answers WHERE valid_flag = 0")
    gad7_invalid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(total_score) as avg_score FROM gad7_answers WHERE valid_flag = 1")
    gad7_avg_row = cursor.fetchone()
    gad7_avg = round(gad7_avg_row["avg_score"], 1) if gad7_avg_row["avg_score"] else 0

    conn.close()

    return render_template(
        "stats.html",
        total_count=total_count,
        valid_count=valid_count,
        invalid_count=invalid_count,
        avg_score=avg_score,
        gad7_total=gad7_total,
        gad7_valid=gad7_valid,
        gad7_invalid=gad7_invalid,
        gad7_avg=gad7_avg
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
