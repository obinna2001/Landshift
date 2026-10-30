from pathlib import Path
import sys

import streamlit as st

# Make the src package root available when Streamlit runs this file directly.
SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from landshift.ui.components.styles import load_app_style


def main():
    # Configure the shared browser tab and layout before creating any page elements.
    st.set_page_config(
        page_title="Urban land-cover change",
        page_icon=":material/map:",
        layout="wide",
    )

    # Define the pages after applying the shared app configuration.
    home_page = st.Page("ui/views/home.py", title="Home", default=True)
    area_page = st.Page("ui/views/area_analysis.py", title="Area Analysis")
    transition_page = st.Page("ui/views/transition_analysis.py", title="Transition Analysis")

    page = st.navigation(
        [home_page, area_page, transition_page],
        position="top",
        expanded=True,
    )

    # load custom css style
    load_app_style()

    # run pages
    page.run()

    
    with st.container(key="footer", gap=None):
        with st.container(key="footer-content", gap=None):
            with st.container(key="footer-grid", gap=None):
                with st.container(key="footer-navigation", gap=None):
                    st.html('<h2 id="footer-navigation-heading">Navigation</h2>')
                    st.page_link("ui/views/home.py", label="Home", width="stretch")
                    st.page_link("ui/views/area_analysis.py", label="Area Analysis", width="stretch")
                    st.page_link("ui/views/transition_analysis.py", label="Transition Analysis", width="stretch")

                with st.container(key="footer-resources", gap=None):
                    st.html('<h2 id="footer-resources-heading">Resources</h2>')
                    st.html(
                        """
                        <nav class="footer-link-list" aria-labelledby="footer-resources-heading">
                            <a target="_blank" rel="noopener noreferrer"
                                href="https://data.grid3.org/datasets/GRID3::grid3-nga-operational-wards-v1-0/about">
                                Administrative Boundaries
                            </a>
                            <a target="_blank" rel="noopener noreferrer"
                                href="https://dynamicworld.app/">
                                Dynamic World V1
                            </a>
                            <a target="_blank" rel="noopener noreferrer"
                                href="https://code.earthengine.google.com/ce4354f43bb0776d1be7e5984d8a7b79">
                                Google Earth Engine Script
                            </a>
                        </nav>
                        """
                    )

                with st.container(key="footer-contact", gap=None):
                    st.html('<h2 id="footer-contact-heading">Contact</h2>')
                    st.html(
                        """
                        <nav class="footer-link-list footer-contact-links" aria-labelledby="footer-contact-heading">
                            <a target="_blank" rel="noopener noreferrer"
                                href="mailto:okeyobinna2001@gmail.com">
                                Email
                            </a>
                            <a target="_blank" rel="noopener noreferrer"
                                href="https://github.com/obinna2001">
                                GitHub
                            </a>
                        </nav>
                        """
                    )

            st.html(
                '<div class="footer-meta">'
                '<p class="footer-copyright">&copy; 2026, Okey Obinna</p>'
                '<p class="footer-study">2016–2025 · Benin City</p>'
                '</div>'
            )



if __name__ == "__main__":
    main()