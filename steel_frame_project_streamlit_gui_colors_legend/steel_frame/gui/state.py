from __future__ import annotations

import streamlit as st


def initialize_state() -> None:
    defaults = {
        "module1_results": None,
        "module2_results": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
