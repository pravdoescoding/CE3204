from __future__ import annotations

from pathlib import Path

import streamlit as st

from steel_frame.gui.page_home import render_home_page
from steel_frame.gui.page_module1 import render_module1_page
from steel_frame.gui.page_module2 import render_module2_page
from steel_frame.gui.state import initialize_state
from steel_frame.gui.widgets import load_reference_data


def main() -> None:
    st.set_page_config(
        page_title="CE3204 Steel Frame Optimizer",
        page_icon="🏗️",
        layout="wide",
    )
    initialize_state()
    data_dir = Path(__file__).resolve().parent / "data"
    refs = load_reference_data(data_dir)

    st.sidebar.title("CE3204 Steel Frame")
    page = st.sidebar.radio("Go to", ["Home", "Module 1", "Module 2"], index=0)
    st.sidebar.caption("Backend logic is unchanged. This app is a GUI layer on top of the existing project code.")

    if page == "Home":
        render_home_page(data_dir)
    elif page == "Module 1":
        render_module1_page(data_dir, refs)
    else:
        render_module2_page(data_dir, refs)


if __name__ == "__main__":
    main()
