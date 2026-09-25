import streamlit as st
from streamlit_drawable_canvas import st_canvas
import math
from PIL import Image, ImageDraw

st.set_page_config(
    page_title="SFD BMD Calculator",
    layout="wide"
)

st.title("Structural Sketch → Structural Model")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Hand Sketch")

stroke_width = st.sidebar.slider(
    "Stroke width",
    1,
    10,
    3
)

canvas_width = st.sidebar.number_input(
    "Canvas width",
    min_value=500,
    max_value=1500,
    value=1000
)

canvas_height = st.sidebar.number_input(
    "Canvas height",
    min_value=300,
    max_value=900,
    value=600
)

# =========================================================
# HAND SKETCH CANVAS
# =========================================================

st.header("1. Hand Sketch")

st.write(
    "Draw your structural system freely. "
    "The interpretation will appear below."
)

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=stroke_width,
    stroke_color="#000000",
    background_color="#FFFFFF",
    height=canvas_height,
    width=canvas_width,
    drawing_mode="freedraw",
    key="hand_sketch_canvas",
)

# =========================================================
# GEOMETRY FUNCTIONS
# =========================================================

def distance(x1, y1, x2, y2):

    return math.sqrt(
        (x2 - x1) ** 2 +
        (y2 - y1) ** 2
    )


def extract_stroke_points(stroke):

    path = stroke.get("path", [])

    points = []

    for item in path:

        if len(item) >= 3:

            command = item[0]

            if command in ["M", "L"]:

                x = item[1]
                y = item[2]

                points.append((x, y))

    return points


def get_stroke_geometry(stroke):

    points = extract_stroke_points(stroke)

    if len(points) < 2:
        return None

    x1, y1 = points[0]
    x2, y2 = points[-1]

    length = distance(
        x1,
        y1,
        x2,
        y2
    )

    if length < 40:
        return None

    angle = math.degrees(
        math.atan2(
            y2 - y1,
            x2 - x1
        )
    )

    # Normalize angle
    while angle < 0:
        angle += 180

    while angle >= 180:
        angle -= 180

    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "length": length,
        "angle": angle
    }


# =========================================================
# STRUCTURAL MODEL RENDERER
# =========================================================

def create_structural_model():

    image = Image.new(
        "RGB",
        (
            int(canvas_width),
            int(canvas_height)
        ),
        "white"
    )

    draw = ImageDraw.Draw(image)

    if canvas_result.json_data is None:
        return image, []

    objects = canvas_result.json_data.get(
        "objects",
        []
    )

    detected_members = []

    for obj in objects:

        if obj.get("type") != "path":
            continue

        geometry = get_stroke_geometry(obj)

        if geometry is None:
            continue

        x1 = geometry["x1"]
        y1 = geometry["y1"]
        x2 = geometry["x2"]
        y2 = geometry["y2"]

        detected_members.append(
            geometry
        )

        # -------------------------------------------------
        # CLEAN MEMBER
        # -------------------------------------------------

        draw.line(
            [
                (x1, y1),
                (x2, y2)
            ],
            fill="black",
            width=5
        )

        # -------------------------------------------------
        # CLEAN NODES
        # -------------------------------------------------

        node_radius = 6

        draw.ellipse(
            [
                x1 - node_radius,
                y1 - node_radius,
                x1 + node_radius,
                y1 + node_radius
            ],
            fill="black"
        )

        draw.ellipse(
            [
                x2 - node_radius,
                y2 - node_radius,
                x2 + node_radius,
                y2 + node_radius
            ],
            fill="black"
        )

    return image, detected_members


# =========================================================
# INTERPRET BUTTON
# =========================================================

st.divider()

interpret = st.button(
    "Interpret Sketch",
    type="primary"
)

# =========================================================
# STRUCTURAL MODEL
# =========================================================

st.header("2. Structural Model")

st.write(
    "The interpreted structural model will appear here "
    "as clean geometric objects."
)

if interpret:

    structural_image, members = create_structural_model()

    st.image(
        structural_image,
        width=int(canvas_width)
    )

    # -----------------------------------------------------
    # MODEL DATA
    # -----------------------------------------------------

    st.subheader("Detected Structural Model")

    if not members:

        st.warning(
            "No structural members were detected."
        )

    else:

        st.success(
            f"{len(members)} structural member(s) detected."
        )

        for i, member in enumerate(
            members,
            start=1
        ):

            st.write(
                f"**Member {i}**"
            )

            st.write(
                f"Start: "
                f"({member['x1']:.1f}, "
                f"{member['y1']:.1f})"
            )

            st.write(
                f"End: "
                f"({member['x2']:.1f}, "
                f"{member['y2']:.1f})"
            )

            st.write(
                f"Length: "
                f"{member['length']:.1f} px"
            )

            st.write(
                f"Angle: "
                f"{member['angle']:.1f}°"
            )

else:

    # Empty structural model canvas
    empty_image = Image.new(
        "RGB",
        (
            int(canvas_width),
            int(canvas_height)
        ),
        "white"
    )

    st.image(
        empty_image,
        width=int(canvas_width)
    )

    st.info(
        "Draw your structure above and click "
        "'Interpret Sketch'."
    )
