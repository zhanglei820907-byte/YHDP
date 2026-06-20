import csv
import io
import random
import sqlite3
import time
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
    """创建 answers / gad7_answers / students / psqi_answers 表"""
    conn = get_db()
    cursor = conn.cursor()

    # PHQ-9 答案表
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

    # GAD-7 答案表
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

    # 学生表（学号唯一，用于重复提交限制与 UID 生成）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            student_name TEXT NOT NULL,
            uid TEXT NOT NULL,
            first_submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PSQI 匹兹堡睡眠质量指数答案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS psqi_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            uid TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER,
            q5 INTEGER, q6 INTEGER, q7 INTEGER, q8 INTEGER,
            q9 INTEGER, q10 INTEGER, q11 INTEGER, q12 INTEGER,
            q13 INTEGER, q14 INTEGER, q15 INTEGER, q16 INTEGER,
            q17 INTEGER, q18 INTEGER, q19 INTEGER,
            total_score INTEGER,
            risk_level TEXT,
            time_start DATETIME,
            time_end DATETIME,
            valid_flag BOOLEAN
        )
    """)

    conn.commit()
    conn.close()


def generate_uid():
    """生成唯一 UID：YHDP + 毫秒时间戳 + 3位随机数"""
    timestamp = str(int(time.time() * 1000))
    rand_num = str(random.randint(100, 999))
    return f"YHDP{timestamp}{rand_num}"


# ============================================================
#  量表计分函数
# ============================================================

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


# ---- PSQI 计分 ----

def _map_sum_to_0_3(total, thresholds):
    """将总分按阈值映射为 0-3"""
    for i, t in enumerate(thresholds):
        if total <= t:
            return i
    return 3


def calc_psqi_scores(q1, q2, q3, q4, q5, q6, q7, q8, q9,
                      q10, q11, q12, q13, q14, q15, q16, q17, q18, q19):
    """
    PSQI 7 维度计分。
    题目映射（19 个自评题目 → 7 个维度）：

    维度 1 睡眠质量:   q15（总体睡眠质量）→ 直接得分 0-3
    维度 2 入睡时间:   q2（入睡时长）+ q5（5a: 30min 内不能入睡）→ 求和映射 0-3
    维度 3 睡眠时长:   q4（实际睡眠小时）→ 直接得分 0-3
    维度 4 睡眠效率:   q1（上床时间）、q3（起床时间）、q4（睡眠小时）→ 计算效率后映射 0-3
    维度 5 睡眠障碍:   q6~q14（5b-5j，共 9 项）→ 求和映射 0-3
    维度 6 药物使用:   q16（催眠药物）→ 直接得分 0-3
    维度 7 日间障碍:   q17（困倦）+ q18（精力不足）→ 求和映射 0-3
    （q19 为室友/同床者观察题，不参与计分）
    """
    # C1 睡眠质量：q15 直接得分
    c1 = q15

    # C2 入睡时间：q2 + q5 → 映射 (0:0, 1-2:1, 3-4:2, 5-6:3)
    c2_raw = q2 + q5
    c2 = _map_sum_to_0_3(c2_raw, [0, 2, 4])

    # C3 睡眠时长：q4 直接得分
    c3 = q4

    # C4 睡眠效率：由 q1（上床时间）、q3（起床时间）、q4（睡眠时长）估算
    bedtime_map   = {0: 21.0, 1: 22.5, 2: 23.5, 3: 25.0}   # 25 = 凌晨 1 点
    waketime_map  = {0:  5.5, 1:  6.5, 2:  7.5, 3:  8.5}
    sleep_hour_map = {0: 7.5, 1: 6.5, 2: 5.5, 3: 4.5}

    bed_hour = bedtime_map.get(q1, 22.5)
    wake_hour = waketime_map.get(q3, 6.5)
    actual_sleep = sleep_hour_map.get(q4, 6.5)

    time_in_bed = wake_hour - (bed_hour % 24)
    if time_in_bed <= 0:
        time_in_bed += 24

    if time_in_bed > 0:
        efficiency = (actual_sleep / time_in_bed) * 100
    else:
        efficiency = 0

    if efficiency >= 85:
        c4 = 0
    elif efficiency >= 75:
        c4 = 1
    elif efficiency >= 65:
        c4 = 2
    else:
        c4 = 3

    # C5 睡眠障碍：q6~q14（9 项 5b-5j）求和映射 (0:0, 1-9:1, 10-18:2, 19-27:3)
    c5_raw = q6 + q7 + q8 + q9 + q10 + q11 + q12 + q13 + q14
    c5 = _map_sum_to_0_3(c5_raw, [0, 9, 18])

    # C6 药物使用：q16 直接得分
    c6 = q16

    # C7 日间功能障碍：q17 + q18 求和映射 (0:0, 1-2:1, 3-4:2, 5-6:3)
    c7_raw = q17 + q18
    c7 = _map_sum_to_0_3(c7_raw, [0, 2, 4])

    total = c1 + c2 + c3 + c4 + c5 + c6 + c7
    return total


def get_psqi_risk_level(score):
    """根据 PSQI 总分返回睡眠质量等级"""
    if score <= 4:
        return "睡眠质量良好"
    elif score <= 10:
        return "睡眠质量一般"
    elif score <= 15:
        return "睡眠质量较差"
    else:
        return "睡眠质量极差"


# ============================================================
#  路由
# ============================================================

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
    """PHQ-9 问卷填写页面"""
    return render_template("survey.html")


@app.route("/submit", methods=["POST"])
def submit():
    """处理 PHQ-9 问卷提交"""
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


# ============================================================
#  PSQI 匹兹堡睡眠质量指数
# ============================================================

@app.route("/psqi_survey")
def psqi_survey():
    """PSQI 睡眠质量问卷填写页面"""
    return render_template("psqi_survey.html")


@app.route("/psqi_submit", methods=["POST"])
def psqi_submit():
    """
    处理 PSQI 问卷提交：
    - 学号重复检查（查 students 表）
    - 7 维度计分 → 总分 0-21 + 风险等级
    - 秒答检测（<10s → valid_flag=0）
    - UID 生成
    """
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    if not student_id or not student_name:
        return "学号和姓名为必填项", 400

    # 收集 19 题得分（0-3）
    scores = []
    for i in range(1, 20):
        try:
            val = int(request.form.get(f"q{i}", "0"))
            scores.append(max(0, min(3, val)))
        except (ValueError, TypeError):
            scores.append(0)

    # 7 维度计分
    total_score = calc_psqi_scores(*scores)
    risk_level = get_psqi_risk_level(total_score)

    # 秒答检测
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

    # 学号重复检查
    existing = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()

    if existing:
        conn.close()
        return "该学号已提交过问卷，无需重复填写。"

    # 生成 UID，写入 students 表
    uid = generate_uid()
    cursor.execute(
        "INSERT INTO students (student_id, student_name, uid) VALUES (?, ?, ?)",
        (student_id, student_name, uid),
    )

    # 写入 psqi_answers 表
    cursor.execute("""
        INSERT INTO psqi_answers
            (student_id, student_name, uid,
             q1, q2, q3, q4, q5, q6, q7, q8, q9,
             q10, q11, q12, q13, q14, q15, q16, q17, q18, q19,
             total_score, risk_level, time_start, time_end, valid_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, student_name, uid,
        scores[0], scores[1], scores[2], scores[3], scores[4],
        scores[5], scores[6], scores[7], scores[8], scores[9],
        scores[10], scores[11], scores[12], scores[13], scores[14],
        scores[15], scores[16], scores[17], scores[18],
        total_score, risk_level,
        start_time_str if time_start_dt else None,
        time_end_str,
        valid_flag
    ))
    conn.commit()
    conn.close()

    return render_template(
        "psqi_result.html",
        student_id=student_id,
        student_name=student_name,
        total_score=total_score,
        risk_level=risk_level,
        valid_flag=valid_flag,
        uid=uid
    )


# ============================================================
#  导出与统计
# ============================================================

@app.route("/export")
def export_csv():
    """导出 CSV 文件（含 PHQ-9、GAD-7、PSQI 三个量表数据）"""
    conn = get_db()
    cursor = conn.cursor()

    output = io.StringIO()
    writer = csv.writer(output)

    # ---- PHQ-9 数据 ----
    cursor.execute("""
        SELECT a.*, s.uid
        FROM answers a
        LEFT JOIN students s ON a.student_id = s.student_id
        ORDER BY a.id
    """)
    rows = cursor.fetchall()

    writer.writerow([
        "id", "student_id", "student_name", "uid",
        "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9",
        "total_score", "risk_level", "time_start", "time_end", "valid_flag"
    ])
    for row in rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"], row["uid"],
            row["q1"], row["q2"], row["q3"], row["q4"], row["q5"],
            row["q6"], row["q7"], row["q8"], row["q9"],
            row["total_score"], row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    # ---- GAD-7 数据 ----
    writer.writerow([])
    cursor.execute("""
        SELECT g.*, s.uid
        FROM gad7_answers g
        LEFT JOIN students s ON g.student_id = s.student_id
        ORDER BY g.id
    """)
    gad7_rows = cursor.fetchall()

    writer.writerow([
        "gad7_id", "gad7_student_id", "gad7_student_name", "uid",
        "g1", "g2", "g3", "g4", "g5", "g6", "g7",
        "gad7_total_score", "gad7_risk_level",
        "gad7_time_start", "gad7_time_end", "gad7_valid_flag"
    ])
    for row in gad7_rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"], row["uid"],
            row["g1"], row["g2"], row["g3"], row["g4"], row["g5"],
            row["g6"], row["g7"],
            row["total_score"], row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    # ---- PSQI 数据 ----
    writer.writerow([])
    cursor.execute("""
        SELECT p.*, s.uid
        FROM psqi_answers p
        LEFT JOIN students s ON p.student_id = s.student_id
        ORDER BY p.id
    """)
    psqi_rows = cursor.fetchall()

    writer.writerow([
        "psqi_id", "student_id", "student_name", "uid",
        "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9",
        "q10", "q11", "q12", "q13", "q14", "q15", "q16", "q17", "q18", "q19",
        "total_score", "risk_level", "time_start", "time_end", "valid_flag"
    ])
    for row in psqi_rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"], row["uid"],
            row["q1"], row["q2"], row["q3"], row["q4"], row["q5"],
            row["q6"], row["q7"], row["q8"], row["q9"], row["q10"],
            row["q11"], row["q12"], row["q13"], row["q14"], row["q15"],
            row["q16"], row["q17"], row["q18"], row["q19"],
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
    """统计页面（含 PHQ-9、GAD-7、PSQI 三个量表）"""
    conn = get_db()
    cursor = conn.cursor()

    # PHQ-9 统计
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

    # PSQI 统计
    cursor.execute("SELECT COUNT(*) as cnt FROM psqi_answers")
    psqi_total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM psqi_answers WHERE valid_flag = 1")
    psqi_valid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM psqi_answers WHERE valid_flag = 0")
    psqi_invalid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(total_score) as avg_score FROM psqi_answers WHERE valid_flag = 1")
    psqi_avg_row = cursor.fetchone()
    psqi_avg = round(psqi_avg_row["avg_score"], 1) if psqi_avg_row["avg_score"] else 0

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
        gad7_avg=gad7_avg,
        psqi_total=psqi_total,
        psqi_valid=psqi_valid,
        psqi_invalid=psqi_invalid,
        psqi_avg=psqi_avg
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
