import streamlit as st

st.set_page_config(page_title="Chat RAG - Cabinet", page_icon="💬", layout="wide")

st.title("Chat interne RAG")
st.markdown(
    "Interface de démonstration : page Chat pour interroger les documents indexés, "
    "page Documents pour gérer l'index."
)

st.info(
    "Chargez des documents dans la page Documents puis posez vos questions depuis la page Chat."
)
