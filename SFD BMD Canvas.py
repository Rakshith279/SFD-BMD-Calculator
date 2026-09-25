import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw

from streamlit_drawable_canvas import st_canvas


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SFD & BMD Structural Sketch Interpreter",
    page_icon="🏗️",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 500


# ============================================================
# INITIALIZE SESSION STATE
# ============================================================

if "interpreted" not in st.session_state:
    st.session_state.interpreted = False

if "binary" not in st.session_state:
    st.session_state.binary = None

if "members" not in st.session_state:
    st.session_state.members = []

if "beam" not in st.session_state:
    st.session_state.beam = None


# ============================================================
# PAGE TITLE
# ============================================================

st.title("🏗️ Structural Sketch Interpreter")

st.markdown(
    """
Draw a structural system in the **Hand Sketch** canvas.

The program will read your sketch and gradually convert it into
a clean structural model.

### Current recognition stage

**Hand Sketch → Beam Detection → Structural Model**

Supports, loads, dimensions, SFD, BMD and deflection will be
added in later stages.
"""
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("✏️ Sketch Settings")

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
    "Background colour",
    "#FFFFFF"
)


# ============================================================
# FUNCTION:
# PREPARE CANVAS IMAGE
# ============================================================

def prepare_binary_image(image_data):
    """
    Convert the RGBA canvas image into a binary image.

    Dark sketch lines become white.
    Background becomes black.
    """

    if image_data is None:
        return None

    # Convert to NumPy array
    img = np.array(image_data)

    # RGBA -> grayscale
    gray = cv2.cvtColor(
        img,
        cv2.COLOR_RGBA2GRAY
    )

    # Threshold dark pixels
    _, binary = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Remove very small noise
    kernel = np.ones(
        (2, 2),
        np.uint8
    )

    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel
    )

    return binary


# ============================================================
# FUNCTION:
# DETECT HORIZONTAL LINES
# ============================================================

def detect_horizontal_members(binary):
    """
    Detect approximately horizontal lines using Hough
    line detection.

    These are potential beams/members.
    """

    members = []

    if binary is None:
        return members

    # Edge detection
    edges = cv2.Canny(
        binary,
        threshold1=50,
        threshold2=150
    )

    # Hough line detection
    lines = cv2.HoughLinesP(
        edges,

        rho=1,

        theta=np.pi / 180,

        threshold=40,

        minLineLength=80,

        maxLineGap=30
    )

    if lines is None:
        return members

    for line in lines:

        x1, y1, x2, y2 = line[0]

        dx = x2 - x1
        dy = y2 - y1

        length = np.sqrt(
            dx * dx +
            dy * dy
        )

        if length == 0:
            continue

        angle = np.degrees(
            np.arctan2(
                dy,
                dx
            )
        )

        # Convert angle to 0-90 range
        angle_abs = abs(angle)

        if angle_abs > 90:
            angle_abs = 180 - angle_abs

        # Accept approximately horizontal lines
        if angle_abs <= 12:

            members.append(
                {
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                    "length": float(length),
                    "angle": float(angle)
                }
            )

    # Longest lines first
    members.sort(
        key=lambda x: x["length"],
        reverse=True
    )

    return members


# ============================================================
# FUNCTION:
# MERGE LINE SEGMENTS
# ============================================================

def merge_member_segments(members):
    """
    HoughLinesP may detect several pieces of the same beam.

    This function combines nearby horizontal segments into
    one representative structural member.
    """

    if not members:
        return None

    # Longest detected segment
    longest = members[0]

    reference_y = (
        longest["y1"] +
        longest["y2"]
    ) / 2

    candidate_segments = []

    for member in members:

        y_mid = (
            member["y1"] +
            member["y2"]
        ) / 2

        # Keep segments close to the main beam
        if abs(y_mid - reference_y) < 40:

            candidate_segments.append(
                member
            )

    if not candidate_segments:
        candidate_segments = [
            longest
        ]

    x_values = []
    y_values = []

    for member in candidate_segments:

        x_values.extend(
            [
                member["x1"],
                member["x2"]
            ]
        )

        y_values.extend(
            [
                member["y1"],
                member["y2"]
            ]
        )

    x_min = min(x_values)
    x_max = max(x_values)

    y_mid = int(
        np.median(y_values)
    )

    return {
        "x1": int(x_min),
        "y1": int(y_mid),
        "x2": int(x_max),
        "y2": int(y_mid),
        "length": int(x_max - x_min)
    }


# ============================================================
# FUNCTION:
# CREATE CLEAN STRUCTURAL MODEL
# ============================================================

def create_structural_model(
    width,
    height,
    beam
):
    """
    Generate a clean engineering representation
    of the detected beam.
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
    # BEAM
    # --------------------------------------------------------

    draw.line(
        [
            (x1, y),
            (x2, y)
        ],
        fill="black",
        width=5
    )

    # --------------------------------------------------------
    # LEFT NODE
    # --------------------------------------------------------

    radius = 6

    draw.ellipse(
        [
            x1 - radius,
            y - radius,
            x1 + radius,
            y + radius
        ],
        fill="black"
    )

    # --------------------------------------------------------
    # RIGHT NODE
    # --------------------------------------------------------

    draw.ellipse(
        [
            x2 - radius,
            y - radius,
            x2 + radius,
            y + radius
        ],
        fill="black"
    )

    return img


# ============================================================
# FUNCTION:
# CREATE DEBUG IMAGE
# ============================================================

def create_detection_debug_image(
    binary,
    members
):
    """
    Display the line segments detected by OpenCV.
    """

    if binary is None:
        return None

    # Binary image -> RGB
    debug = cv2.cvtColor(
        binary,
        cv2.COLOR_GRAY2RGB
    )

    # Draw detected lines
    for member in members[:20]:

        cv2.line(
            debug,

            (
                member["x1"],
                member["y1"]
            ),

            (
                member["x2"],
                member["y2"]
            ),

            (0, 255, 0),

            2
        )

    return debug


# ============================================================
# HAND SKETCH SECTION
# ============================================================

st.subheader("1. Hand Sketch")

st.info(
    """
For the first test, draw a simple horizontal beam.

Example:

    ──────────────────────

Once this works, try adding supports and loads.
"""
)


# ============================================================
# DRAWING CANVAS
# ============================================================

canvas_result = st_canvas(

    fill_color="rgba(255, 255, 255, 0)",

    stroke_width=stroke_width,

    stroke_color=stroke_color,

    background_color=background_color,

    height=CANVAS_HEIGHT,

    width=CANVAS_WIDTH,

    drawing_mode="freedraw",

    display_toolbar=True,

    # Required for reading the rendered image
    return_image_data=True,

    update_streamlit=True,

    key="hand_sketch_canvas"
)


# ============================================================
# INTERPRET BUTTON
# ============================================================

st.markdown("")

interpret = st.button(
    "🔍 Interpret Sketch",
    type="primary",
    use_container_width=True
)


# ============================================================
# INTERPRET SKETCH
# ============================================================

if interpret:

    # --------------------------------------------------------
    # Check whether image data exists
    # --------------------------------------------------------

    if canvas_result is None:

        st.error(
            "Canvas data could not be read."
        )

    elif canvas_result.image_data is None:

        st.warning(
            "Please draw something in the canvas first."
        )

    else:

        # ----------------------------------------------------
        # STEP 1
        # Convert canvas into binary image
        # ----------------------------------------------------

        binary = prepare_binary_image(
            canvas_result.image_data
        )

        # ----------------------------------------------------
        # STEP 2
        # Detect horizontal lines
        # ----------------------------------------------------

        members = detect_horizontal_members(
            binary
        )

        # ----------------------------------------------------
        # STEP 3
        # Merge detected segments
        # ----------------------------------------------------

        beam = merge_member_segments(
            members
        )

        # ----------------------------------------------------
        # Store results
        # ----------------------------------------------------

        st.session_state.binary = binary

        st.session_state.members = members

        st.session_state.beam = beam

        st.session_state.interpreted = True


# ============================================================
# STRUCTURAL MODEL
# ============================================================

if st.session_state.interpreted:

    st.divider()

    st.subheader("2. Structural Model")

    beam = st.session_state.beam

    # --------------------------------------------------------
    # No beam found
    # --------------------------------------------------------

    if beam is None:

        st.error(
            """
            No horizontal structural member was detected.

            Try drawing a clearer horizontal beam and click
            **Interpret Sketch** again.
            """
        )

    # --------------------------------------------------------
    # Beam detected
    # --------------------------------------------------------

    else:

        model_image = create_structural_model(
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            beam
        )

        st.image(
            model_image,
            caption="Interpreted Structural Model",
            use_container_width=True
        )

        st.success(
            "Horizontal structural member detected."
        )

        st.write(
            f"""
            **Detected beam geometry**

            Start: ({beam['x1']}, {beam['y1']})

            End: ({beam['x2']}, {beam['y2']})

            Approximate canvas length:
            **{beam['length']} pixels**
            """
        )


# ============================================================
# DEBUG INFORMATION
# ============================================================

if st.session_state.interpreted:

    st.divider()

    with st.expander(
        "🔧 Interpretation Debug Information"
    ):

        binary = st.session_state.binary

        members = st.session_state.members

        st.write(
            f"Horizontal line candidates detected: "
            f"**{len(members)}**"
        )

        # ----------------------------------------------------
        # Show binary image
        # ----------------------------------------------------

        if binary is not None:

            st.image(
                binary,
                caption="Processed sketch",
                use_container_width=True
            )

        # ----------------------------------------------------
        # Show detected lines
        # ----------------------------------------------------

        if members:

            debug_image = (
                create_detection_debug_image(
                    binary,
                    members
                )
            )

            st.image(
                debug_image,
                caption="Detected horizontal line segments",
                use_container_width=True
            )

            st.write(
                "Detected line segments:"
            )

            for i, member in enumerate(
                members[:10]
            ):

                st.write(
                    f"""
                    **Segment {i + 1}**

                    Start:
                    ({member['x1']}, {member['y1']})

                    End:
                    ({member['x2']}, {member['y2']})

                    Length:
                    {member['length']:.1f} px

                    Angle:
                    {member['angle']:.1f}°
                    """
                )

        else:

            st.warning(
                "No horizontal line segments detected."
            )


# ============================================================
# DEVELOPMENT STATUS
# ============================================================

st.divider()

st.subheader("Development Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Beam",
        "✓" if st.session_state.beam
        else "—"
    )

with col2:
    st.metric(
        "Supports",
        "Next"
    )

with col3:
    st.metric(
        "Loads",
        "Next"
    )

with col4:
    st.metric(
        "SFD / BMD",
        "Later"
    )


st.caption(
    """
Structural interpretation pipeline:

Hand Sketch
→ Geometry Recognition
→ Support Recognition
→ Load Recognition
→ Structural Model
→ Structural Analysis
→ SFD
→ BMD
→ Deflection
"""
)
