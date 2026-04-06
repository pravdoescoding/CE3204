from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_home_page(data_dir: Path) -> None:
    st.title("CE3204 Steel Frame Analysis and Optimization")
    st.markdown(
        """
This app is a GUI built on top of the existing CE3204 backend.

**Module 1** checks a user-defined design and returns utilization ratios and total cost.

**Module 2** searches for the lowest-cost design that satisfies the chosen constraints.
        """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Module 1")
        st.write("Input geometry, loads, sections, grades, and design standard. Then run analysis.")
    with col2:
        st.subheader("Module 2")
        st.write("Input geometry, loads, and constraints. Then run optimization or view infeasibility diagnostics.")

    st.subheader("Project files")
    st.code(f"Data folder: {data_dir}")
    st.info("Use the sidebar to open Module 1 or Module 2.")
