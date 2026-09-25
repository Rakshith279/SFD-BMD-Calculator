import streamlit as st
from streamlit_drawable_canvas import st_canvas

st.set_page_config(
    page_title="Structural Sketch",
    page_icon="🏗️",
    layout="wide"
)

st.title("Structural Sketch → Structural Model")

st.write(
    "Draw your structural system in the canvas. "
    "Interpretation will be added in the next stage."
)

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Drawing Tools")

drawing_mode = st.sidebar.selectbox(
    "Tool",
    (
        "freedraw",
        "line",
        "rect",
        "circle",
        "transform",
    ),
    index=0,
)

stroke_width = st.sidebar.slider(
    "Stroke width",
    min_value=1,
    max_value=10,
    value=3,
)

stroke_color = st.sidebar.color_picker(
    "Stroke color",
    "#000000",
)

background_color = st.sidebar.color_picker(
    "Canvas background",
    "#FFFFFF",
)

canvas_width = st.sidebar.slider(
    "Canvas width",
    min_value=600,
    max_value=1400,
    value=1000,
    step=50,
)

canvas_height = st.sidebar.slider(
    "Canvas height",
    min_value=400,
    max_value=800,
    value=600,
    step=50,
)

# ---------------------------------------------------------
# Canvas
# ---------------------------------------------------------

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_color=background_color,
    background_image=None,
    update_streamlit=True,
    height=canvas_height,
    width=canvas_width,
    drawing_mode=drawing_mode,
    point_display_radius=0,
    key="structural_canvas",
)

# ---------------------------------------------------------
# Canvas information
# ---------------------------------------------------------

if canvas_result.json_data is not None:

    objects = canvas_result.json_data["objects"]

    st.subheader("Canvas Data")

    st.write(
        f"Number of drawn objects: **{len(objects)}**"
    )

    with st.expander("View raw drawing data"):
        st.json(canvas_result.json_data)

    # -----------------------------------------------------
    # Simple object listing
    # -----------------------------------------------------

    if objects:

        st.subheader("Detected Drawing Objects")

        for i, obj in enumerate(objects):

            obj_type = obj.get("type", "unknown")

            st.write(
                f"**Object {i + 1}:** `{obj_type}`"
            )

else:

    st.info("Start drawing on the canvas.")
