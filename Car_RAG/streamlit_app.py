
import os
import json
import traceback
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import streamlit as st

from rag.answer import ask, verify_citations
from rag.chunking import chunk_fixed, chunk_by_headings
from rag.embed import Embedder
from rag.loader import load_docs
from rag.search import Index, search, expanded_search

from eval_retrieval import needles, is_hit, reciprocal_rank
from eval_answers import check
from groq import RateLimitError


# ==================================================
# הגדרות כלליות
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

GOLDEN_FILE = BASE_DIR / "golden.json"
HISTORY_FILE = BASE_DIR / "golden_history.json"

CHUNKERS = {
    "headings": chunk_by_headings,
    "fixed": chunk_fixed
}


st.set_page_config(
    page_title="Car RAG",
    page_icon="🚗",
    layout="wide"
)


# ==================================================
# מצב Session State
# ==================================================

DEFAULT_STATE = {
    "busy": False,
    "active_action": None,
    "answer_result": None,
    "retrieval_result": None,
    "answers_result": None,
    "last_error": None
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==================================================
# טיפול בשגיאות
# ==================================================

def save_error(error_location, exception):

    st.session_state.last_error = {
        "location": error_location,
        "type": type(exception).__name__,
        "message": str(exception),
        "traceback": traceback.format_exc(),
        "created_at": datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    }

    st.session_state.busy = False
    st.session_state.active_action = None


def show_saved_error():

    error = st.session_state.last_error

    if not error:
        return

    st.error(
        f"שגיאה באזור: {error['location']}\n\n"
        f"{error['type']}: {error['message']}"
    )

    with st.expander("הצגת פרטי השגיאה המלאים", expanded=True):

        st.caption(
            f"מועד השגיאה: {error['created_at']}"
        )

        st.code(
            error["traceback"],
            language="text"
        )

    if st.button("נקה הודעת שגיאה", key="clear_saved_error"):
        st.session_state.last_error = None
        st.rerun()


# ==================================================
# עיצוב RTL
# ==================================================

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        flex-direction: row-reverse;
    }

    section.main {
        direction: ltr;
    }

    [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"],
    [data-testid="stWidgetLabel"],
    [data-testid="stHeadingWithActionElements"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"],
    [data-testid="stExpander"] summary,
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] {
        direction: rtl;
        text-align: right;
        unicode-bidi: plaintext;
    }

    input, textarea {
        direction: rtl !important;
        text-align: right !important;
    }

    [data-testid="stSelectbox"] {
        direction: rtl;
    }

    [data-testid="stSelectbox"] [data-baseweb="select"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] div[role="combobox"],
    [data-testid="stSelectbox"] input,
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] [role="option"] {
        direction: rtl !important;
        text-align: right !important;
    }

    [data-testid="stSelectbox"] [data-baseweb="select"] svg {
        order: 2;
    }

    pre, code, [data-testid="stCode"] {
        direction: ltr !important;
        text-align: left !important;
        unicode-bidi: embed;
    }

    [data-testid="stJson"] {
        direction: ltr;
        text-align: left;
    }

    [data-testid="stButton"] button p,
    [data-testid="stDownloadButton"] button p {
        direction: rtl;
        unicode-bidi: plaintext;
    }

    [data-testid="stSlider"] {
        direction: ltr;
    }

    [data-testid="stSlider"] [data-testid="stWidgetLabel"] {
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSlider"] input[type="range"],
    [data-testid="stSlider"] [data-baseweb="slider"] {
        direction: ltr !important;
    }

    [data-testid="stDataFrame"] {
        direction: ltr;
    }

    [data-testid="stProgress"] {
        direction: ltr;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================
# פונקציות עזר
# ==================================================

def show_table(rows):

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )


def load_golden():

    if not GOLDEN_FILE.exists():
        raise FileNotFoundError(
            f"לא נמצא הקובץ: {GOLDEN_FILE}"
        )

    with open(GOLDEN_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ==================================================
# שמירת היסטוריית הרצות
# ==================================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        history = json.load(file)

    if not isinstance(history, list):
        raise ValueError(
            "קובץ היסטוריית ההרצות חייב להכיל רשימה."
        )

    return history


def save_run(run_data):

    history = load_history()
    history.append(run_data)

    temp_file = HISTORY_FILE.with_suffix(".tmp")

    try:

        with open(temp_file, "w", encoding="utf-8") as file:

            json.dump(
                history,
                file,
                ensure_ascii=False,
                indent=4
            )

        os.replace(temp_file, HISTORY_FILE)

    finally:

        if temp_file.exists():
            temp_file.unlink()


def get_run_config():

    return {
        "chunker": chunker_name,
        "search_mode": search_mode,
        "top_k": top_k,
        "current_only": current_only,
        "query_expansion": use_expansion
    }


def create_run_id():

    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


# ==================================================
# בניית אינדקס
# ==================================================

@st.cache_resource(show_spinner="טוען מסמכים ובונה אינדקס...")
def build_index(chunker_name):

    docs = load_docs(folder=str(BASE_DIR / "data"))

    chunker = CHUNKERS[chunker_name]

    chunks = [
        chunk
        for doc in docs
        for chunk in chunker(doc)
    ]

    index = Index(chunks, Embedder())

    return index, len(docs), len(chunks)


# ==================================================
# כותרת
# ==================================================

st.title("מערכת RAG – אופק רכב")

st.caption(
    "מערכת לשאילת שאלות ולהערכת איכות השליפה והתשובות"
)


# ==================================================
# הגדרות בסרגל הצד
# ==================================================

st.sidebar.header("הגדרות מערכת")

chunker_name = st.sidebar.selectbox(
    "שיטת חלוקת מסמכים",
    options=["headings", "fixed"],
    format_func=lambda x: {
        "headings": "לפי כותרות",
        "fixed": "מקטעים בגודל קבוע"
    }[x],
    disabled=st.session_state.busy
)

search_mode = st.sidebar.selectbox(
    "שיטת חיפוש",
    options=["hybrid", "vector"],
    format_func=lambda x: {
        "hybrid": "משולב – Vector + BM25",
        "vector": "חיפוש וקטורי"
    }[x],
    disabled=st.session_state.busy
)

top_k = st.sidebar.slider(
    "מספר מקטעים לשליפה",
    min_value=1,
    max_value=10,
    value=3,
    disabled=st.session_state.busy
)

current_only = st.sidebar.checkbox(
    "הצג רק מידע עדכני",
    value=False,
    disabled=st.session_state.busy
)

use_expansion = st.sidebar.checkbox(
    "הפעל הרחבת שאילתות באמצעות Groq",
    value=True,
    disabled=st.session_state.busy
)


# ==================================================
# הצגת שגיאה קודמת
# ==================================================

show_saved_error()


# ==================================================
# טעינת האינדקס
# ==================================================

try:

    index, docs_count, chunks_count = build_index(
        chunker_name
    )

    st.sidebar.success("האינדקס נטען בהצלחה")

    st.sidebar.metric("מסמכים", docs_count)
    st.sidebar.metric("מקטעים", chunks_count)

except Exception as e:

    save_error("טעינת האינדקס", e)

    st.error(
        f"שגיאה בטעינת האינדקס: "
        f"{type(e).__name__}: {e}"
    )

    with st.expander("פרטי השגיאה המלאים", expanded=True):
        st.code(traceback.format_exc(), language="text")

    st.stop()


# ==================================================
# פונקציית חיפוש
# ==================================================

def run_search(question):

    if use_expansion:

        return expanded_search(
            index,
            question,
            search_mode,
            top_k,
            current_only
        )

    return search(
        index,
        question,
        search_mode,
        top_k,
        current_only
    )


# ==================================================
# אזור שאלות רגילות
# ==================================================

st.header("שאל את המערכת")

question = st.text_area(
    "הקלד שאלה:",
    placeholder="לדוגמה: מה טווח הנסיעה של OF-E5?",
    height=100,
    disabled=st.session_state.busy,
    key="question_input"
)

submit = st.button(
    "שלח שאלה",
    type="primary",
    disabled=(
        st.session_state.busy
        or not question.strip()
    ),
    key="submit_question"
)


# ==================================================
# כפתורי Golden
# ==================================================

st.divider()

st.header("הרצת בדיקות Golden")

st.write(
    "בחר את סוג הבדיקה שברצונך להריץ על השאלות "
    "שבקובץ golden.json."
)

col1, col2 = st.columns(2)

run_retrieval = col1.button(
    "הרצת Golden – Retrieval",
    use_container_width=True,
    disabled=st.session_state.busy,
    key="run_retrieval"
)

run_answers = col2.button(
    "הרצת Golden – Answers",
    use_container_width=True,
    disabled=st.session_state.busy,
    key="run_answers"
)


# ==================================================
# התחלת פעולה
# ==================================================

def start(action, clear_keys=()):

    for key in clear_keys:
        st.session_state[key] = None

    st.session_state.last_error = None
    st.session_state.active_action = action
    st.session_state.busy = True

    st.rerun()


if submit:

    if not os.environ.get("GROQ_API_KEY"):

        st.error("לא הוגדר GROQ_API_KEY")

    else:

        start(
            "question",
            (
                "answer_result",
                "retrieval_result",
                "answers_result"
            )
        )

elif run_retrieval:

    start(
        "retrieval",
        (
            "answer_result",
            "retrieval_result",
            "answers_result"
        )
    )

elif run_answers:

    if not os.environ.get("GROQ_API_KEY"):

        st.error("לא הוגדר GROQ_API_KEY")

    else:

        start(
            "answers",
            (
                "answer_result",
                "retrieval_result",
                "answers_result"
            )
        )


# ==================================================
# ביצוע: שאלה רגילה
# ==================================================

action = st.session_state.active_action

if st.session_state.busy and action == "question":

    try:

        with st.spinner("מחפש מידע ומייצר תשובה..."):

            chunks = run_search(question)

            answer, usage = ask(
                question,
                chunks
            )

            bad_citations = verify_citations(
                answer,
                chunks
            )

        st.session_state.answer_result = {
            "question": question,
            "chunks": chunks,
            "answer": answer,
            "usage": usage,
            "bad_citations": bad_citations
        }

    except Exception as e:

        save_error("שאלה רגילה", e)

    st.session_state.busy = False
    st.session_state.active_action = None

    st.rerun()


# ==================================================
# ביצוע: Golden Retrieval
# ==================================================

elif st.session_state.busy and action == "retrieval":

    try:

        golden = load_golden()

        results = []

        by_type = defaultdict(
            lambda: [0, 0, 0.0]
        )

        with st.spinner(
            "מריץ בדיקות שליפה על כל שאלות ה-Golden..."
        ):

            for q in golden:

                chunks = run_search(q["question"])

                if not needles(q):

                    results.append({
                        "מזהה": q["id"],
                        "סוג": q["type"],
                        "שאלה": q["question"],
                        "תוצאה": "ללא בדיקת שליפה",
                        "דירוג": "-",
                        "MRR": "-",
                        "מקטעים": ", ".join(
                            c.id for c in chunks
                        )
                    })

                    continue

                hit = is_hit(q, chunks)
                rr = reciprocal_rank(q, chunks)

                by_type[q["type"]][0] += int(hit)
                by_type[q["type"]][1] += 1
                by_type[q["type"]][2] += rr

                results.append({
                    "מזהה": q["id"],
                    "סוג": q["type"],
                    "שאלה": q["question"],
                    "תוצאה": "עבר" if hit else "נכשל",
                    "דירוג": round(1 / rr, 2) if rr else "-",
                    "MRR": round(rr, 3),
                    "מקטעים": ", ".join(
                        c.id for c in chunks
                    )
                })

        total_hits = sum(
            values[0] for values in by_type.values()
        )

        total_questions = sum(
            values[1] for values in by_type.values()
        )

        total_rr = sum(
            values[2] for values in by_type.values()
        )

        metrics = {
            "passed": total_hits,
            "total": total_questions,
            "recall": (
                total_hits / total_questions
                if total_questions else 0
            ),
            "mrr": (
                total_rr / total_questions
                if total_questions else 0
            )
        }

        run_data = {
            "run_id": create_run_id(),
            "created_at": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "kind": "retrieval",
            "config": get_run_config(),
            "metrics": metrics,
            "results": results
        }

        save_run(run_data)

        st.session_state.retrieval_result = {
            "results": results,
            "by_type": dict(by_type),
            "metrics": metrics
        }

    except Exception as e:

        save_error("Golden Retrieval", e)

    st.session_state.busy = False
    st.session_state.active_action = None

    st.rerun()


# ==================================================
# ביצוע: Golden Answers
# ==================================================

elif st.session_state.busy and action == "answers":

    try:

        golden = load_golden()

        results = []

        passed = 0
        tokens_in = 0
        tokens_out = 0

        total = len(golden)

        progress = st.progress(0.0)
        status = st.empty()

        for i, q in enumerate(golden):

            status.write(
                f"מריץ שאלה {i + 1} מתוך {total}: "
                f"{q['question']}"
            )

            chunks = run_search(q["question"])

            answer, usage = ask(
                q["question"],
                chunks
            )

            bad_citations = verify_citations(
                answer,
                chunks
            )

            ok, why = check(
                q,
                answer,
                bad_citations,
                chunks
            )

            passed += int(ok)

            tokens_in += usage.prompt_tokens
            tokens_out += usage.completion_tokens

            results.append({
                "מזהה": q["id"],
                "סוג": q["type"],
                "שאלה": q["question"],
                "תוצאה": "עבר" if ok else "נכשל",
                "סיבת כישלון": why,
                "תשובת המודל": answer.answer,
                "ציטוטים תקינים": (
                    len(answer.citations)
                    - len(bad_citations)
                ),
                "ציטוטים לא תקינים": len(bad_citations)
            })

            if total:
                progress.progress((i + 1) / total)

        status.write("הבדיקה הסתיימה.")

        metrics = {
            "passed": passed,
            "total": total,
            "pass_rate": (
                passed / total if total else 0
            ),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out
        }

        run_data = {
            "run_id": create_run_id(),
            "created_at": datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "kind": "answers",
            "config": get_run_config(),
            "metrics": metrics,
            "results": results
        }

        save_run(run_data)

        st.session_state.answers_result = {
            "results": results,
            "metrics": metrics,
            "passed": passed,
            "total": total,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out
        }

    except Exception as e:

        save_error("Golden Answers", e)

    st.session_state.busy = False
    st.session_state.active_action = None

    st.rerun()


# ==================================================
# הצגת תוצאות שמורות של שאלה רגילה
# ==================================================

result = st.session_state.answer_result

if result:

    answer = result["answer"]
    chunks = result["chunks"]
    bad_citations = result["bad_citations"]
    usage = result["usage"]

    st.subheader("תשובה")

    if answer.insufficient_context:
        st.warning(answer.answer)
    else:
        st.markdown(answer.answer)

    st.subheader("ציטוטים")

    if not answer.citations:
        st.info("לא הוחזרו ציטוטים.")

    for citation in answer.citations:

        if citation in bad_citations:
            st.error(
                f"ציטוט לא אומת: {citation.chunk_id}"
            )
        else:
            st.success(
                f"ציטוט אומת: {citation.chunk_id}"
            )

        st.code(citation.quote)

    st.subheader("מקטעים שנשלפו")

    if not chunks:
        st.warning("לא נמצאו מקטעים.")

    for i, chunk in enumerate(chunks, start=1):

        with st.expander(f"{i}. {chunk.id}"):

            st.write(chunk.text)
            st.json(chunk.meta)

    st.subheader("צריכת טוקנים")

    c1, c2 = st.columns(2)

    c1.metric(
        "Input tokens",
        usage.prompt_tokens
    )

    c2.metric(
        "Output tokens",
        usage.completion_tokens
    )


# ==================================================
# הצגת תוצאות Retrieval
# ==================================================

retrieval = st.session_state.retrieval_result

if retrieval:

    metrics = retrieval["metrics"]

    st.subheader("תוצאות Retrieval")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "שאלות שעברו",
        f"{metrics['passed']}/{metrics['total']}"
    )

    c2.metric(
        "Recall@K",
        f"{metrics['recall']:.2%}"
    )

    c3.metric(
        "MRR",
        f"{metrics['mrr']:.3f}"
    )

    show_table(retrieval["results"])

    st.subheader("מדדים לפי סוג שאלה")

    type_results = []

    for question_type, values in retrieval["by_type"].items():

        hits, count, rr_sum = values

        type_results.append({
            "סוג שאלה": question_type,
            "עברו": f"{hits}/{count}",
            "Recall": round(hits / count, 3) if count else 0,
            "MRR": round(rr_sum / count, 3) if count else 0
        })

    show_table(type_results)


# ==================================================
# הצגת תוצאות Answers
# ==================================================

answers = st.session_state.answers_result

if answers:

    st.subheader("תוצאות Answers")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "שאלות שעברו",
        f"{answers['passed']}/{answers['total']}"
    )

    c2.metric(
        "Input tokens",
        f"{answers['tokens_in']:,}"
    )

    c3.metric(
        "Output tokens",
        f"{answers['tokens_out']:,}"
    )

    show_table(answers["results"])

    st.subheader("פירוט תשובות")

    for result in answers["results"]:

        title = (
            f"שאלה {result['מזהה']} – "
            f"{result['תוצאה']} – "
            f"{result['שאלה']}"
        )

        with st.expander(title):

            st.write("**תשובת המודל:**")
            st.write(result["תשובת המודל"])

            st.write(
                f"ציטוטים תקינים: "
                f"{result['ציטוטים תקינים']}"
            )

            st.write(
                f"ציטוטים לא תקינים: "
                f"{result['ציטוטים לא תקינים']}"
            )

            if result["סיבת כישלון"]:
                st.error(result["סיבת כישלון"])
            else:
                st.success("השאלה עברה את הבדיקה.")


# ==================================================
# היסטוריית הרצות והשוואת תוצאות
# ==================================================

st.divider()

st.header("היסטוריית הרצות Golden")

try:

    history = load_history()

except Exception as e:

    save_error("טעינת היסטוריית הרצות", e)
    history = []

if not history:

    st.info("עדיין לא נשמרו הרצות Golden.")

else:

    history = sorted(
        history,
        key=lambda x: x["run_id"],
        reverse=True
    )

    history_rows = []

    for run in history:

        metrics = run["metrics"]

        if run["kind"] == "retrieval":
            score = f"{metrics['recall']:.2%}"
        else:
            score = f"{metrics['pass_rate']:.2%}"

        history_rows.append({
            "תאריך": run["created_at"],
            "מזהה הרצה": run["run_id"],
            "סוג בדיקה": run["kind"],
            "שיטת חלוקה": run["config"]["chunker"],
            "שיטת חיפוש": run["config"]["search_mode"],
            "Top K": run["config"]["top_k"],
            "מידע עדכני בלבד": run["config"]["current_only"],
            "הרחבת שאילתות": run["config"]["query_expansion"],
            "עברו": f"{metrics['passed']}/{metrics['total']}",
            "מדד הצלחה": score
        })

    st.subheader("כל ההרצות")
    show_table(history_rows)

    st.subheader("השוואה בין שתי הרצות")

    run_kind = st.selectbox(
        "סוג הבדיקות להשוואה",
        options=["retrieval", "answers"],
        format_func=lambda x: {
            "retrieval": "Retrieval",
            "answers": "Answers"
        }[x],
        key="comparison_kind"
    )

    matching_runs = [
        run for run in history
        if run["kind"] == run_kind
    ]

    if len(matching_runs) < 2:

        st.info(
            "נדרשות לפחות שתי הרצות מאותו סוג כדי לבצע השוואה."
        )

    else:

        options = list(range(len(matching_runs)))

        def run_label(i):

            run = matching_runs[i]

            return (
                f"{run['created_at']} | "
                f"{run['config']['chunker']} | "
                f"{run['config']['search_mode']} | "
                f"Top K={run['config']['top_k']}"
            )

        col1, col2 = st.columns(2)

        first_index = col1.selectbox(
            "הרצה ראשונה",
            options=options,
            format_func=run_label,
            index=1,
            key="comparison_first"
        )

        second_index = col2.selectbox(
            "הרצה שנייה",
            options=options,
            format_func=run_label,
            index=0,
            key="comparison_second"
        )

        first_run = matching_runs[first_index]
        second_run = matching_runs[second_index]

        if first_index == second_index:

            st.warning("יש לבחור שתי הרצות שונות.")

        else:

            m1 = first_run["metrics"]
            m2 = second_run["metrics"]

            st.markdown("### השוואת מדדים")

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "שאלות שעברו – הרצה ראשונה",
                f"{m1['passed']}/{m1['total']}"
            )

            c2.metric(
                "שאלות שעברו – הרצה שנייה",
                f"{m2['passed']}/{m2['total']}",
                delta=m2["passed"] - m1["passed"]
            )

            if run_kind == "retrieval":

                st.markdown("#### מדדי Retrieval")

                metric_cols = st.columns(2)

                metric_cols[0].metric(
                    "Recall@K – הרצה ראשונה",
                    f"{m1['recall']:.2%}"
                )

                metric_cols[1].metric(
                    "Recall@K – הרצה שנייה",
                    f"{m2['recall']:.2%}",
                    delta=f"{(m2['recall'] - m1['recall']):.2%}"
                )

                metric_cols = st.columns(2)

                metric_cols[0].metric(
                    "MRR – הרצה ראשונה",
                    f"{m1['mrr']:.3f}"
                )

                metric_cols[1].metric(
                    "MRR – הרצה שנייה",
                    f"{m2['mrr']:.3f}",
                    delta=round(m2["mrr"] - m1["mrr"], 3)
                )

            else:

                st.markdown("#### Pass Rate")

                metric_cols = st.columns(2)

                metric_cols[0].metric(
                    "הרצה ראשונה",
                    f"{m1['pass_rate']:.2%}"
                )

                metric_cols[1].metric(
                    "הרצה שנייה",
                    f"{m2['pass_rate']:.2%}",
                    delta=f"{(m2['pass_rate'] - m1['pass_rate']):.2%}"
                )

                st.markdown("#### צריכת טוקנים")

                token_rows = [
                    {
                        "סוג טוקנים": "Input",
                        "הרצה ראשונה": m1["tokens_in"],
                        "הרצה שנייה": m2["tokens_in"],
                        "הפרש": m2["tokens_in"] - m1["tokens_in"]
                    },
                    {
                        "סוג טוקנים": "Output",
                        "הרצה ראשונה": m1["tokens_out"],
                        "הרצה שנייה": m2["tokens_out"],
                        "הפרש": m2["tokens_out"] - m1["tokens_out"]
                    }
                ]

                show_table(token_rows)

            st.markdown("### השוואת הגדרות")

            config_rows = []

            for key in first_run["config"]:

                value1 = first_run["config"][key]
                value2 = second_run["config"][key]

                config_rows.append({
                    "הגדרה": key,
                    "הרצה ראשונה": str(value1),
                    "הרצה שנייה": str(value2),
                    "האם השתנתה": (
                        "כן" if value1 != value2 else "לא"
                    )
                })

            show_table(config_rows)

            st.markdown("### השוואת תוצאות לפי שאלה")

            first_results = {
                str(row["מזהה"]): row
                for row in first_run["results"]
            }

            second_results = {
                str(row["מזהה"]): row
                for row in second_run["results"]
            }

            all_ids = sorted(
                set(first_results) | set(second_results)
            )

            comparison_rows = []

            for question_id in all_ids:

                r1 = first_results.get(question_id, {})
                r2 = second_results.get(question_id, {})

                status1 = r1.get("תוצאה", "לא קיימת")
                status2 = r2.get("תוצאה", "לא קיימת")

                if status1 == "נכשל" and status2 == "עבר":
                    change = "שיפור"

                elif status1 == "עבר" and status2 == "נכשל":
                    change = "הרעה"

                elif status1 == status2:
                    change = "ללא שינוי"

                else:
                    change = "לא ניתן להשוות"

                comparison_rows.append({
                    "מזהה": question_id,
                    "שאלה": r2.get(
                        "שאלה",
                        r1.get("שאלה", "")
                    ),
                    "הרצה ראשונה": status1,
                    "הרצה שנייה": status2,
                    "שינוי": change
                })

            show_table(comparison_rows)

            st.markdown("### פרטי ההרצות")

            with st.expander("הצגת הגדרות ההרצה הראשונה"):
                st.json(first_run["config"])

            with st.expander("הצגת הגדרות ההרצה השנייה"):
                st.json(second_run["config"])

    st.divider()

    st.download_button(
        "הורדת היסטוריית ההרצות (JSON)",
        data=json.dumps(
            history,
            ensure_ascii=False,
            indent=4
        ),
        file_name="golden_history.json",
        mime="application/json",
        use_container_width=True
    )
