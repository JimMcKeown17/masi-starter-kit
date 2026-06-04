import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4o-mini"


st.title("Ask AI")
st.write("Type a question and send it to a model on OpenRouter.")


question = st.text_input("Your question")


if st.button("Ask") and question:
    api_key = os.getenv("OPENROUTER_API_KEY")

    response = requests.post(
        OPENROUTER_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": question}],
        },
        timeout=60,
    )
    response.raise_for_status()

    answer = response.json()["choices"][0]["message"]["content"]
    st.write(answer)
