"""SQLite 스키마 및 연결 관리.

SQLAlchemy 대신 표준 라이브러리 sqlite3를 사용한다.
- 테이블 3개, 단일 파일 DB, 사내 소규모 사용 -> ORM 오버헤드/의존성이 이득보다 큼
- 추후 PostgreSQL 등으로 옮길 경우 쿼리가 이 모듈과 repository 함수에 모여 있어 교체 범위가 작다
"""
import os
import sqlite3

DB_PATH = os.environ.get("WELDER_DB", os.path.join(os.path.dirname(__file__), "data", "welder.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS welders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    welder_no   TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    birth_date  TEXT,
    company     TEXT,
    role        TEXT,
    status      TEXT NOT NULL DEFAULT '재직'
);

CREATE TABLE IF NOT EXISTS test_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    welder_id       INTEGER NOT NULL REFERENCES welders(id) ON DELETE CASCADE,
    project_name    TEXT,
    welding_date    TEXT NOT NULL,
    process         TEXT,
    joint_type      TEXT NOT NULL CHECK (joint_type IN ('BW','FW')),
    thickness       REAL,
    position        TEXT,
    filler_material TEXT,
    backing         TEXT
);

CREATE TABLE IF NOT EXISTS test_results_and_certs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id           INTEGER NOT NULL UNIQUE REFERENCES test_records(id) ON DELETE CASCADE,
    vt_result         TEXT,
    rt_ut_result      TEXT,
    macro_bend_result TEXT,
    final_status      TEXT NOT NULL DEFAULT '진행중',
    issue_date        TEXT,
    expire_date       TEXT,
    renewal_count     INTEGER NOT NULL DEFAULT 0 CHECK (renewal_count BETWEEN 0 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_tests_welder ON test_records(welder_id);
"""


def get_conn(path: str | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
