import streamlit as st
import numpy as np
import cv2
from PIL import Image, ImageDraw
from streamlit_drawable_canvas import st_canvas


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Structural Sketch Interpreter",
    page_icon="🏗️",
    layout="wide"
)


# ============================================================
# CONSTANTS
# ============================================================

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 500


# ============================================================
# SESSION STATE
# ============================================================

if "interpreted" not in st.session_state:
    st.session_state.interpreted = False

if "binary" not in st.session_state:
    st.session_state.binary = None

if "members" not in st.session_state:
    st.session_state.members = []

if "beam" not in st.session_state:
    st.session_state.beam = None

if "debug_image" not in st.session_state:
    st.session_state.debug_image = None


# ============================================================
# TITLE
# ============================================================

st.title("🏗️ Structural Sketch Interpreter")

st.markdown(
    """
Draw a structural system by hand in the canvas below.

The current prototype will:

1. Capture your hand sketch
2. Detect horizontal structural members
3. Create a clean structural model
4. Display the detected geometry separately

**Current milestone:** Beam/member recognition.

Supports, loads, dimensions, SFD, BMD and deflection interpretation will be added progressively.
"""
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("✏️ Drawing Settings")

stroke_width = st.sidebar.slider(
    "Pen Thickness",
    min_value=1,
    max_value=10,
    value=3
)

stroke_color = st.sidebar.color_picker(
    "Stroke Color",
    "#000000"
)

background_color = st.sidebar.color_picker(
    "Background Color",
    "#FFFFFF"
)


# ============================================================
# IMAGE PREPARATION
# ============================================================

def prepare_binary_image(image_data):
    """
    Convert canvas RGBA image into a clean binary image.

    Black/dark drawing → white foreground
    White background → black background
    """

    if image_data is None:
        return None

    try:
        img = np.array(image_data)

        # ----------------------------------------------------
        # Convert RGBA/RGB to grayscale
        # ----------------------------------------------------

        if len(img.shape) == 3:

            if img.shape[2] == 4:
                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_RGBA2GRAY
                )

            elif img.shape[2] == 3:
                gray = cv2.cvtColor(
                    img,
                    cv2.COLOR_RGB2GRAY
                )

            else:
                gray = img[:, :, 0]

        else:
            gray = img

        # ----------------------------------------------------
        # Threshold
        # ----------------------------------------------------

        _, binary = cv2.threshold(
            gray,
            200,
            255,
            cv2.THRESH_BINARY_INV
        )

        # ----------------------------------------------------
        # Remove tiny noise
        # ----------------------------------------------------

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

    except Exception as e:

        st.error(
            f"Could not process the sketch image: {e}"
        )

        return None


# ============================================================
# HORIZONTAL MEMBER DETECTION
# ============================================================

def detect_horizontal_members(binary):

    """
    Detect approximately horizontal lines using Hough transform.

    This is intentionally simple at this stage.

    Future versions will recognize:
    - beams
    - columns
    - braces
    - supports
    - loads
    - dimensions
    """

    if binary is None:
        return []

    # --------------------------------------------------------
    # Edge detection
    # --------------------------------------------------------

    edges = cv2.Canny(
        binary,
        50,
        150,
        apertureSize=3
    )

    # --------------------------------------------------------
    # Hough line detection
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Filter horizontal lines
    # --------------------------------------------------------

    for line in lines:

        x1, y1, x2, y2 = line[0]

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0:
            continue

        angle = np.degrees(
            np.arctan2(dy, dx)
        )

        # Normalize angle
        angle = abs(angle)

        if angle > 90:
            angle = 180 - angle

        # Approximately horizontal
        if angle <= 12:

            length = np.sqrt(
                dx ** 2 + dy ** 2
            )

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

    return members


# ============================================================
# MERGE HORIZONTAL MEMBER SEGMENTS
# ============================================================

def merge_member_segments(members):

    """
    Merge multiple Hough segments that belong to the same beam.

    At this stage we primarily look for the longest horizontal
    structural member.
    """

    if not members:
        return None

    # --------------------------------------------------------
    # Select longest detected segment
    # --------------------------------------------------------

    longest = max(
        members,
        key=lambda m: m["length"]
    )

    y_reference = (
        longest["y1"] +
        longest["y2"]
    ) / 2

    tolerance = 40

    related_segments = []

    for member in members:

        y_mid = (
            member["y1"] +
            member["y2"]
        ) / 2

        if abs(y_mid - y_reference) <= tolerance:

            related_segments.append(member)

    # --------------------------------------------------------
    # Find overall horizontal extent
    # --------------------------------------------------------

    x_values = []

    for member in related_segments:

        x_values.append(member["x1"])
        x_values.append(member["x2"])

    if not x_values:
        return longest

    x_min = min(x_values)
    x_max = max(x_values)

    # --------------------------------------------------------
    # Average Y coordinate
    # --------------------------------------------------------

    y_values = []

    for member in related_segments:

        y_values.append(member["y1"])
        y_values.append(member["y2"])

    y_average = int(
        sum(y_values) / len(y_values)
    )

    return {
        "x1": int(x_min),
        "y1": y_average,
        "x2": int(x_max),
        "y2": y_average,
        "length": float(x_max - x_min)
    }


# ============================================================
# CREATE CLEAN STRUCTURAL MODEL
# ============================================================

def create_structural_model(
    width,
    height,
    beam
):

    """
    Create a clean structural model from detected geometry.

    This is deliberately separate from the original hand sketch.
    """

    image = Image.new(
        "RGB",
        (width, height),
        "white"
    )

    draw = ImageDraw.Draw(image)

    if beam is None:
        return image

    x1 = beam["x1"]
    y1 = beam["y1"]

    x2 = beam["x2"]
    y2 = beam["y2"]

    # --------------------------------------------------------
    # Beam
    # --------------------------------------------------------

    draw.line(
        [(x1, y1), (x2, y2)],
        fill="black",
        width=6
    )

    # --------------------------------------------------------
    # End nodes
    # --------------------------------------------------------

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

    return image


# ============================================================
# CREATE DEBUG IMAGE
# ============================================================

def create_detection_debug_image(
    binary,
    members
):

    """
    Display what the computer vision algorithm detected.
    """

    if binary is None:
        return None

    # Convert binary to RGB
    debug = cv2.cvtColor(
        binary,
        cv2.COLOR_GRAY2RGB
    )

    # --------------------------------------------------------
    # Draw detected segments in green
    # --------------------------------------------------------

    for member in members:

        x1 = member["x1"]
        y1 = member["y1"]

        x2 = member["x2"]
        y2 = member["y2"]

        cv2.line(
            debug,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

    return debug


# ============================================================
# FALLBACK: CREATE IMAGE FROM CANVAS JSON
# ============================================================

def create_image_from_canvas_json(
    json_data,
    width,
    height,
    background="#FFFFFF"
):

    """
    Fallback method for installations where image_data is not
    available from streamlit-drawable-canvas.

    It converts simple freehand Fabric.js paths into a PIL image.
    """

    if not json_data:
        return None

    try:

        image = Image.new(
            "RGB",
            (width, height),
            background
        )

        draw = ImageDraw.Draw(image)

        objects = json_data.get(
            "objects",
            []
        )

        for obj in objects:

            obj_type = obj.get(
                "type",
                ""
            )

            # ------------------------------------------------
            # Handle freehand paths
            # ------------------------------------------------

            if obj_type == "path":

                path_data = obj.get(
                    "path",
                    []
                )

                points = []

                current_x = 0
                current_y = 0

                for command in path_data:

                    if not command:
                        continue

                    command_type = command[0]

                    # Move
                    if command_type == "M":

                        if len(command) >= 3:

                            current_x = float(
                                command[1]
                            )

                            current_y = float(
                                command[2]
                            )

                            points.append(
                                (
                                    current_x,
                                    current_y
                                )
                            )

                    # Line
                    elif command_type == "L":

                        if len(command) >= 3:

                            current_x = float(
                                command[1]
                            )

                            current_y = float(
                                command[2]
                            )

                            points.append(
                                (
                                    current_x,
                                    current_y
                                )
                            )

                    # Cubic / quadratic curves
                    elif command_type in ["C", "Q"]:

                        if len(command) >= 3:

                            # For fallback purposes use the
                            # final coordinate in the command.
                            try:

                                current_x = float(
                                    command[-2]
                                )

                                current_y = float(
                                    command[-1]
                                )

                                points.append(
                                    (
                                        current_x,
                                        current_y
                                    )
                                )

                            except Exception:
                                pass

                # ------------------------------------------------
                # Apply Fabric object positioning
                # ------------------------------------------------

                left = float(
                    obj.get("left", 0)
                )

                top = float(
                    obj.get("top", 0)
                )

                scale_x = float(
                    obj.get("scaleX", 1)
                )

                scale_y = float(
                    obj.get("scaleY", 1)
                )

                if len(points) >= 2:

                    transformed = []

                    for px, py in points:

                        tx = (
                            left +
                            px * scale_x
                        )

                        ty = (
                            top +
                            py * scale_y
                        )

                        transformed.append(
                            (tx, ty)
                        )

                    draw.line(
                        transformed,
                        fill="black",
                        width=3
                    )

        return np.array(image)

    except Exception:

        return None


# ============================================================
# HAND SKETCH
# ============================================================

st.header("✏️ Hand Sketch")

st.info(
    "Draw the structural system freely. "
    "For the current version, start with a horizontal beam."
)


# ============================================================
# ORIGINAL HAND SKETCH CANVAS
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
    key="hand_sketch_canvas"
)


# ============================================================
# INTERPRET BUTTON
# ============================================================

st.write("")

interpret_button = st.button(
    "🔍 Interpret Sketch",
    type="primary"
)


# ============================================================
# INTERPRETATION PIPELINE
# ============================================================

if interpret_button:

    # --------------------------------------------------------
    # Try to obtain rendered canvas image
    # --------------------------------------------------------

    image_data = getattr(
        canvas_result,
        "image_data",
        None
    )

    # --------------------------------------------------------
    # If image_data is unavailable, try JSON fallback
    # --------------------------------------------------------

    if image_data is None:

        json_data = getattr(
            canvas_result,
            "json_data",
            None
        )

        if json_data is not None:

            image_data = create_image_from_canvas_json(
                json_data,
                CANVAS_WIDTH,
                CANVAS_HEIGHT,
                background_color
            )

    # --------------------------------------------------------
    # Validate image
    # --------------------------------------------------------

    if image_data is None:

        st.error(
            "Could not read the sketch from the canvas."
        )

        st.info(
            "Please draw something and try again."
        )

        st.session_state.interpreted = False

    else:

        # ----------------------------------------------------
        # Convert sketch to binary image
        # ----------------------------------------------------

        binary = prepare_binary_image(
            image_data
        )

        if binary is None:

            st.session_state.interpreted = False

        else:

            # ------------------------------------------------
            # Detect horizontal members
            # ------------------------------------------------

            members = detect_horizontal_members(
                binary
            )

            # ------------------------------------------------
            # Merge segments
            # ------------------------------------------------

            beam = merge_member_segments(
                members
            )

            # ------------------------------------------------
            # Debug image
            # ------------------------------------------------

            debug_image = create_detection_debug_image(
                binary,
                members
            )

            # ------------------------------------------------
            # Store results
            # ------------------------------------------------

            st.session_state.binary = binary

            st.session_state.members = members

            st.session_state.beam = beam

            st.session_state.debug_image = debug_image

            st.session_state.interpreted = True


# ============================================================
# STRUCTURAL MODEL
# ============================================================

if st.session_state.interpreted:

    st.divider()

    st.header("🏗️ Structural Model")

    beam = st.session_state.beam

    if beam is not None:

        # ----------------------------------------------------
        # Create clean structural model
        # ----------------------------------------------------

        structural_model = create_structural_model(
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            beam
        )

        st.image(
            structural_model,
            caption="Clean Structural Model",
            use_container_width=False
        )

        # ----------------------------------------------------
        # Beam information
        # ----------------------------------------------------

        st.subheader("Detected Geometry")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Member Length",
                f"{beam['length']:.0f} px"
            )

        with col2:

            st.metric(
                "Start X",
                f"{beam['x1']} px"
            )

        with col3:

            st.metric(
                "End X",
                f"{beam['x2']} px"
            )

        st.success(
            "Beam detected successfully."
        )

    else:

        st.error(
            "No horizontal structural member was detected."
        )

        st.info(
            """
            Try drawing a clearer horizontal beam.

            Example:

            ●━━━━━━━━━━━━━━━━━━━━●
            """
        )


# ============================================================
# DEBUG INFORMATION
# ============================================================

if st.session_state.interpreted:

    st.divider()

    with st.expander(
        "🔧 Detection Debug Information"
    ):

        # ----------------------------------------------------
        # Binary image
        # ----------------------------------------------------

        if st.session_state.binary is not None:

            st.subheader(
                "Processed Binary Image"
            )

            st.image(
                st.session_state.binary,
                caption="Binary image used for detection",
                use_container_width=False
            )

        # ----------------------------------------------------
        # Detected segments
        # ----------------------------------------------------

        if st.session_state.debug_image is not None:

            st.subheader(
                "Detected Line Segments"
            )

            st.image(
                st.session_state.debug_image,
                caption="Green lines = detected horizontal segments",
                use_container_width=False
            )

        # ----------------------------------------------------
        # Raw detection information
        # ----------------------------------------------------

        st.subheader(
            "Detected Segments"
        )

        if st.session_state.members:

            for i, member in enumerate(
                st.session_state.members
            ):

                st.write(
                    f"""
                    **Segment {i + 1}**

                    Start: ({member['x1']}, {member['y1']})

                    End: ({member['x2']}, {member['y2']})

                    Length: {member['length']:.1f} px

                    Angle: {member.get('angle', 0):.1f}°
                    """
                )

        else:

            st.write(
                "No line segments detected."
            )


# ============================================================
# CURRENT DEVELOPMENT STATUS
# ============================================================

st.divider()

st.subheader("🚧 Development Status")

status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:

    if st.session_state.beam is not None:
        st.success("✓ Beam")
    else:
        st.warning("○ Beam")

with status_col2:

    st.info("○ Supports")

with status_col3:

    st.info("○ Loads")

with status_col4:

    st.info("○ SFD / BMD")


# ============================================================
# PIPELINE
# ============================================================

st.caption(
    """
Current pipeline:

Hand Sketch
→ Image Processing
→ Line Recognition
→ Structural Member
→ Structural Model

Next:

→ Support Recognition
→ Load Recognition
→ Dimension Recognition
→ Structural JSON
→ Structural Analysis
→ AFD / SFD / BMD
→ Qualitative Deflection
"""
)
