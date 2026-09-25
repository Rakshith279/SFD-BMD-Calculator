import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw

from streamlit_drawable_canvas import st_canvas


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Structural Sketch Interpreter",
    page_icon="🏗️",
    layout="wide"
)


# ============================================================
# SETTINGS
# ============================================================

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 500


# ============================================================
# IMAGE PROCESSING
# ============================================================

def prepare_binary_image(image_data):
    """
    Convert canvas RGBA image into a clean binary image.

    Black/dark sketch lines -> white
    Background -> black
    """

    if image_data is None:
        return None

    img = np.array(image_data)

    # RGBA -> grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)

    # Threshold dark pixels
    _, binary = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Remove tiny noise
    kernel = np.ones((2, 2), np.uint8)

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel
    )

    return binary


# ============================================================
# LINE DETECTION
# ============================================================

def detect_horizontal_members(binary):
    """
    Detect approximately horizontal structural members.

    Returns:
        list of dictionaries containing:
        x1, y1, x2, y2, length, angle
    """

    edges = cv2.Canny(
        binary,
        threshold1=50,
        threshold2=150
    )

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=80,
        maxLineGap=30
    )

    members = []

    if lines is None:
        return members

    for line in lines:

        x1, y1, x2, y2 = line[0]

        dx = x2 - x1
        dy = y2 - y1

        length = np.sqrt(dx * dx + dy * dy)

        if length == 0:
            continue

        angle = np.degrees(np.arctan2(dy, dx))

        # Normalize angle
        angle_abs = abs(angle)

        if angle_abs > 90:
            angle_abs = 180 - angle_abs

        # Accept lines within +/- 12 degrees of horizontal
        if angle_abs <= 12:

            members.append({
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "length": length,
                "angle": angle
            })

    # Longest first
    members.sort(
        key=lambda x: x["length"],
        reverse=True
    )

    return members


# ============================================================
# MERGE HORIZONTAL LINE SEGMENTS
# ============================================================

def merge_member_segments(members):
    """
    Hough detection can produce multiple segments for one beam.

    This function converts them into one representative beam.
    """

    if not members:
        return None

    # Take reasonably long segments
    longest = members[0]

    reference_y = (
        longest["y1"] +
        longest["y2"]
    ) / 2

    candidate_segments = []

    for m in members:

        y_mid = (
            m["y1"] +
            m["y2"]
        ) / 2

        # Keep lines close to the main beam
        if abs(y_mid - reference_y) < 40:

            candidate_segments.append(m)

    if not candidate_segments:
        candidate_segments = [longest]

    x_values = []

    y_values = []

    for m in candidate_segments:

        x_values.extend([
            m["x1"],
            m["x2"]
        ])

        y_values.extend([
            m["y1"],
            m["y2"]
        ])

    x_min = min(x_values)
    x_max = max(x_values)

    y_mid = int(np.median(y_values))

    return {
        "x1": x_min,
        "y1": y_mid,
        "x2": x_max,
        "y2": y_mid,
        "length": x_max - x_min
    }


# ============================================================
# STRUCTURAL MODEL CREATION
# ============================================================

def create_structural_model(
    width,
    height,
    beam
):
    """
    Create a clean structural diagram.

    Currently:
        - beam
        - end nodes

    Supports/load recognition will be added next.
    """

    img = Image.new(
        "RGB",
        (width, height),
        "white"
    )

    draw = ImageDraw.Draw(img)

    if beam is None:
        return img

    x1 = beam["x1"]
    x2 = beam["x2"]
    y = beam["y1"]

    # --------------------------------------------------------
    # Beam
    # --------------------------------------------------------

    draw.line(
        [(x1, y), (x2, y)],
        fill="black",
        width=5
    )

    # --------------------------------------------------------
    # Left node
    # --------------------------------------------------------

    r = 6

    draw.ellipse(
        [
            x1 - r,
            y - r,
            x1 + r,
            y + r
        ],
        fill="black"
    )

    # --------------------------------------------------------
    # Right node
    # --------------------------------------------------------

    draw.ellipse(
        [
            x2 - r,
            y - r,
            x2 + r,
            y + r
        ],
        fill="black"
    )

    return img


# ============================================================
# DEBUG IMAGE
# ============================================================

def create_detection_debug_image(
    binary,
    members
):
    """
    Display what the computer vision system detected.
    """

    if binary is None:
        return None

    # Convert binary to RGB
    debug = cv2.cvtColor(
        binary,
        cv2.COLOR_GRAY2RGB
    )

    # Draw detected lines
    for i, m in enumerate(members[:20]):

        cv2.line(
            debug,
            (m["x1"], m["y1"]),
            (m["x2"], m["y2"]),
            (0, 255, 0),
            2
        )

    return debug


# ============================================================
# HEADER
# ============================================================

st.title("🏗️ Structural Sketch Interpreter")

st.write(
    """
Draw a structural sketch in the canvas below.

The program will first interpret the **geometry** of your sketch
and generate a clean structural model.
"""
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Sketch Settings")

stroke_width = st.sidebar.slider(
    "Pen thickness",
    min_value=1,
    max_value=15,
    value=4
)

stroke_color = st.sidebar.color_picker(
    "Pen colour",
    "#000000"
)

background_color = st.sidebar.color_picker(
    "Canvas background",
    "#FFFFFF"
)


# ============================================================
# HAND SKETCH
# ============================================================

st.subheader("1. Hand Sketch")

st.caption(
    "Draw the structural system here. "
    "For the first test, draw only a beam."
)

canvas_result = st_canvas(

    fill_color="rgba(255, 255, 255, 0)",

    stroke_width=stroke_width,

    stroke_color=stroke_color,

    background_color=background_color,

    height=CANVAS_HEIGHT,

    width=CANVAS_WIDTH,

    drawing_mode="freedraw",

    display_toolbar=True,

    update_streamlit=True,

    key="hand_sketch_canvas"
)


# ============================================================
# INTERPRET BUTTON
# ============================================================

interpret = st.button(
    "🔍 Interpret Sketch",
    type="primary",
    use_container_width=True
)


# ============================================================
# INTERPRETATION
# ============================================================

if interpret:

    if canvas_result.image_data is None:

        st.warning(
            "Please draw something in the sketch canvas first."
        )

    else:

        # ----------------------------------------------------
        # STEP 1 — Convert sketch into binary image
        # ----------------------------------------------------

        binary = prepare_binary_image(
            canvas_result.image_data
        )

        # ----------------------------------------------------
        # STEP 2 — Detect horizontal lines
        # ----------------------------------------------------

        members = detect_horizontal_members(
            binary
        )

        # ----------------------------------------------------
        # STEP 3 — Merge line segments
        # ----------------------------------------------------

        beam = merge_member_segments(
            members
        )

        # Save results in session state
        st.session_state["binary"] = binary
        st.session_state["members"] = members
        st.session_state["beam"] = beam

        st.session_state["interpreted"] = True


# ============================================================
# STRUCTURAL MODEL
# ============================================================

if st.session_state.get("interpreted", False):

    st.divider()

    st.subheader("2. Structural Model")

    beam = st.session_state.get("beam")

    if beam is None:

        st.error(
            """
            I could not identify a horizontal structural member.

            Try drawing a clear beam approximately horizontally,
            then click **Interpret Sketch** again.
            """
        )

    else:

        model_image = create_structural_model(
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            beam
        )

        st.image(
            model_image,
            caption="Interpreted structural model",
            use_container_width=True
        )

        st.success(
            f"Beam detected — approximately "
            f"{int(beam['length'])} canvas pixels long."
        )


# ============================================================
# DEBUG / COMPUTER VISION INFORMATION
# ============================================================

if st.session_state.get("interpreted", False):

    with st.expander(
        "🔧 Interpretation Debug Information"
    ):

        binary = st.session_state.get(
            "binary"
        )

        members = st.session_state.get(
            "members",
            []
        )

        st.write(
            f"Horizontal line candidates detected: "
            f"**{len(members)}**"
        )

        if members:

            debug_image = create_detection_debug_image(
                binary,
                members
            )

            st.image(
                debug_image,
                caption="Detected horizontal line segments",
                use_container_width=True
            )

            st.write("Detected segments:")

            for i, m in enumerate(members[:10]):

                st.write(
                    f"""
                    **Segment {i + 1}:**
                    ({m['x1']}, {m['y1']})
                    → ({m['x2']}, {m['y2']})
                    | Length = {m['length']:.1f}px
                    """
                )

        else:

            st.warning(
                "No horizontal line segments were detected."
            )


# ============================================================
# CURRENT DEVELOPMENT STATUS
# ============================================================

st.divider()

st.caption(
    """
Current recognition stage:
    Beam geometry ✓

Next:
    Supports → Point loads → Distributed loads →
    Dimensions/OCR → Structural relationships →
    AFD/SFD/BMD → Deflection
"""
)
