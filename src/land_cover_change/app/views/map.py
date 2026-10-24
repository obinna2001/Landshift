import streamlit as st

with st.container(key="title-section"):
    with st.container(key="title-content"):
        st.html(
            """
            <p class="hero-eyebrow">
                land cover land change map
            </p>

            <h1 class="hero-title">
                Explore the landscape across three study years    
            </h1>

            <p class="hero-lead">
                Explore land-cover patterns across Uteh, Iwogban and nearby communities
            </p>
            """
        )

    with st.container(key="main-content"):
        with st.container(key="map-selection"):
            st.html("""<h1>Placeholder for map widgets - drop down</h1>""")

            
        with st.container(key="map"):
            st.html("""<h1> Map box </h1>""")