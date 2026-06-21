import csv
import io
import random
import sqlite3
import time
from datetime import datetime, timezone
from flask import Flask, render_template, request, make_response, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "yhdp_secret_key_2026_health_profile"

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
    # 迁移: 为已有 students 表添加 birth_date 和 last_login 列
    for col, col_type in [("birth_date", "TEXT"), ("last_login", "DATETIME")]:
        try:
            cursor.execute(f"ALTER TABLE students ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # 列已存在

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

    # KIDMED 地中海饮食质量指数答案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kidmed_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            uid TEXT,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER,
            q5 INTEGER, q6 INTEGER, q7 INTEGER, q8 INTEGER,
            q9 INTEGER, q10 INTEGER, q11 INTEGER, q12 INTEGER,
            q13 INTEGER, q14 INTEGER, q15 INTEGER, q16 INTEGER,
            total_score INTEGER,
            risk_level TEXT,
            time_start DATETIME,
            time_end DATETIME,
            valid_flag BOOLEAN
        )
    """)

    # 体格测试数据表（教师端录入）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS physical_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            uid TEXT,
            measure_date DATE,
            grip_left_1 REAL, grip_left_2 REAL, grip_left_3 REAL,
            grip_right_1 REAL, grip_right_2 REAL, grip_right_3 REAL,
            grip_left_best REAL, grip_right_best REAL, grip_avg_best REAL,
            grip_dominant INTEGER,
            waist_circ REAL,
            weight REAL, bmi REAL,
            body_fat_rate REAL, body_fat_mass REAL,
            muscle_mass REAL, skeletal_muscle REAL,
            bone_mass REAL,
            body_water_rate REAL, body_water_mass REAL,
            protein_rate REAL, protein_mass REAL,
            bmr REAL,
            visceral_fat INTEGER,
            subcut_fat_rate REAL,
            body_age INTEGER,
            body_type INTEGER,
            heart_rate INTEGER,
            body_score INTEGER,
            measure_operator TEXT,
            data_complete INTEGER DEFAULT 0,
            data_quality_note TEXT,
            measure_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 家庭体力活动支持量表答案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_support_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            uid TEXT,
            mother_self_ex INTEGER, father_self_ex INTEGER,
            mother_joint_ex INTEGER, father_joint_ex INTEGER,
            mother_invites INTEGER, father_invites INTEGER,
            mother_transport INTEGER, father_transport INTEGER,
            mother_registers INTEGER, father_registers INTEGER,
            mother_watches INTEGER, father_watches INTEGER,
            mother_tv_limit INTEGER, father_tv_limit INTEGER,
            mother_computer_limit INTEGER, father_computer_limit INTEGER,
            mother_game_limit INTEGER, father_game_limit INTEGER,
            mother_total INTEGER, father_total INTEGER, family_total INTEGER,
            risk_level TEXT,
            time_start DATETIME, time_end DATETIME, valid_flag BOOLEAN
        )
    """)

    # 运动认知量表答案表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cognition_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT NOT NULL,
            uid TEXT,
            c1 INTEGER, c2 INTEGER, c3 INTEGER, c4 INTEGER, c5 INTEGER,
            c6 INTEGER, c7 INTEGER, c8 INTEGER, c9 INTEGER, c10 INTEGER,
            c11 INTEGER, c12 INTEGER, c13 INTEGER, c14 INTEGER, c15 INTEGER,
            c16 INTEGER, c17 INTEGER, c18 INTEGER, c19 INTEGER, c20 INTEGER,
            c21 INTEGER, c22 INTEGER, c23 INTEGER, c24 INTEGER, c25 INTEGER,
            c26 INTEGER, c27 INTEGER, c28 INTEGER, c29 INTEGER, c30 INTEGER,
            c31 INTEGER, c32 INTEGER, c33 INTEGER, c34 INTEGER, c35 INTEGER,
            c36 INTEGER, c37 INTEGER, c38 INTEGER, c39 INTEGER, c40 INTEGER,
            c41 INTEGER, c42 INTEGER, c43 INTEGER,
            dimension1_benefit INTEGER,
            dimension2_barrier INTEGER,
            dimension3_family INTEGER,
            dimension4_self_efficacy INTEGER,
            total_score INTEGER,
            risk_level TEXT,
            time_start DATETIME, time_end DATETIME, valid_flag BOOLEAN
        )
    """)

    # 预警规则表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            description TEXT,
            source_table TEXT NOT NULL,
            source_field TEXT NOT NULL,
            operator TEXT NOT NULL,
            threshold REAL NOT NULL,
            alert_level TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 预警记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            rule_id INTEGER NOT NULL,
            alert_level TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_score REAL NOT NULL,
            triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT '待处理',
            note TEXT
        )
    """)

    # 科学锻炼知识库
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT,
            category TEXT NOT NULL,
            video_url TEXT,
            image_url TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # 插入预置规则（如不存在）
    default_rules = [
        ("重度抑郁风险", "PHQ-9总分≥20", "answers", "total_score", ">=", 20, "高危"),
        ("中度抑郁风险", "PHQ-9总分≥15", "answers", "total_score", ">=", 15, "中危"),
        ("重度焦虑风险", "GAD-7总分≥20", "gad7_answers", "total_score", ">=", 20, "高危"),
        ("中度焦虑风险", "GAD-7总分≥15", "gad7_answers", "total_score", ">=", 15, "中危"),
        ("睡眠质量差", "PSQI总分≥11", "psqi_answers", "total_score", ">=", 11, "中危"),
        ("饮食质量较差", "KIDMED总分≤3", "kidmed_answers", "total_score", "<=", 3, "低危"),
    ]
    for name, desc, tbl, fld, op, thresh, level in default_rules:
        exists = cursor.execute(
            "SELECT id FROM alert_rules WHERE rule_name = ? AND source_table = ?",
            (name, tbl)
        ).fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO alert_rules (rule_name, description, source_table, source_field, operator, threshold, alert_level) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, desc, tbl, fld, op, thresh, level)
            )

    conn.commit()
    conn.close()


def generate_uid():
    """生成唯一 UID：YHDP + 毫秒时间戳 + 3位随机数"""
    timestamp = str(int(time.time() * 1000))
    rand_num = str(random.randint(100, 999))
    return f"YHDP{timestamp}{rand_num}"


def check_and_create_alerts(student_id, source_table, score):
    """
    预警规则引擎：根据学生得分检查所有激活规则，触发生成预警记录。
    返回本次触发的预警数量。
    """
    conn = get_db()
    cursor = conn.cursor()

    rules = cursor.execute(
        """SELECT * FROM alert_rules
           WHERE is_active = 1 AND source_table = ?""",
        (source_table,)
    ).fetchall()

    triggered = 0
    for rule in rules:
        op = rule["operator"]
        threshold = rule["threshold"]
        match = False

        if op == ">=" and score >= threshold:
            match = True
        elif op == "<=" and score <= threshold:
            match = True
        elif op == ">" and score > threshold:
            match = True
        elif op == "<" and score < threshold:
            match = True
        elif op == "==" and score == threshold:
            match = True

        if not match:
            continue

        # 检查是否已存在 待处理 的重复预警
        dup = cursor.execute(
            """SELECT id FROM alerts
               WHERE student_id = ? AND rule_id = ? AND status = '待处理'""",
            (student_id, rule["id"])
        ).fetchone()

        if dup:
            continue

        cursor.execute(
            """INSERT INTO alerts
               (student_id, rule_id, alert_level, source_table, source_score)
               VALUES (?, ?, ?, ?, ?)""",
            (student_id, rule["id"], rule["alert_level"], source_table, score)
        )
        triggered += 1

    conn.commit()
    conn.close()
    return triggered


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


# ---- KIDMED 计分 ----

# KIDMED 正负向题定义
KIDMED_POSITIVE = {1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12}
KIDMED_NEGATIVE = {6, 13, 14, 15, 16}


def calc_kidmed_score(scores):
    """
    KIDMED 计分（16 题，每题 0/1）。
    正向题 选"是"=1,"否"=0；负向题 选"是"=0,"否"=1。总分 0-16。
    """
    total = 0
    for i, val in enumerate(scores, start=1):
        if i in KIDMED_POSITIVE:
            total += val
        else:
            total += (1 - val)  # 负向反转
    return total


def get_kidmed_risk_level(score):
    """根据 KIDMED 总分返回饮食质量等级"""
    if score >= 8:
        return "饮食质量良好"
    elif score >= 4:
        return "需要改善"
    else:
        return "饮食质量较差"


# ---- 家庭支持计分 ----

# 反向题（需要 5 - raw 转换）；其余为正向题
FAMILY_REVERSE_KEYS = {
    "mother_tv_limit", "father_tv_limit",
    "mother_computer_limit", "father_computer_limit",
    "mother_game_limit", "father_game_limit",
}


def calc_family_support(raw_scores):
    """
    家庭体力活动支持量表计分（18 题，每题 1-4）。
    正向题直接计分；反向题 actual = 5 - raw。
    返回 (mother_total, father_total, family_total)。
    """
    scored = {}
    for key, raw in raw_scores.items():
        if key in FAMILY_REVERSE_KEYS:
            scored[key] = 5 - raw
        else:
            scored[key] = raw

    mother_total = sum(
        scored[k] for k in [
            "mother_self_ex", "mother_joint_ex", "mother_invites",
            "mother_transport", "mother_registers", "mother_watches",
            "mother_tv_limit", "mother_computer_limit", "mother_game_limit"
        ]
    )
    father_total = sum(
        scored[k] for k in [
            "father_self_ex", "father_joint_ex", "father_invites",
            "father_transport", "father_registers", "father_watches",
            "father_tv_limit", "father_computer_limit", "father_game_limit"
        ]
    )
    family_total = mother_total + father_total
    return mother_total, father_total, family_total


def get_family_risk_level(family_total):
    """根据家庭总支持分返回风险等级"""
    if family_total >= 54:
        return "高支持"
    elif family_total >= 36:
        return "中等支持"
    else:
        return "低支持"


# ---- 运动认知计分 ----

def calc_cognition_scores(c_list):
    """
    运动认知量表计分（43 题，每题 1-4）。
    D1 益处认知: c1-c18   (18题，正向)
    D2 障碍认知: c19-c30  (12题，反向: 5-raw)
    D3 家庭氛围: c31-c39  (9题，正向)
    D4 自我效能: c40-c43  (4题，正向)
    返回 (d1, d2, d3, d4, total)
    """
    d1 = sum(c_list[0:18])
    d2_raw = c_list[18:30]
    d2 = sum(5 - v for v in d2_raw)
    d3 = sum(c_list[30:39])
    d4 = sum(c_list[39:43])
    total = d1 + d2 + d3 + d4
    return d1, d2, d3, d4, total


def get_cognition_risk_level(score):
    """根据认知总分返回风险等级（43-172）"""
    if score >= 129:
        return "高水平"
    elif score >= 86:
        return "中等水平"
    else:
        return "低水平"


# ============================================================
#  路由
# ============================================================

@app.route("/")
def index():
    """统一入口页面"""
    return render_template("index.html")


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
    check_and_create_alerts(student_id, "answers", total_score)
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
    check_and_create_alerts(student_id, "gad7_answers", total_score)
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
    check_and_create_alerts(student_id, "psqi_answers", total_score)
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
#  KIDMED 地中海饮食质量指数
# ============================================================

@app.route("/kidmed_survey")
def kidmed_survey():
    """KIDMED 饮食质量问卷填写页面"""
    return render_template("kidmed_survey.html")


@app.route("/kidmed_submit", methods=["POST"])
def kidmed_submit():
    """
    处理 KIDMED 问卷提交：
    - 学号重复检查（查 students 表）
    - 正负向计分 → 总分 0-16 + 风险等级
    - 秒答检测（<10s → valid_flag=0）
    - UID 生成
    """
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    if not student_id or not student_name:
        return "学号和姓名为必填项", 400

    # 收集 16 题得分（0 或 1）
    scores = []
    for i in range(1, 17):
        try:
            val = int(request.form.get(f"q{i}", "0"))
            scores.append(max(0, min(1, val)))
        except (ValueError, TypeError):
            scores.append(0)

    # 正负向计分
    total_score = calc_kidmed_score(scores)
    risk_level = get_kidmed_risk_level(total_score)

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

    # 写入 kidmed_answers 表
    cursor.execute("""
        INSERT INTO kidmed_answers
            (student_id, student_name, uid,
             q1, q2, q3, q4, q5, q6, q7, q8,
             q9, q10, q11, q12, q13, q14, q15, q16,
             total_score, risk_level, time_start, time_end, valid_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, student_name, uid,
        scores[0], scores[1], scores[2], scores[3],
        scores[4], scores[5], scores[6], scores[7],
        scores[8], scores[9], scores[10], scores[11],
        scores[12], scores[13], scores[14], scores[15],
        total_score, risk_level,
        start_time_str if time_start_dt else None,
        time_end_str,
        valid_flag
    ))
    conn.commit()
    check_and_create_alerts(student_id, "kidmed_answers", total_score)
    conn.close()

    return render_template(
        "kidmed_result.html",
        student_id=student_id,
        student_name=student_name,
        total_score=total_score,
        risk_level=risk_level,
        valid_flag=valid_flag,
        uid=uid
    )


# ============================================================
#  家庭体力活动支持量表
# ============================================================

FAMILY_QUESTIONS = [
    ("mother_self_ex",  "母亲自己锻炼"),
    ("father_self_ex",  "父亲自己锻炼"),
    ("mother_joint_ex", "母亲与孩子一起锻炼"),
    ("father_joint_ex", "父亲与孩子一起锻炼"),
    ("mother_invites",  "母亲邀请孩子去锻炼"),
    ("father_invites",  "父亲邀请孩子去锻炼"),
    ("mother_transport","母亲接送孩子去运动场所"),
    ("father_transport","父亲接送孩子去运动场所"),
    ("mother_registers","母亲为孩子报名运动班"),
    ("father_registers","父亲为孩子报名运动班"),
    ("mother_watches",  "母亲观看孩子运动或比赛"),
    ("father_watches",  "父亲观看孩子运动或比赛"),
    ("mother_tv_limit", "母亲限制看电视时间"),
    ("father_tv_limit", "父亲限制看电视时间"),
    ("mother_computer_limit", "母亲限制用电脑时间"),
    ("father_computer_limit", "父亲限制用电脑时间"),
    ("mother_game_limit", "母亲限制玩电子游戏时间"),
    ("father_game_limit", "父亲限制玩电子游戏时间"),
]


@app.route("/family_support_survey")
def family_support_survey():
    """家庭体力活动支持量表填写页面"""
    return render_template("family_support_survey.html")


@app.route("/family_support_submit", methods=["POST"])
def family_support_submit():
    """处理家庭支持量表提交"""
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    if not student_id or not student_name:
        return "学号和姓名为必填项", 400

    # 收集 18 题原始得分（1-4），字段名与表列名一致
    raw_scores = {}
    for field, _label in FAMILY_QUESTIONS:
        try:
            val = int(request.form.get(field, "1"))
            raw_scores[field] = max(1, min(4, val))
        except (ValueError, TypeError):
            raw_scores[field] = 1

    # 计分
    mother_total, father_total, family_total = calc_family_support(raw_scores)
    risk_level = get_family_risk_level(family_total)

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

    # 生成 UID
    uid = generate_uid()
    cursor.execute(
        "INSERT INTO students (student_id, student_name, uid) VALUES (?, ?, ?)",
        (student_id, student_name, uid),
    )

    # 入库
    cursor.execute("""
        INSERT INTO family_support_answers (
            student_id, student_name, uid,
            mother_self_ex, father_self_ex,
            mother_joint_ex, father_joint_ex,
            mother_invites, father_invites,
            mother_transport, father_transport,
            mother_registers, father_registers,
            mother_watches, father_watches,
            mother_tv_limit, father_tv_limit,
            mother_computer_limit, father_computer_limit,
            mother_game_limit, father_game_limit,
            mother_total, father_total, family_total,
            risk_level, time_start, time_end, valid_flag
        ) VALUES (
            ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        student_id, student_name, uid,
        raw_scores["mother_self_ex"], raw_scores["father_self_ex"],
        raw_scores["mother_joint_ex"], raw_scores["father_joint_ex"],
        raw_scores["mother_invites"], raw_scores["father_invites"],
        raw_scores["mother_transport"], raw_scores["father_transport"],
        raw_scores["mother_registers"], raw_scores["father_registers"],
        raw_scores["mother_watches"], raw_scores["father_watches"],
        raw_scores["mother_tv_limit"], raw_scores["father_tv_limit"],
        raw_scores["mother_computer_limit"], raw_scores["father_computer_limit"],
        raw_scores["mother_game_limit"], raw_scores["father_game_limit"],
        mother_total, father_total, family_total,
        risk_level,
        start_time_str if time_start_dt else None,
        time_end_str, valid_flag
    ))
    conn.commit()
    check_and_create_alerts(student_id, "family_support_answers", family_total)
    conn.close()

    return render_template(
        "family_support_result.html",
        student_id=student_id, student_name=student_name,
        mother_total=mother_total, father_total=father_total,
        family_total=family_total, risk_level=risk_level,
        valid_flag=valid_flag, uid=uid
    )


# ============================================================
#  运动认知量表
# ============================================================

@app.route("/cognition_survey")
def cognition_survey():
    """运动认知量表填写页面"""
    return render_template("cognition_survey.html")


@app.route("/cognition_submit", methods=["POST"])
def cognition_submit():
    """处理运动认知量表提交"""
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()
    start_time_str = request.form.get("start_time", "")

    if not student_id or not student_name:
        return "学号和姓名为必填项", 400

    # 收集 43 题（1-4分）
    c_scores = []
    for i in range(1, 44):
        try:
            val = int(request.form.get(f"c{i}", "1"))
            c_scores.append(max(1, min(4, val)))
        except (ValueError, TypeError):
            c_scores.append(1)

    d1, d2, d3, d4, total = calc_cognition_scores(c_scores)
    risk_level = get_cognition_risk_level(total)

    time_end = datetime.now(timezone.utc)
    time_end_str = time_end.isoformat()
    elapsed = 0
    ts = None
    if start_time_str:
        try:
            ts = datetime.fromisoformat(start_time_str)
            elapsed = int((time_end - ts).total_seconds())
        except (ValueError, TypeError):
            pass
    valid_flag = elapsed >= 10 if ts else False

    conn = get_db()
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if existing:
        conn.close()
        return "该学号已提交过问卷，无需重复填写。"

    uid = generate_uid()
    cursor.execute(
        "INSERT INTO students (student_id, student_name, uid) VALUES (?, ?, ?)",
        (student_id, student_name, uid),
    )

    cursor.execute("""
        INSERT INTO cognition_answers (
            student_id, student_name, uid,
            c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,
            c11,c12,c13,c14,c15,c16,c17,c18,c19,c20,
            c21,c22,c23,c24,c25,c26,c27,c28,c29,c30,
            c31,c32,c33,c34,c35,c36,c37,c38,c39,c40,
            c41,c42,c43,
            dimension1_benefit, dimension2_barrier,
            dimension3_family, dimension4_self_efficacy,
            total_score, risk_level,
            time_start, time_end, valid_flag
        ) VALUES (
            ?, ?, ?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?
        )
    """, (
        student_id, student_name, uid,
        *c_scores,
        d1, d2, d3, d4, total, risk_level,
        start_time_str if ts else None, time_end_str, valid_flag
    ))
    conn.commit()
    check_and_create_alerts(student_id, "cognition_answers", total)
    conn.close()

    return render_template(
        "cognition_result.html",
        student_id=student_id, student_name=student_name,
        d1=d1, d2=d2, d3=d3, d4=d4,
        total_score=total, risk_level=risk_level,
        valid_flag=valid_flag, uid=uid
    )


# ============================================================
# ============================================================
#  科学锻炼知识库管理
# ============================================================

KB_CATEGORIES = [
    "力量训练", "有氧运动", "柔韧性", "运动康复",
    "营养建议", "心理健康", "睡眠改善", "综合健康",
]


@app.route("/kb")
def kb_list():
    """知识库列表"""
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()
    query = "SELECT * FROM knowledge_base WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR tags LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC"
    items = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("kb_list.html", items=items, categories=KB_CATEGORIES,
                           filters={"search": search, "category": category})


@app.route("/kb/view/<int:item_id>")
def kb_view(item_id):
    """查看知识详情"""
    conn = get_db()
    item = conn.execute("SELECT * FROM knowledge_base WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not item:
        return "知识条目不存在", 404
    return render_template("kb_detail.html", item=item)


@app.route("/kb/add", methods=["GET", "POST"])
def kb_add():
    """新增知识条目"""
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            """INSERT INTO knowledge_base
               (title, content, tags, category, video_url, image_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("title", "").strip(),
                request.form.get("content", "").strip(),
                request.form.get("tags", "").strip(),
                request.form.get("category", "").strip(),
                request.form.get("video_url", "").strip() or None,
                request.form.get("image_url", "").strip() or None,
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("kb_list"))
    return render_template("kb_add_edit.html", item=None, categories=KB_CATEGORIES)


@app.route("/kb/edit/<int:item_id>", methods=["GET", "POST"])
def kb_edit(item_id):
    """编辑知识条目"""
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            """UPDATE knowledge_base SET
               title=?, content=?, tags=?, category=?, video_url=?, image_url=?,
               updated_at=?
               WHERE id=?""",
            (
                request.form.get("title", "").strip(),
                request.form.get("content", "").strip(),
                request.form.get("tags", "").strip(),
                request.form.get("category", "").strip(),
                request.form.get("video_url", "").strip() or None,
                request.form.get("image_url", "").strip() or None,
                datetime.now(timezone.utc).isoformat(),
                item_id,
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("kb_list"))
    item = conn.execute("SELECT * FROM knowledge_base WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not item:
        return "知识条目不存在", 404
    return render_template("kb_add_edit.html", item=item, categories=KB_CATEGORIES)


@app.route("/kb/delete/<int:item_id>", methods=["POST"])
def kb_delete(item_id):
    """删除知识条目"""
    conn = get_db()
    conn.execute("DELETE FROM knowledge_base WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("kb_list"))


# ============================================================
#  预警规则引擎
# ============================================================

SOURCE_TABLE_OPTIONS = [
    ("answers", "PHQ-9 抑郁"),
    ("gad7_answers", "GAD-7 焦虑"),
    ("psqi_answers", "PSQI 睡眠"),
    ("kidmed_answers", "KIDMED 饮食"),
    ("family_support_answers", "家庭支持"),
    ("cognition_answers", "运动认知"),
]


@app.route("/rules")
def rules_list():
    """规则列表页面"""
    conn = get_db()
    rules = conn.execute("SELECT * FROM alert_rules ORDER BY id").fetchall()
    conn.close()
    return render_template("rules.html", rules=rules)


@app.route("/rules/add", methods=["GET", "POST"])
def rules_add():
    """新增规则"""
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            """INSERT INTO alert_rules
               (rule_name, description, source_table, source_field, operator, threshold, alert_level, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("rule_name", "").strip(),
                request.form.get("description", "").strip(),
                request.form.get("source_table", "").strip(),
                request.form.get("source_field", "total_score").strip(),
                request.form.get("operator", ">=").strip(),
                float(request.form.get("threshold", 0)),
                request.form.get("alert_level", "中危").strip(),
                1 if request.form.get("is_active") == "1" else 0,
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("rules_list"))
    return render_template("rules_add_edit.html", rule=None, tables=SOURCE_TABLE_OPTIONS)


@app.route("/rules/edit/<int:rule_id>", methods=["GET", "POST"])
def rules_edit(rule_id):
    """编辑规则"""
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            """UPDATE alert_rules SET
               rule_name=?, description=?, source_table=?, source_field=?,
               operator=?, threshold=?, alert_level=?, is_active=?
               WHERE id=?""",
            (
                request.form.get("rule_name", "").strip(),
                request.form.get("description", "").strip(),
                request.form.get("source_table", "").strip(),
                request.form.get("source_field", "total_score").strip(),
                request.form.get("operator", ">=").strip(),
                float(request.form.get("threshold", 0)),
                request.form.get("alert_level", "中危").strip(),
                1 if request.form.get("is_active") == "1" else 0,
                rule_id,
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("rules_list"))
    rule = conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)).fetchone()
    conn.close()
    if not rule:
        return "规则不存在", 404
    return render_template("rules_add_edit.html", rule=rule, tables=SOURCE_TABLE_OPTIONS)


@app.route("/rules/delete/<int:rule_id>", methods=["POST"])
def rules_delete(rule_id):
    """删除规则"""
    conn = get_db()
    conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("rules_list"))


@app.route("/rules/toggle/<int:rule_id>", methods=["POST"])
def rules_toggle(rule_id):
    """切换规则启用/禁用"""
    conn = get_db()
    rule = conn.execute("SELECT is_active FROM alert_rules WHERE id = ?", (rule_id,)).fetchone()
    if rule:
        new_state = 0 if rule["is_active"] == 1 else 1
        conn.execute("UPDATE alert_rules SET is_active = ? WHERE id = ?", (new_state, rule_id))
        conn.commit()
    conn.close()
    return redirect(url_for("rules_list"))


@app.route("/run_alert_check")
def run_alert_check():
    """全量扫描：对所有学生所有量表检查预警"""
    conn = get_db()
    cursor = conn.cursor()
    total_triggers = 0

    # PHQ-9
    for row in cursor.execute("SELECT * FROM answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "answers", row["total_score"])
    # GAD-7
    for row in cursor.execute("SELECT * FROM gad7_answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "gad7_answers", row["total_score"])
    # PSQI
    for row in cursor.execute("SELECT * FROM psqi_answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "psqi_answers", row["total_score"])
    # KIDMED
    for row in cursor.execute("SELECT * FROM kidmed_answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "kidmed_answers", row["total_score"])
    # Family
    for row in cursor.execute("SELECT * FROM family_support_answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "family_support_answers", row["family_total"])
    # Cognition
    for row in cursor.execute("SELECT * FROM cognition_answers").fetchall():
        total_triggers += check_and_create_alerts(row["student_id"], "cognition_answers", row["total_score"])

    conn.close()
    return f"全量预警扫描完成，共触发 {total_triggers} 条新预警。"


# ============================================================
#  教师端预警总览
# ============================================================

@app.route("/alerts")
def alerts_dashboard():
    """教师端预警总览"""
    conn = get_db()
    cursor = conn.cursor()

    # 筛选参数
    alert_level = request.args.get("level", "").strip()
    rule_type = request.args.get("rule_type", "").strip()
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search = request.args.get("search", "").strip()

    # 构建查询
    query = """SELECT a.*, r.rule_name, s.student_name
               FROM alerts a
               JOIN alert_rules r ON a.rule_id = r.id
               LEFT JOIN students s ON a.student_id = s.student_id
               WHERE 1=1"""
    params = []

    if alert_level:
        query += " AND a.alert_level = ?"
        params.append(alert_level)
    if rule_type:
        query += " AND r.rule_name = ?"
        params.append(rule_type)
    if status:
        query += " AND a.status = ?"
        params.append(status)
    if date_from:
        query += " AND a.triggered_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND a.triggered_at <= ?"
        params.append(date_to + " 23:59:59")
    if search:
        query += " AND (a.student_id LIKE ? OR s.student_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY CASE a.alert_level WHEN '高危' THEN 1 WHEN '中危' THEN 2 ELSE 3 END, a.triggered_at DESC"
    alerts = cursor.execute(query, params).fetchall()

    # 统计数据（全量，不受筛选影响）
    total_alerts = cursor.execute("SELECT COUNT(*) as c FROM alerts").fetchone()["c"]
    high_cnt = cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE alert_level='高危'").fetchone()["c"]
    mid_cnt = cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE alert_level='中危'").fetchone()["c"]
    low_cnt = cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE alert_level='低危'").fetchone()["c"]
    pending_cnt = cursor.execute("SELECT COUNT(*) as c FROM alerts WHERE status='待处理'").fetchone()["c"]

    # 规则类型列表（用于筛选下拉）
    rule_types = cursor.execute("SELECT DISTINCT rule_name FROM alert_rules ORDER BY rule_name").fetchall()

    conn.close()

    return render_template(
        "alerts.html",
        alerts=alerts,
        total_alerts=total_alerts,
        high_cnt=high_cnt,
        mid_cnt=mid_cnt,
        low_cnt=low_cnt,
        pending_cnt=pending_cnt,
        rule_types=rule_types,
        filters={"level": alert_level, "rule_type": rule_type, "status": status,
                 "date_from": date_from, "date_to": date_to, "search": search},
    )


@app.route("/alerts/export")
def alerts_export():
    """导出预警数据为 CSV"""
    level = request.args.get("level", "").strip()
    rule_type = request.args.get("rule_type", "").strip()
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """SELECT a.*, r.rule_name, s.student_name
               FROM alerts a
               JOIN alert_rules r ON a.rule_id = r.id
               LEFT JOIN students s ON a.student_id = s.student_id
               WHERE 1=1"""
    params = []

    if level:
        query += " AND a.alert_level = ?"; params.append(level)
    if rule_type:
        query += " AND r.rule_name = ?"; params.append(rule_type)
    if status:
        query += " AND a.status = ?"; params.append(status)
    if date_from:
        query += " AND a.triggered_at >= ?"; params.append(date_from)
    if date_to:
        query += " AND a.triggered_at <= ?"; params.append(date_to + " 23:59:59")
    if search:
        query += " AND (a.student_id LIKE ? OR s.student_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY a.triggered_at DESC"
    rows = cursor.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["学号", "姓名", "规则名称", "预警等级", "触发日期", "得分", "状态", "备注"])
    for r in rows:
        writer.writerow([r["student_id"], r["student_name"], r["rule_name"],
                         r["alert_level"], r["triggered_at"], r["source_score"],
                         r["status"], r["note"] or ""])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    resp.headers["Content-Disposition"] = "attachment; filename=alerts_export.csv"
    return resp


@app.route("/alerts/student/<student_id>")
def alerts_student_view(student_id):
    """查看某学生的所有预警记录"""
    conn = get_db()
    cursor = conn.cursor()
    records = cursor.execute(
        """SELECT a.*, r.rule_name, s.student_name
           FROM alerts a
           JOIN alert_rules r ON a.rule_id = r.id
           LEFT JOIN students s ON a.student_id = s.student_id
           WHERE a.student_id = ?
           ORDER BY a.triggered_at DESC""",
        (student_id,)
    ).fetchall()
    student = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    conn.close()
    if not student:
        return "学生不存在", 404
    return render_template("alerts.html", alerts=records, student_view=student,
                           total_alerts=0, high_cnt=0, mid_cnt=0, low_cnt=0, pending_cnt=0,
                           rule_types=[], filters={})


# ============================================================
#  学生健康档案（一生一档 Phase 1）
# ============================================================

@app.route("/my_health_login", methods=["GET", "POST"])
def my_health_login():
    """学生健康档案登录页"""
    error = None
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        birth_date = request.form.get("birth_date", "").strip()

        if not student_id or not birth_date:
            error = "请填写学号和出生日期"
        else:
            conn = get_db()
            student = conn.execute(
                "SELECT * FROM students WHERE student_id = ?", (student_id,)
            ).fetchone()

            if not student:
                conn.close()
                error = "学号或出生日期错误"
            elif student["birth_date"] is None or student["birth_date"] == "":
                # 学号存在但无出生日期 → 先存 session 跳转设置页
                conn.close()
                session["pending_student_id"] = student_id
                return redirect(url_for("my_health_setup"))
            elif student["birth_date"] == birth_date:
                # 更新最后登录时间
                conn.execute(
                    "UPDATE students SET last_login = ? WHERE student_id = ?",
                    (datetime.now(timezone.utc).isoformat(), student_id),
                )
                conn.commit()
                conn.close()
                session["student_id"] = student_id
                session.pop("pending_student_id", None)
                return redirect(url_for("my_health"))
            else:
                conn.close()
                error = "学号或出生日期错误"

    return render_template("login.html", error=error)


@app.route("/my_health_setup", methods=["GET", "POST"])
def my_health_setup():
    """首次设置出生日期"""
    pending_id = session.get("pending_student_id")
    logged_id = session.get("student_id")
    student_id = pending_id or logged_id

    if not student_id:
        return redirect(url_for("my_health_login"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        return redirect(url_for("my_health_login"))

    if request.method == "POST":
        birth_date = request.form.get("birth_date", "").strip()
        if not birth_date:
            conn.close()
            return render_template("my_health_setup.html", student=student, error="请选择出生日期")

        conn.execute(
            "UPDATE students SET birth_date = ? WHERE student_id = ?",
            (birth_date, student_id),
        )
        conn.commit()
        conn.close()
        session["student_id"] = student_id
        session.pop("pending_student_id", None)
        return redirect(url_for("my_health"))

    conn.close()
    return render_template("my_health_setup.html", student=student, error=None)


@app.route("/my_health")
def my_health():
    """个人健康档案首页"""
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for("my_health_login"))

    conn = get_db()
    cursor = conn.cursor()

    # 学生信息
    student = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    if not student:
        conn.close()
        session.clear()
        return redirect(url_for("my_health_login"))

    # ---- 聚合各量表数据 ----
    def fetch_scale(table, order_by="id ASC"):
        return cursor.execute(
            f"SELECT * FROM {table} WHERE student_id = ? ORDER BY {order_by}", (student_id,)
        ).fetchall()

    phq9_data = fetch_scale("answers")
    gad7_data = fetch_scale("gad7_answers")
    psqi_data = fetch_scale("psqi_answers")
    kidmed_data = fetch_scale("kidmed_answers")
    family_data = fetch_scale("family_support_answers")
    cognition_data = fetch_scale("cognition_answers")
    physical_data = cursor.execute(
        "SELECT * FROM physical_measurements WHERE student_id = ? ORDER BY measure_date ASC, id ASC",
        (student_id,)
    ).fetchall()

    # ---- 辅助函数 ----
    def latest(rows, key="total_score"):
        return rows[-1] if rows else None

    def trend(rows, key="total_score"):
        """返回 [(label, score), ...] 用于 Chart.js"""
        result = []
        for r in rows:
            label = (r["time_end"] if "time_end" in r.keys() else
                     r["created_at"] if "created_at" in r.keys() else
                     r["measure_date"] if "measure_date" in r.keys() else "")
            if isinstance(label, str) and "T" in label:
                label = label[:10]
            val = r[key] if key in r.keys() else 0
            result.append((str(label or ""), val))
        return result

    # ---- 构建模板数据 ----
    scales = {}

    for slug, data, score_key, label, color, date_key in [
        ("phq9", phq9_data, "total_score", "PHQ-9 抑郁", "#4a6cf7", "time_end"),
        ("gad7", gad7_data, "total_score", "GAD-7 焦虑", "#f7931e", "time_end"),
        ("psqi", psqi_data, "total_score", "PSQI 睡眠", "#1b9e77", "time_end"),
        ("kidmed", kidmed_data, "total_score", "KIDMED 饮食", "#E74C3C", "time_end"),
        ("family", family_data, "family_total", "家庭支持", "#3B8BEA", "time_end"),
        ("cognition", cognition_data, "total_score", "运动认知", "#8E44AD", "time_end"),
    ]:
        latest_row = latest(data, key=score_key)
        scales[slug] = {
            "label": label,
            "color": color,
            "count": len(data),
            "latest": latest_row,
            "score": latest_row[score_key] if latest_row else None,
            "risk": latest_row["risk_level"] if latest_row else None,
            "date": (latest_row["time_end"] if latest_row else None) or "",
            "trend": trend(data, key=score_key),
            "rows": data,
            "score_key": score_key,
            "date_key": date_key,
        }

    # 体格数据
    latest_phys = physical_data[-1] if physical_data else None
    phys = {
        "count": len(physical_data),
        "latest": latest_phys,
        "bmi": latest_phys["bmi"] if latest_phys else None,
        "body_fat_rate": latest_phys["body_fat_rate"] if latest_phys else None,
        "weight": latest_phys["weight"] if latest_phys else None,
        "waist_circ": latest_phys["waist_circ"] if latest_phys else None,
        "muscle_mass": latest_phys["muscle_mass"] if latest_phys else None,
        "body_score": latest_phys["body_score"] if latest_phys else None,
    }

    # ---- 预警数据 ----
    alert_rows = cursor.execute(
        """SELECT a.*, r.rule_name, r.description
           FROM alerts a
           JOIN alert_rules r ON a.rule_id = r.id
           WHERE a.student_id = ?
           ORDER BY
             CASE a.alert_level WHEN '高危' THEN 1 WHEN '中危' THEN 2 ELSE 3 END,
             a.triggered_at DESC""",
        (student_id,)
    ).fetchall()

    alert_summary = {
        "total": len(alert_rows),
        "highest": "高危" if any(a["alert_level"] == "高危" for a in alert_rows)
                   else "中危" if any(a["alert_level"] == "中危" for a in alert_rows)
                   else "低危" if alert_rows else None,
        "details": alert_rows,
    }

    conn.close()

    return render_template(
        "my_health.html",
        student=student,
        scales=scales,
        phys=phys,
        physical_count=len(physical_data),
        alerts=alert_summary,
    )


@app.route("/my_health_logout")
def my_health_logout():
    """退出健康档案"""
    session.clear()
    return redirect(url_for("my_health_login"))


# ============================================================
#  体格测试模块（教师端录入）
# ============================================================

@app.route("/physical_input")
def physical_input():
    """教师端体测数据录入页面"""
    return render_template("physical_input.html")


@app.route("/physical_search", methods=["POST"])
def physical_search():
    """按学号检索学生信息（用于录入页面自动填充）"""
    student_id = request.form.get("student_id", "").strip()
    if not student_id:
        return '<div class="alert alert-warning">请输入学号</div>'

    conn = get_db()
    cursor = conn.cursor()
    student = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    conn.close()

    if not student:
        return '<div class="alert alert-danger">未找到该学号的学生信息，请先在问卷系统中提交任意问卷以注册学号</div>'

    return f'''<div class="alert alert-success">
        <strong>✅ 已找到</strong><br>
        学号：{student["student_id"]}<br>
        姓名：{student["student_name"]}<br>
        UID：{student["uid"]}
        <input type="hidden" id="found_student_name" value="{student["student_name"]}">
        <input type="hidden" id="found_uid" value="{student["uid"]}">
    </div>'''


@app.route("/physical_submit", methods=["POST"])
def physical_submit():
    """保存体测数据"""
    student_id = request.form.get("student_id", "").strip()
    student_name = request.form.get("student_name", "").strip()

    if not student_id or not student_name:
        return "学号和姓名为必填项", 400

    # 辅助函数：安全读取 float/int
    def get_float(key, default=None):
        val = request.form.get(key, "").strip()
        if val == "":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def get_int(key, default=None):
        val = request.form.get(key, "").strip()
        if val == "":
            return default
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    # 握力数据
    gl1 = get_float("grip_left_1")
    gl2 = get_float("grip_left_2")
    gl3 = get_float("grip_left_3")
    gr1 = get_float("grip_right_1")
    gr2 = get_float("grip_right_2")
    gr3 = get_float("grip_right_3")

    # 自动计算握力最佳值
    left_vals = [v for v in [gl1, gl2, gl3] if v is not None]
    right_vals = [v for v in [gr1, gr2, gr3] if v is not None]
    grip_left_best = max(left_vals) if left_vals else None
    grip_right_best = max(right_vals) if right_vals else None
    grip_avg_best = ((grip_left_best or 0) + (grip_right_best or 0)) / 2 if (grip_left_best is not None and grip_right_best is not None) else None

    grip_dominant = get_int("grip_dominant")

    # 腰围
    waist_circ = get_float("waist_circ")

    # 体脂称数据
    weight = get_float("weight")
    bmi = get_float("bmi")
    body_fat_rate = get_float("body_fat_rate")
    body_fat_mass = get_float("body_fat_mass")
    muscle_mass = get_float("muscle_mass")
    skeletal_muscle = get_float("skeletal_muscle")
    bone_mass = get_float("bone_mass")
    body_water_rate = get_float("body_water_rate")
    body_water_mass = get_float("body_water_mass")
    protein_rate = get_float("protein_rate")
    protein_mass = get_float("protein_mass")
    bmr = get_float("bmr")
    visceral_fat = get_int("visceral_fat")
    subcut_fat_rate = get_float("subcut_fat_rate")
    body_age = get_int("body_age")
    body_type = get_int("body_type")
    heart_rate = get_int("heart_rate")
    body_score = get_int("body_score")

    measure_date = request.form.get("measure_date", "").strip()
    measure_operator = request.form.get("measure_operator", "").strip()
    data_quality_note = request.form.get("data_quality_note", "").strip() or None

    # 自动判断数据完整度
    required_fields = [
        gl1, gl2, gl3, gr1, gr2, gr3, grip_dominant,
        waist_circ, weight, bmi, body_fat_rate, body_fat_mass,
        muscle_mass, skeletal_muscle, bone_mass,
        body_water_rate, body_water_mass, protein_rate, protein_mass,
        bmr, visceral_fat, subcut_fat_rate, body_age, body_type,
        heart_rate, body_score
    ]
    data_complete = 1 if all(v is not None for v in required_fields) else 0

    # 查询 UID
    conn = get_db()
    cursor = conn.cursor()
    uid_row = cursor.execute(
        "SELECT uid FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    uid = uid_row["uid"] if uid_row else None

    cursor.execute("""
        INSERT INTO physical_measurements (
            student_id, student_name, uid, measure_date,
            grip_left_1, grip_left_2, grip_left_3,
            grip_right_1, grip_right_2, grip_right_3,
            grip_left_best, grip_right_best, grip_avg_best,
            grip_dominant, waist_circ,
            weight, bmi, body_fat_rate, body_fat_mass,
            muscle_mass, skeletal_muscle, bone_mass,
            body_water_rate, body_water_mass,
            protein_rate, protein_mass, bmr,
            visceral_fat, subcut_fat_rate,
            body_age, body_type, heart_rate, body_score,
            measure_operator, data_complete, data_quality_note
        ) VALUES (
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?
        )
    """, (
        student_id, student_name, uid, measure_date if measure_date else None,
        gl1, gl2, gl3,
        gr1, gr2, gr3,
        grip_left_best, grip_right_best, grip_avg_best,
        grip_dominant, waist_circ,
        weight, bmi, body_fat_rate, body_fat_mass,
        muscle_mass, skeletal_muscle, bone_mass,
        body_water_rate, body_water_mass,
        protein_rate, protein_mass, bmr,
        visceral_fat, subcut_fat_rate,
        body_age, body_type, heart_rate, body_score,
        measure_operator if measure_operator else None,
        data_complete, data_quality_note
    ))
    conn.commit()
    conn.close()

    return render_template(
        "physical_view.html",
        message=f"✅ 体测数据已保存！学号：{student_id}，姓名：{student_name}",
        records=None,
        detail=None
    )


@app.route("/physical_view")
def physical_view():
    """查看已录入的体测数据列表"""
    conn = get_db()
    cursor = conn.cursor()
    records = cursor.execute(
        """SELECT id, student_id, student_name, measure_date,
                  measure_operator, data_complete, measure_time
           FROM physical_measurements
           ORDER BY measure_time DESC"""
    ).fetchall()
    conn.close()
    return render_template("physical_view.html", records=records, detail=None, message=None)


@app.route("/physical_view/<int:record_id>")
def physical_view_detail(record_id):
    """查看某条体测记录的详细信息"""
    conn = get_db()
    cursor = conn.cursor()
    detail = cursor.execute(
        "SELECT * FROM physical_measurements WHERE id = ?", (record_id,)
    ).fetchone()
    records = cursor.execute(
        """SELECT id, student_id, student_name, measure_date,
                  measure_operator, data_complete, measure_time
           FROM physical_measurements
           ORDER BY measure_time DESC"""
    ).fetchall()
    conn.close()

    if not detail:
        return "记录不存在", 404

    return render_template("physical_view.html", records=records, detail=detail, message=None)


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

    # ---- KIDMED 数据 ----
    writer.writerow([])
    cursor.execute("""
        SELECT k.*, s.uid
        FROM kidmed_answers k
        LEFT JOIN students s ON k.student_id = s.student_id
        ORDER BY k.id
    """)
    kidmed_rows = cursor.fetchall()

    writer.writerow([
        "kidmed_id", "student_id", "student_name", "uid",
        "q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8",
        "q9", "q10", "q11", "q12", "q13", "q14", "q15", "q16",
        "total_score", "risk_level", "time_start", "time_end", "valid_flag"
    ])
    for row in kidmed_rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"], row["uid"],
            row["q1"], row["q2"], row["q3"], row["q4"], row["q5"],
            row["q6"], row["q7"], row["q8"], row["q9"], row["q10"],
            row["q11"], row["q12"], row["q13"], row["q14"], row["q15"],
            row["q16"],
            row["total_score"], row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    # ---- 家庭体力活动支持 数据 ----
    writer.writerow([])
    cursor.execute("""
        SELECT f.*, s.uid
        FROM family_support_answers f
        LEFT JOIN students s ON f.student_id = s.student_id
        ORDER BY f.id
    """)
    family_rows = cursor.fetchall()
    writer.writerow([
        "family_id", "student_id", "student_name", "uid",
        "mother_self_ex", "father_self_ex",
        "mother_joint_ex", "father_joint_ex",
        "mother_invites", "father_invites",
        "mother_transport", "father_transport",
        "mother_registers", "father_registers",
        "mother_watches", "father_watches",
        "mother_tv_limit", "father_tv_limit",
        "mother_computer_limit", "father_computer_limit",
        "mother_game_limit", "father_game_limit",
        "mother_total", "father_total", "family_total",
        "risk_level", "time_start", "time_end", "valid_flag"
    ])
    for row in family_rows:
        writer.writerow([
            row["id"], row["student_id"], row["student_name"], row["uid"],
            row["mother_self_ex"], row["father_self_ex"],
            row["mother_joint_ex"], row["father_joint_ex"],
            row["mother_invites"], row["father_invites"],
            row["mother_transport"], row["father_transport"],
            row["mother_registers"], row["father_registers"],
            row["mother_watches"], row["father_watches"],
            row["mother_tv_limit"], row["father_tv_limit"],
            row["mother_computer_limit"], row["father_computer_limit"],
            row["mother_game_limit"], row["father_game_limit"],
            row["mother_total"], row["father_total"], row["family_total"],
            row["risk_level"],
            row["time_start"], row["time_end"], row["valid_flag"]
        ])

    # ---- 运动认知 数据 ----
    writer.writerow([])
    cursor.execute("""
        SELECT c.*, s.uid
        FROM cognition_answers c
        LEFT JOIN students s ON c.student_id = s.student_id
        ORDER BY c.id
    """)
    cog_rows = cursor.fetchall()
    cog_header = ["cog_id", "student_id", "student_name", "uid"]
    for i in range(1, 44):
        cog_header.append(f"c{i}")
    cog_header += ["d1_benefit", "d2_barrier", "d3_family", "d4_self_efficacy",
                   "total_score", "risk_level", "time_start", "time_end", "valid_flag"]
    writer.writerow(cog_header)
    for row in cog_rows:
        r = [row["id"], row["student_id"], row["student_name"], row["uid"]]
        for i in range(1, 44):
            r.append(row[f"c{i}"])
        r += [row["dimension1_benefit"], row["dimension2_barrier"],
              row["dimension3_family"], row["dimension4_self_efficacy"],
              row["total_score"], row["risk_level"],
              row["time_start"], row["time_end"], row["valid_flag"]]
        writer.writerow(r)

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

    # KIDMED 统计
    cursor.execute("SELECT COUNT(*) as cnt FROM kidmed_answers")
    kidmed_total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM kidmed_answers WHERE valid_flag = 1")
    kidmed_valid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM kidmed_answers WHERE valid_flag = 0")
    kidmed_invalid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(total_score) as avg_score FROM kidmed_answers WHERE valid_flag = 1")
    kidmed_avg_row = cursor.fetchone()
    kidmed_avg = round(kidmed_avg_row["avg_score"], 1) if kidmed_avg_row["avg_score"] else 0

    # 家庭支持 统计
    cursor.execute("SELECT COUNT(*) as cnt FROM family_support_answers")
    family_total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM family_support_answers WHERE valid_flag = 1")
    family_valid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM family_support_answers WHERE valid_flag = 0")
    family_invalid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(family_total) as avg_score FROM family_support_answers WHERE valid_flag = 1")
    family_avg_row = cursor.fetchone()
    family_avg = round(family_avg_row["avg_score"], 1) if family_avg_row["avg_score"] else 0

    # 运动认知 统计
    cursor.execute("SELECT COUNT(*) as cnt FROM cognition_answers")
    cog_total = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM cognition_answers WHERE valid_flag = 1")
    cog_valid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM cognition_answers WHERE valid_flag = 0")
    cog_invalid = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(total_score) as avg_score FROM cognition_answers WHERE valid_flag = 1")
    cog_avg_row = cursor.fetchone()
    cog_avg = round(cog_avg_row["avg_score"], 1) if cog_avg_row["avg_score"] else 0

    conn.close()

    return render_template(
        "stats.html",
        total_count=total_count, valid_count=valid_count,
        invalid_count=invalid_count, avg_score=avg_score,
        gad7_total=gad7_total, gad7_valid=gad7_valid,
        gad7_invalid=gad7_invalid, gad7_avg=gad7_avg,
        psqi_total=psqi_total, psqi_valid=psqi_valid,
        psqi_invalid=psqi_invalid, psqi_avg=psqi_avg,
        kidmed_total=kidmed_total, kidmed_valid=kidmed_valid,
        kidmed_invalid=kidmed_invalid, kidmed_avg=kidmed_avg,
        family_total=family_total, family_valid=family_valid,
        family_invalid=family_invalid, family_avg=family_avg,
        cog_total=cog_total, cog_valid=cog_valid,
        cog_invalid=cog_invalid, cog_avg=cog_avg
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
