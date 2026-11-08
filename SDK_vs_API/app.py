
import streamlit as st
from API.agent import run_agent

st.set_page_config(
    page_title="MeetSpot",
    page_icon="📍",
    layout="centered",
)

st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        direction: rtl;
        text-align: right;
    }

    [data-testid="stHeader"] {
        direction: rtl;
    }

    [data-testid="stChatMessage"] {
        direction: rtl;
        text-align: right;
    }

    [data-testid="stChatMessage"] p {
        text-align: right;
    }

    [data-testid="stChatInput"] {
        direction: rtl;
    }

    [data-testid="stChatInput"] textarea {
        direction: rtl;
        text-align: right;
    }

    h1, h2, h3, p, label {
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("📍 MeetSpot")
st.caption("העוזר שלכם למציאת מקומות לפגישות")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "שלום! אני יכול לעזור לכם למצוא מקום מתאים לפגישה הבאה. "
                "תאר לי בשפה חופשית מה אתם מחפשים."
            ),
        }
    ]

# הצגת היסטוריית השיחה
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# קלט המשתמש
if prompt := st.chat_input("כתוב מה אתם מחפשים..."):
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("מחפש מקומות מתאימים..."):
            try:
                answer = run_agent(prompt)

                if answer is None:
                    answer = "לא התקבלה תשובה מהסוכן."

                st.markdown(str(answer))

            except Exception:
                st.error(
                    "אירעה שגיאה בהפעלת הסוכן. "
                    "בדוק את הלוגים של היישום."
                )
                raise

    st.session_state.messages.append(
        {"role": "assistant", "content": str(answer)}
    )
