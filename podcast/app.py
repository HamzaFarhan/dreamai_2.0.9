import json
from copy import deepcopy
import streamlit as st
from pod_ai import (
    Info,
    ask_cld,
    get_segments_between,
    merge_same_role_messages,
    sys_message,
)

from dreamai.ai import ModelName, assistant_message, user_message

st.set_page_config(page_title="DreamPod")
st.title("DreamPod 🎙️✨")


@st.cache_data
def load_segments(path: str = "segments.json") -> list[dict]:
    return json.load(open(path))


segments = load_segments()

if "messages" not in st.session_state.keys():
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "What would you like to know?",
        }
    ]
if "used_timestamps" not in st.session_state.keys():
    st.session_state.used_timestamps = []

audio_file = "audios/TacticsFC/[20240222]Do teams want superstars anymore.mp3"
st.audio(audio_file, format="audio/mp3")

timestamp = st.number_input("Timestamp", min_value=30.0, step=10.0)
if prompt := st.chat_input("Your question"):
    prompt = user_message(prompt)
    st.session_state.messages.append(prompt)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    messages = deepcopy(st.session_state.messages[1:])
    # if timestamp not in st.session_state.used_timestamps:
    segments_until_timestamp = get_segments_between(segments, end=timestamp)
    transcript_message = user_message(
        f"TRANSCRIPT UNTIL {timestamp} SECONDS\n\n{json.dumps(segments_until_timestamp)}"
    )
    messages.append(transcript_message)
    # st.session_state.used_timestamps.append(timestamp)
    print(f"\n\nMESSAGES\n\n{messages}\n\n")
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            info = ask_cld.create(
                system=sys_message,
                messages=merge_same_role_messages(messages),  # type: ignore
                model=ModelName.HAIKU,
                max_tokens=1024,
                response_model=Info,
            )
            message = assistant_message(info.model_dump_json())
            st.write(message["content"])
            st.session_state.messages.append(message)
