import streamlit as st


with st.container(key="title-section"):
    with st.container(key="title-content"):
        st.markdown(
            """
                <p class="hero-eyebrow">
                    2016–2025 · BENIN CITY, NIGERIA
                </p>

                <h1 class="hero-title">
                    How is the landscape around Uteh and Iwogban changing?
                </h1>
                
                <p class="hero-lead">
                    An interactive study of land-cover patterns across a 57.64 km² peri-urban landscape, 
                    using Dynamic World imagery 2016, 2020 and 2025
                </p>
            """,
            unsafe_allow_html=True,
        )


with st.container(key="main-content"):
    # Project Overview and Study area
    with st.container(key="project-overview"):
        st.html(
            """
            <section
                id="project"
                class="section-shell project-layout"
                aria-labelledby="project-heading"
            >
                <article class="project-copy">
                    <p class="section-label">The project</p>

                    <h2>A personal question, examined spatially</h2>

                    <p>
                        This project began as an inquiry into how much the landscape has changed across Uteh,
                        Iwogban and nearby communities. Having spent much of the past decade in and around the
                        study area, I wanted to examine those changes systematically.
                    </p>

                    <p>
                        The analysis compares land-cover maps for 2016, 2020 and 2025. It documents observed spatial
                        change without assuming that every conversion was caused exclusively by urbanisation.
                    </p>
                </article>

                <aside aria-labelledby="study-area-heading">
                    <h2 class="section-label" id="study-area-heading">Study area</h2>

                    <dl class="study-facts-list">
                        <div class="study-facts">
                            <dt>Location</dt>
                            <dd>Edo State, Nigeria</dd>
                        </div>

                        <div class="study-facts">
                            <dt>Size</dt>
                            <dd>57.64 km²</dd>
                        </div>

                        <div class="study-facts">
                            <dt>Landscape</dt>
                            <dd>Peri-urban</dd>
                        </div>

                        <div class="study-facts">
                            <dt>Observation years</dt>
                            <dd>2016 · 2020 · 2025</dd>
                        </div>

                        <div class="study-facts">
                            <dt>Spatial resolution</dt>
                            <dd>10 metres</dd>
                        </div>

                        <div class="study-facts">
                            <dt>Projection</dt>
                            <dd>WGS 84 / UTM 31N</dd>
                        </div>
                    </dl>
                </aside>
            </section>
            """
        )

    # Methodology
    with st.container(key="method-section"):
        st.html(
            """
            <section
                id="methodology"
                class="section-shell method-layout"
                aria-labelledby="method-heading"
            >
                <article class="methodology-content">
                    <div class="method-head">
                        <div class="method-title-group">
                            <p class="section-label">Method at a glance</p>

                            <h2 id="method-heading">From satellite observation to evidence</h2>
                        </div>

                        <p class="method-introduction">
                            Dynamic World labels were clipped to the study boundary, measured by class,
                            and compared across the three study years.
                        </p>
                    </div>

                    <div class="method-list">
                        <div class="method-step">
                            <p class="step-number">01</p>
                            <h3 class="step-title">Map</h3>
                            <p class="step-description">Inspect land-cover patterns for each study year.</p>
                        </div>

                        <div class="method-step">
                            <p class="step-number">02</p>
                            <h3 class="step-title">Measure</h3>
                            <p class="step-description">Calculate area and share for every land-cover class.</p>
                        </div>

                        <div class="method-step">
                            <p class="step-number">03</p>
                            <h3 class="step-title">Compare</h3>
                            <p class="step-description">Identify persistence and transitions between classes.</p>
                        </div>
                    </div>

                </article>
            </section>
            """
        )

    # Data sources
    with st.container(key="sources-section"):
        st.html(
            """
            <section
                id="data-sources"
                class="section-shell sources-layout"
                aria-labelledby="data-sources-heading"
            >
                <p class="section-label">Data sources</p>

                <h2 id="data-sources-heading">Open data, documented clearly</h2>

                <p class="sources-introduction">
                    The analysis combines satellite-derived land-cover labels with administrative boundary
                    data and a reproducible acquisition.
                </p>

                <div class="sources-list">
                    <article>
                        <h3 class="source-title">Dynamic World V1</h3>

                        <p class="source-content">
                            10-metre land-cover labels derived from Sentinel-2 imagery for 2016, 2020 and 2025.
                        </p>

                        <a
                            href="https://dynamicworld.app/"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="View Dynamic World V1 dataset"
                        >
                            View dataset
                        </a>
                    </article>

                    <article>
                        <h3 class="source-title">GRID3 boundaries</h3>

                        <p class="source-content">
                            Nigeria operational ward boundaries used to locate and prepare the study area.
                        </p>

                        <a
                            href="https://data.grid3.org/datasets/GRID3::grid3-nga-operational-wards-v1-0/about"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="View GRID3 Nigeria Operational Wards v1.0 dataset"
                        >
                            View dataset
                        </a>
                    </article>

                    <article>
                        <h3 class="source-title">Earth Engine workflow</h3>

                        <p class="source-content">
                            The acquisition and export script used to prepare the Dynamic World GeoTIFF files.
                        </p>

                        <a
                            href="https://code.earthengine.google.com/ce4354f43bb0776d1be7e5984d8a7b79"
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label="View Google Earth Engine workflow script"
                        >
                            View script
                        </a>
                    </article>
                </div>
            </section>
            """
        )
    
    # Key findings
    with st.container(key="key-findings-section"):
        st.html(
            """
            <section
                id="key-findings"
                class="section-shell"
            >
                <div class="key-findings-heading">
                    <p class="section-label">Key findings</p>

                    <h2 id="key-findings-header">The clearest signals of a changing landscape</h2>

                    <p id="key-findings-introduction">
                        Three measures capture the scale and direction of change across Uteh, 
                        Iwogban and nearby communities, from the growth of built land and loss 
                        of tree cover to the landscape’s largest mapped conversion.
                    </p>
                </div>

                <div id="key-findings-cards">

                    <div class="score-card">
                        <p class="key-findings-card-label">Built area in 2025</p>
                        <p class="key-findings-card-value">36.43 km²</p>
                        <p class="key-findings-card-description">
                            <span class="highlight-text">+14.28 km²</span> since 2016
                        </p>
                    </div>

                    <div class="score-card">
                        <p class="key-findings-card-label">Tree cover in 2025</p>
                        <p class="key-findings-card-value">11.76 km²</p>
                        <p class="key-findings-card-description">
                            <span class="highlight-text negative">−19.30 km²</span> since 2016
                        </p>
                    </div>

                    <div class="score-card">
                        <p class="key-findings-card-label">Largest conversion</p>
                        <p class="key-findings-card-value">3.40 km²</p>
                        <p class="key-findings-card-description">Trees → built · 2016–2020</p>
                    </div>
                </div>
            </section>    
            """
        )