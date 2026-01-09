import os
import re
import csv
import time
import json
import uuid
import random
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple

from flask import Flask, render_template, request, jsonify, send_from_directory, session

# =========================
# Config
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STIM_ROOT = os.path.join(BASE_DIR, "stimuli")
DATA_DIR = os.path.join(BASE_DIR, "data")

DIR_PRACT_RVB = os.path.join(STIM_ROOT, "EMO_PRACT_rvb")  # 2I2AFC (dry + _rvb)
DIR_137 = os.path.join(STIM_ROOT, "EMO_137")              # 5AFC practice (dry)
DIR_STIM_RVB = os.path.join(STIM_ROOT, "EMO_STIM_rvb")    # 5AFC test (dry + rvb1/rvb2)

EMOTIONS_5AFC = ["Amusement", "Anger", "Sadness", "Fear", "Surprise"]

# amu_F137.wav / fear_M137.wav / rel_F545_rvb.wav / amu_F820_rvb1.wav ...
RE_FN = re.compile(
    r"^(?P<emo>[A-Za-z]+)_(?P<sex>[MF])(?P<utt>\d+)(?:_rvb(?P<rvb>(?:\d+)|(?:)))?\.wav$"
)

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def list_wavs(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    return sorted([f for f in os.listdir(folder) if f.lower().endswith(".wav")])

def parse_fn(fn: str) -> dict:
    m = RE_FN.match(fn)
    if not m:
        return {"raw": fn}

    emo = m.group("emo").lower()
    sex = m.group("sex")
    utt = m.group("utt")
    rvb_raw = m.group("rvb")  # None / "" / "1" / "2" ...

    if rvb_raw is None:
        rvb_level = "dry"
    else:
        rvb_level = "rvb" + (rvb_raw if rvb_raw != "" else "")
        if rvb_level == "rvb":
            rvb_level = "rvb"

    base_id = f"{emo}_{sex}{utt}"
    return {
        "emo": emo,              # sad/fear/amu/rel/ang/surp...
        "sex": sex,              # F/M
        "utt": utt,              # 137/545/820...
        "rvb_level": rvb_level,  # dry / rvb / rvb1 / rvb2
        "base_id": base_id,
    }

def make_log_path(participant_id: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", participant_id.strip())[:50] or "anon"
    return os.path.join(DATA_DIR, f"{safe}_{ts}.csv")

# =========================
# Trial data
# =========================
@dataclass
class Trial:
    block: str
    trial_index: int
    question: str
    stim_A: Optional[str] = None
    stim_B: Optional[str] = None
    stim: Optional[str] = None
    meta: Optional[dict] = None

# =========================
# 4-stage mapping
# =========================
def stage_id_from_block(block: str) -> int:
    if block == "2I2AFC_discrimination":
        return 1
    if block == "2I2AFC_dry_rvb":
        return 2
    if block == "5AFC_practice":
        return 3
    return 4  # 5AFC_test

def stage_label(stage_id: int) -> str:
    return {1: "1단계", 2: "2단계", 3: "3단계", 4: "4단계"}[stage_id]

STAGE_COUNT = 4

# =========================
# Trial builders
# =========================
def build_2i2afc_discrimination_4() -> List[Trial]:
    """
    1단계: sad vs fear 2개(F/M) + amu vs rel 2개(F/M) = 4
    질문은 run.html에서 target에 따라:
      - sad vs fear -> more sad?
      - amu vs rel  -> more amused?
    """
    files = list_wavs(DIR_PRACT_RVB)
    meta_map = {fn: parse_fn(fn) for fn in files}

    def find_one(emo: str, sex: str, utt: str, rvb_level: str) -> Optional[str]:
        for fn, m in meta_map.items():
            if m.get("emo") == emo and m.get("sex") == sex and m.get("utt") == utt and m.get("rvb_level") == rvb_level:
                return fn
        return None

    trials: List[Trial] = []
    specs = [
        # sad vs fear (137)
        ("sad", "F", "137", "fear", "F", "137", "sad"),
        ("sad", "M", "137", "fear", "M", "137", "sad"),
        # amu vs rel (545)
        ("amu", "F", "545", "rel", "F", "545", "amu"),
        ("amu", "M", "545", "rel", "M", "545", "amu"),
    ]

    for e1, s1, u1, e2, s2, u2, target in specs:
        a = find_one(e1, s1, u1, "dry")
        b = find_one(e2, s2, u2, "dry")
        if not (a and b):
            raise FileNotFoundError(f"Missing discrimination file(s): {e1}_{s1}{u1} or {e2}_{s2}{u2} (dry)")
        trials.append(Trial(
            block="2I2AFC_discrimination",
            trial_index=0,
            question="(auto)",  # 화면 표시용 질문은 run.html에서 생성
            stim_A=a,
            stim_B=b,
            meta={"target": target}  # "sad" or "amu"
        ))

    random.shuffle(trials)
    for i, t in enumerate(trials, start=1):
        t.trial_index = i
    return trials

def build_2i2afc_dry_rvb_8() -> List[Trial]:
    """
    2단계: sad/fear/amu/rel x (F/M) = 8
    - A/B에 dry/rvb가 매 trial 랜덤으로 섞이게 구성
    - 질문은 run.html에서 emo에 따라:
        sad  -> more sad?
        fear -> more fearful?
        amu  -> more amused?
        rel  -> more relieved?
    """
    files = list_wavs(DIR_PRACT_RVB)
    meta_map = {fn: parse_fn(fn) for fn in files}

    def find_one(emo: str, sex: str, utt: str, rvb_level: str) -> Optional[str]:
        for fn, m in meta_map.items():
            if m.get("emo") == emo and m.get("sex") == sex and m.get("utt") == utt and m.get("rvb_level") == rvb_level:
                return fn
        return None

    targets = [
        ("sad", "F", "137"), ("sad", "M", "137"),
        ("fear", "F", "137"), ("fear", "M", "137"),
        ("amu", "F", "545"), ("amu", "M", "545"),
        ("rel", "F", "545"), ("rel", "M", "545"),
    ]

    trials: List[Trial] = []
    for emo, sex, utt in targets:
        dry = find_one(emo, sex, utt, "dry")
        rvb = find_one(emo, sex, utt, "rvb")
        if not (dry and rvb):
            raise FileNotFoundError(f"Missing dry/rvb file(s): {emo}_{sex}{utt} dry/rvb")

        # ✅ A/B 랜덤 섞기
        if random.random() < 0.5:
            stim_A, stim_B = dry, rvb
            A_is = "dry"
            B_is = "rvb"
        else:
            stim_A, stim_B = rvb, dry
            A_is = "rvb"
            B_is = "dry"

        trials.append(Trial(
            block="2I2AFC_dry_rvb",
            trial_index=0,
            question="(auto)",
            stim_A=stim_A,
            stim_B=stim_B,
            meta={"emo": emo, "A_is": A_is, "B_is": B_is}
        ))

    random.shuffle(trials)
    for i, t in enumerate(trials, start=1):
        t.trial_index = i
    return trials

def build_5afc_practice_10() -> List[Trial]:
    wavs = list_wavs(DIR_137)
    if len(wavs) < 10:
        raise ValueError(f"EMO_137에 wav가 10개 미만입니다. 현재: {len(wavs)}")
    random.shuffle(wavs)
    wavs = wavs[:10]

    trials: List[Trial] = []
    for i, fn in enumerate(wavs, start=1):
        trials.append(Trial(
            block="5AFC_practice",
            trial_index=i,
            question="Which of the following 5 emotion classes did the talker seem to be expressing?",
            stim=fn,
            meta=parse_fn(fn)
        ))
    return trials

def build_5afc_test_60() -> List[Trial]:
    wavs = list_wavs(DIR_STIM_RVB)
    if len(wavs) < 60:
        raise ValueError(f"EMO_STIM_rvb에 wav가 60개 미만입니다. 현재: {len(wavs)}")

    # ✅ 제약 없이 완전 랜덤
    random.shuffle(wavs)
    selected = wavs[:60]

    trials: List[Trial] = []
    for i, fn in enumerate(selected, start=1):
        trials.append(Trial(
            block="5AFC_test",
            trial_index=i,
            question="Which of the following 5 emotion classes did the talker seem to be expressing?",
            stim=fn,
            meta=parse_fn(fn)
        ))
    return trials


# =========================
# Session store
# =========================
STORE: Dict[str, dict] = {}

def get_state() -> dict:
    sid = session.get("sid")
    if not sid or sid not in STORE:
        raise RuntimeError("Session not initialized. Go to / and press Start.")
    return STORE[sid]

# =========================
# Flask app
# =========================
app = Flask(__name__)
app.secret_key = "SER_PILOT_CHANGE_ME"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    ensure_dirs()
    pid = request.form.get("participant_id", "").strip() or "anon"

    random.seed(time.time())

    t1 = build_2i2afc_discrimination_4()  # 4
    t2 = build_2i2afc_dry_rvb_8()         # 8
    t3 = build_5afc_practice_10()         # 10
    t4 = build_5afc_test_60()             # 60

    trials: List[dict] = []
    trials.extend([asdict(t) for t in t1])
    trials.extend([asdict(t) for t in t2])
    trials.extend([asdict(t) for t in t3])
    trials.extend([asdict(t) for t in t4])

    sid = uuid.uuid4().hex
    session["sid"] = sid

    log_path = make_log_path(pid)

    STORE[sid] = {
        "participant_id": pid,
        "log_path": log_path,
        "trials": trials,
        "cursor": 0,
        "stage_totals": {1: len(t1), 2: len(t2), 3: len(t3), 4: len(t4)},
    }

    # 로그 헤더
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "participant_id",
            "timestamp_unix",
            "stage_id",
            "stage_label",
            "stage_trial_index",
            "stage_trial_total",
            "block",
            "trial_global_index",
            "question_shown",
            "stim_A", "stim_B", "stim",
            "meta_json",
            "response",
            "rt_ms",
            "played_json"
        ])

    return jsonify({"ok": True})

@app.route("/run")
def run():
    return render_template("run.html", emotions=EMOTIONS_5AFC)

@app.route("/api/trial", methods=["GET"])
def api_trial():
    st = get_state()
    trials = st["trials"]
    cursor = st["cursor"]

    if cursor >= len(trials):
        return jsonify({"done": True})

    t = trials[cursor]
    block = t.get("block", "")
    sid = stage_id_from_block(block)

    # stage index 계산
    prev_same_stage = 0
    for i in range(cursor):
        if stage_id_from_block(trials[i].get("block", "")) == sid:
            prev_same_stage += 1
    stage_index = prev_same_stage + 1
    stage_total = int(st["stage_totals"].get(sid, 0))

    return jsonify({
        "done": False,
        "trial": t,
        "cursor": cursor,
        "total": len(trials),
        "stage": {
            "id": sid,
            "label": stage_label(sid),
            "count": STAGE_COUNT,
            "index": stage_index,
            "total": stage_total
        }
    })

@app.route("/api/submit", methods=["POST"])
def api_submit():
    st = get_state()
    payload = request.get_json(force=True)

    resp = payload.get("response")
    rt_ms = payload.get("rt_ms")
    played = payload.get("played", {})
    question_shown = payload.get("question_shown", "")

    trials = st["trials"]
    cursor = st["cursor"]
    if cursor >= len(trials):
        return jsonify({"ok": False, "error": "No trial remaining"})

    t = trials[cursor]
    pid = st["participant_id"]
    log_path = st["log_path"]

    block = t.get("block", "")
    sid = stage_id_from_block(block)

    prev_same_stage = 0
    for i in range(cursor):
        if stage_id_from_block(trials[i].get("block", "")) == sid:
            prev_same_stage += 1
    stage_index = prev_same_stage + 1
    stage_total = int(st["stage_totals"].get(sid, 0))

    row = [
        pid,
        int(time.time()),
        sid,
        stage_label(sid),
        stage_index,
        stage_total,
        block,
        cursor + 1,
        question_shown,
        t.get("stim_A"),
        t.get("stim_B"),
        t.get("stim"),
        json.dumps(t.get("meta", {}), ensure_ascii=False),
        resp,
        rt_ms,
        json.dumps(played, ensure_ascii=False),
    ]

    with open(log_path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

    st["cursor"] = cursor + 1
    return jsonify({"ok": True})

@app.route("/done")
def done():
    return render_template("done.html")

@app.route("/stimuli/<path:subdir>/<path:filename>")
def serve_stim(subdir, filename):
    folder = os.path.join(STIM_ROOT, subdir)
    return send_from_directory(folder, filename)

if __name__ == "__main__":
    ensure_dirs()
    app.run(host="127.0.0.1", port=5000, debug=True)
