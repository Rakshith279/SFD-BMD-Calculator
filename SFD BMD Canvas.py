import streamlit as st
import math

st.set_page_config(
    page_title="Structural Engineering Canvas",
    layout="wide"
)

# =========================================================
# PAGE
# =========================================================

st.title("Structural Engineering Canvas")

st.caption(
    "Create a clean geometric representation of a structural system."
)

# =========================================================
# SESSION STATE
# =========================================================

if "objects" not in st.session_state:
    st.session_state.objects = []

if "selected_tool" not in st.session_state:
    st.session_state.selected_tool = "Beam"

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Structural Objects")

tool = st.sidebar.radio(
    "Select object",
    [
        "Beam",
        "Pin Support",
        "Roller Support",
        "Fixed Support",
        "Point Load",
        "UDL",
        "Moment"
    ]
)

st.session_state.selected_tool = tool

st.sidebar.divider()

st.sidebar.header("Canvas")

snap = st.sidebar.checkbox(
    "Snap to grid",
    value=True
)

grid_size = st.sidebar.slider(
    "Grid spacing",
    10,
    100,
    25
)

st.sidebar.divider()

if st.sidebar.button("Clear Structure"):
    st.session_state.objects = []
    st.rerun()

# =========================================================
# CANVAS SIZE
# =========================================================

WIDTH = 1100
HEIGHT = 650

# =========================================================
# SNAP
# =========================================================

def snap_value(value):

    if not snap:
        return value

    return round(value / grid_size) * grid_size


def snap_point(x, y):

    return (
        snap_value(x),
        snap_value(y)
    )

# =========================================================
# GEOMETRY
# =========================================================

def distance(p1, p2):

    return math.sqrt(
        (p2[0] - p1[0]) ** 2 +
        (p2[1] - p1[1]) ** 2
    )


def draw_line(canvas, p1, p2, width=4):

    canvas.line(
        [p1[0], p1[1], p2[0], p2[1]],
        fill="black",
        width=width
    )


# =========================================================
# OBJECT CREATION
# =========================================================

def create_beam(x1, y1, x2, y2):

    return {
        "type": "beam",
        "start": [x1, y1],
        "end": [x2, y2]
    }


def create_pin(x, y):

    return {
        "type": "pin",
        "position": [x, y]
    }


def create_roller(x, y):

    return {
        "type": "roller",
        "position": [x, y]
    }


def create_fixed(x, y):

    return {
        "type": "fixed",
        "position": [x, y]
    }


def create_point_load(x, y, magnitude=10):

    return {
        "type": "point_load",
        "position": [x, y],
        "magnitude": magnitude
    }


def create_udl(x1, y1, x2, y2, magnitude=10):

    return {
        "type": "udl",
        "start": [x1, y1],
        "end": [x2, y2],
        "magnitude": magnitude
    }


def create_moment(x, y, magnitude=10):

    return {
        "type": "moment",
        "position": [x, y],
        "magnitude": magnitude
    }

# =========================================================
# RENDERING
# =========================================================

from PIL import Image, ImageDraw


def render_structure():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        "white"
    )

    draw = ImageDraw.Draw(image)

    # -----------------------------------------------------
    # GRID
    # -----------------------------------------------------

    if snap:

        for x in range(0, WIDTH, grid_size):

            draw.line(
                [(x, 0), (x, HEIGHT)],
                fill="#eeeeee",
                width=1
            )

        for y in range(0, HEIGHT, grid_size):

            draw.line(
                [(0, y), (WIDTH, y)],
                fill="#eeeeee",
                width=1
            )

    # -----------------------------------------------------
    # OBJECTS
    # -----------------------------------------------------

    for obj in st.session_state.objects:

        obj_type = obj["type"]

        # =================================================
        # BEAM
        # =================================================

        if obj_type == "beam":

            x1, y1 = obj["start"]
            x2, y2 = obj["end"]

            draw.line(
                [(x1, y1), (x2, y2)],
                fill="black",
                width=5
            )

        # =================================================
        # PIN SUPPORT
        # =================================================

        elif obj_type == "pin":

            x, y = obj["position"]

            size = 25

            draw.polygon(
                [
                    (x, y),
                    (x - size, y + size),
                    (x + size, y + size)
                ],
                outline="black",
                fill="white"
            )

            # Ground
            draw.line(
                [
                    (x - size - 10, y + size),
                    (x + size + 10, y + size)
                ],
                fill="black",
                width=3
            )

            # Ground hatch
            for i in range(-size, size + 10, 10):

                draw.line(
                    [
                        (x + i, y + size),
                        (x + i - 8, y + size + 8)
                    ],
                    fill="black",
                    width=2
                )

        # =================================================
        # ROLLER SUPPORT
        # =================================================

        elif obj_type == "roller":

            x, y = obj["position"]

            size = 22

            draw.polygon(
                [
                    (x, y),
                    (x - size, y + size),
                    (x + size, y + size)
                ],
                outline="black",
                fill="white"
            )

            # Wheels
            draw.ellipse(
                [
                    x - 17,
                    y + size - 1,
                    x - 3,
                    y + size + 13
                ],
                outline="black",
                width=2
            )

            draw.ellipse(
                [
                    x + 3,
                    y + size - 1,
                    x + 17,
                    y + size + 13
                ],
                outline="black",
                width=2
            )

            # Ground
            ground_y = y + size + 13

            draw.line(
                [
                    (x - 30, ground_y),
                    (x + 30, ground_y)
                ],
                fill="black",
                width=3
            )

        # =================================================
        # FIXED SUPPORT
        # =================================================

        elif obj_type == "fixed":

            x, y = obj["position"]

            wall_width = 12
            wall_height = 55

            draw.rectangle(
                [
                    x - wall_width,
                    y - wall_height,
                    x,
                    y + wall_height
                ],
                outline="black",
                fill="white"
            )

            for yy in range(
                y - wall_height,
                y + wall_height,
                10
            ):

                draw.line(
                    [
                        (x - wall_width, yy),
                        (x - wall_width - 10, yy + 10)
                    ],
                    fill="black",
                    width=2
                )

        # =================================================
        # POINT LOAD
        # =================================================

        elif obj_type == "point_load":

            x, y = obj["position"]

            arrow_length = 70

            draw.line(
                [
                    (x, y - arrow_length),
                    (x, y)
                ],
                fill="black",
                width=4
            )

            # Arrow head
            draw.polygon(
                [
                    (x, y),
                    (x - 9, y - 16),
                    (x + 9, y - 16)
                ],
                fill="black"
            )

            draw.text(
                (x + 12, y - arrow_length),
                f"P = {obj['magnitude']}",
                fill="black"
            )

        # =================================================
        # UDL
        # =================================================

        elif obj_type == "udl":

            x1, y1 = obj["start"]
            x2, y2 = obj["end"]

            spacing = 35

            # Main load line
            draw.line(
                [
                    (x1, y1 - 60),
                    (x2, y2 - 60)
                ],
                fill="black",
                width=3
            )

            # Arrows
            length = max(
                1,
                int(abs(x2 - x1) / spacing)
            )

            for i in range(length + 1):

                t = i / max(length, 1)

                x = x1 + t * (x2 - x1)
                y = y1 + t * (y2 - y1)

                draw.line(
                    [
                        (x, y - 60),
                        (x, y)
                    ],
                    fill="black",
                    width=2
                )

                draw.polygon(
                    [
                        (x, y),
                        (x - 6, y - 10),
                        (x + 6, y - 10)
                    ],
                    fill="black"
                )

            draw.text(
                (
                    min(x1, x2),
                    min(y1, y2) - 90
                ),
                f"w = {obj['magnitude']}",
                fill="black"
            )

        # =================================================
        # MOMENT
        # =================================================

        elif obj_type == "moment":

            x, y = obj["position"]

            radius = 30

            draw.arc(
                [
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius
                ],
                start=30,
                end=320,
                fill="black",
                width=4
            )

            # Arrow head
            draw.polygon(
                [
                    (x + 25, y - 17),
                    (x + 33, y - 5),
                    (x + 18, y - 5)
                ],
                fill="black"
            )

            draw.text(
                (x + 40, y - 10),
                f"M = {obj['magnitude']}",
                fill="black"
            )

    return image


# =========================================================
# CANVAS INTERACTION
# =========================================================

st.subheader("Engineering Drawing Canvas")

st.info(
    f"Selected tool: {tool}  |  Click on the canvas to place the object."
)

# ---------------------------------------------------------
# HTML CANVAS
# ---------------------------------------------------------

canvas_placeholder = st.empty()

image = render_structure()

canvas_placeholder.image(
    image,
    width=WIDTH
)

# =========================================================
# PLACEMENT CONTROLS
# =========================================================

st.subheader("Add Object")

col1, col2, col3 = st.columns(3)

with col1:

    x = st.number_input(
        "X coordinate",
        0,
        WIDTH,
        250
    )

with col2:

    y = st.number_input(
        "Y coordinate",
        0,
        HEIGHT,
        250
    )

with col3:

    magnitude = st.number_input(
        "Load / Moment value",
        value=10.0
    )

# =========================================================
# BEAM CONTROLS
# =========================================================

if tool == "Beam":

    st.write("Beam geometry")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        x1 = st.number_input(
            "Start X",
            0,
            WIDTH,
            200,
            key="beam_x1"
        )

    with c2:
        y1 = st.number_input(
            "Start Y",
            0,
            HEIGHT,
            300,
            key="beam_y1"
        )

    with c3:
        x2 = st.number_input(
            "End X",
            0,
            WIDTH,
            800,
            key="beam_x2"
        )

    with c4:
        y2 = st.number_input(
            "End Y",
            0,
            HEIGHT,
            300,
            key="beam_y2"
        )

    if st.button("Add Beam"):

        p1 = snap_point(x1, y1)
        p2 = snap_point(x2, y2)

        st.session_state.objects.append(
            create_beam(
                p1[0],
                p1[1],
                p2[0],
                p2[1]
            )
        )

        st.rerun()

# =========================================================
# SUPPORTS
# =========================================================

elif tool == "Pin Support":

    if st.button("Add Pin Support"):

        px, py = snap_point(x, y)

        st.session_state.objects.append(
            create_pin(px, py)
        )

        st.rerun()


elif tool == "Roller Support":

    if st.button("Add Roller Support"):

        px, py = snap_point(x, y)

        st.session_state.objects.append(
            create_roller(px, py)
        )

        st.rerun()


elif tool == "Fixed Support":

    if st.button("Add Fixed Support"):

        px, py = snap_point(x, y)

        st.session_state.objects.append(
            create_fixed(px, py)
        )

        st.rerun()

# =========================================================
# POINT LOAD
# =========================================================

elif tool == "Point Load":

    if st.button("Add Point Load"):

        px, py = snap_point(x, y)

        st.session_state.objects.append(
            create_point_load(
                px,
                py,
                magnitude
            )
        )

        st.rerun()

# =========================================================
# UDL
# =========================================================

elif tool == "UDL":

    st.write("UDL geometry")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        ux1 = st.number_input(
            "Start X",
            0,
            WIDTH,
            250,
            key="udl_x1"
        )

    with c2:
        uy1 = st.number_input(
            "Start Y",
            0,
            HEIGHT,
            300,
            key="udl_y1"
        )

    with c3:
        ux2 = st.number_input(
            "End X",
            0,
            WIDTH,
            750,
            key="udl_x2"
        )

    with c4:
        uy2 = st.number_input(
            "End Y",
            0,
            HEIGHT,
            300,
            key="udl_y2"
        )

    if st.button("Add UDL"):

        p1 = snap_point(ux1, uy1)
        p2 = snap_point(ux2, uy2)

        st.session_state.objects.append(
            create_udl(
                p1[0],
                p1[1],
                p2[0],
                p2[1],
                magnitude
            )
        )

        st.rerun()

# =========================================================
# MOMENT
# =========================================================

elif tool == "Moment":

    if st.button("Add Moment"):

        px, py = snap_point(x, y)

        st.session_state.objects.append(
            create_moment(
                px,
                py,
                magnitude
            )
        )

        st.rerun()

# =========================================================
# OBJECT DATA
# =========================================================

st.divider()

st.subheader("Structural Model")

if not st.session_state.objects:

    st.write("No structural objects created yet.")

else:

    for i, obj in enumerate(
        st.session_state.objects,
        start=1
    ):

        st.json({
            "object_id": i,
            **obj
        })
