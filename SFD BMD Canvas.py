import streamlit as st
from streamlit_drawable_canvas import st_canvas
import math
from PIL import Image, ImageDraw

# =========================================================
# PAGE
# =========================================================

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
# HAND SKETCH
# =========================================================

st.header("1. Hand Sketch")

st.write(
    "Draw the structural system freely below."
)

canvas_result = st_canvas(
    fill_color="rgba(255,255,255,0)",
    stroke_width=stroke_width,
    stroke_color="#000000",
    background_color="#FFFFFF",
    height=canvas_height,
    width=canvas_width,
    drawing_mode="freedraw",
    key="hand_sketch_canvas",
)

# =========================================================
# PATH PROCESSING
# =========================================================

def extract_points(path):

    """
    Extract points from Fabric.js freehand paths.

    Handles:
        M = move
        L = line
        Q = quadratic curve
        C = cubic curve
    """

    points = []

    for command in path:

        if not command:
            continue

        code = command[0]

        # Move
        if code == "M" and len(command) >= 3:

            points.append(
                (
                    float(command[1]),
                    float(command[2])
                )
            )

        # Line
        elif code == "L" and len(command) >= 3:

            points.append(
                (
                    float(command[1]),
                    float(command[2])
                )
            )

        # Quadratic curve
        elif code == "Q" and len(command) >= 5:

            points.append(
                (
                    float(command[3]),
                    float(command[4])
                )
            )

        # Cubic curve
        elif code == "C" and len(command) >= 7:

            points.append(
                (
                    float(command[5]),
                    float(command[6])
                )
            )

    return points


# =========================================================
# BASIC GEOMETRY
# =========================================================

def distance(p1, p2):

    return math.sqrt(
        (p2[0] - p1[0]) ** 2 +
        (p2[1] - p1[1]) ** 2
    )


def bounding_box(points):

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys)
    )


def stroke_geometry(points):

    if len(points) < 2:
        return None

    x1, y1 = points[0]
    x2, y2 = points[-1]

    length = distance(
        (x1, y1),
        (x2, y2)
    )

    if length < 20:
        return None

    dx = x2 - x1
    dy = y2 - y1

    angle = math.degrees(
        math.atan2(dy, dx)
    )

    # Convert to 0–180
    angle = angle % 180

    xmin, ymin, xmax, ymax = bounding_box(points)

    return {
        "points": points,
        "start": (x1, y1),
        "end": (x2, y2),
        "length": length,
        "angle": angle,
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "width": xmax - xmin,
        "height": ymax - ymin
    }


# =========================================================
# STRAIGHTNESS
# =========================================================

def straightness(points):

    if len(points) < 3:
        return 1.0

    p1 = points[0]
    p2 = points[-1]

    total = distance(p1, p2)

    if total == 0:
        return 0

    travelled = 0

    for i in range(len(points) - 1):

        travelled += distance(
            points[i],
            points[i + 1]
        )

    if travelled == 0:
        return 0

    return total / travelled


# =========================================================
# MEMBER DETECTION
# =========================================================

def is_member(g):

    """
    Detect long approximately straight strokes.
    """

    if g["length"] < 100:
        return False

    s = straightness(g["points"])

    if s < 0.92:
        return False

    angle = g["angle"]

    # Horizontal
    horizontal = (
        angle < 8 or
        angle > 172
    )

    # Vertical
    vertical = (
        82 < angle < 98
    )

    # For now, horizontal/vertical members
    return horizontal or vertical


# =========================================================
# POINT LOAD DETECTION
# =========================================================

def is_vertical_stroke(g):

    angle = g["angle"]

    return (
        82 < angle < 98
    )


def is_point_load_candidate(g):

    """
    Detect a vertical stroke which is shorter than
    a structural member.

    This is only the first-stage detector.
    """

    if g["length"] < 25:
        return False

    if g["length"] > 250:
        return False

    if not is_vertical_stroke(g):
        return False

    return True


# =========================================================
# SUPPORT DETECTION
# =========================================================

def classify_support_group(
    nearby_strokes,
    beam_x,
    beam_y
):

    """
    Heuristic support recognition.

    This is intentionally conservative.
    """

    if len(nearby_strokes) < 2:
        return None

    vertical_count = 0
    diagonal_count = 0
    horizontal_count = 0

    for g in nearby_strokes:

        angle = g["angle"]

        if 82 < angle < 98:
            vertical_count += 1

        elif (
            15 < angle < 75 or
            105 < angle < 165
        ):
            diagonal_count += 1

        else:
            horizontal_count += 1

    # Fixed support:
    # vertical wall + hatch-like diagonals
    if (
        vertical_count >= 1 and
        diagonal_count >= 2
    ):
        return "Fixed Support"

    # Pin / roller:
    # diagonal strokes around beam end
    if diagonal_count >= 2:

        # If circular-looking short strokes exist,
        # classify as roller.
        circular_candidates = 0

        for g in nearby_strokes:

            if (
                g["width"] > 5 and
                g["height"] > 5 and
                g["width"] < 60 and
                g["height"] < 60
            ):
                circular_candidates += 1

        if circular_candidates >= 1:
            return "Roller Support"

        return "Pin Support"

    return None


# =========================================================
# INTERPRET SKETCH
# =========================================================

def interpret_sketch():

    if canvas_result.json_data is None:

        return {
            "members": [],
            "loads": [],
            "supports": [],
            "strokes": []
        }

    objects = canvas_result.json_data.get(
        "objects",
        []
    )

    strokes = []

    for index, obj in enumerate(objects):

        if obj.get("type") != "path":
            continue

        path = obj.get("path", [])

        points = extract_points(path)

        geometry = stroke_geometry(points)

        if geometry is None:
            continue

        geometry["stroke_id"] = index

        strokes.append(
            geometry
        )

    members = []
    load_candidates = []

    # -----------------------------------------------------
    # MEMBER / LOAD CANDIDATES
    # -----------------------------------------------------

    for g in strokes:

        if is_member(g):

            members.append(g)

        elif is_point_load_candidate(g):

            load_candidates.append(g)

    # -----------------------------------------------------
    # SUPPORT DETECTION
    # -----------------------------------------------------

    supports = []

    # Look around ends of detected members

    for member in members:

        endpoints = [
            member["start"],
            member["end"]
        ]

        for endpoint in endpoints:

            ex, ey = endpoint

            nearby = []

            for stroke in strokes:

                if stroke is member:
                    continue

                sx, sy = stroke["start"]
                tx, ty = stroke["end"]

                d1 = distance(
                    (ex, ey),
                    (sx, sy)
                )

                d2 = distance(
                    (ex, ey),
                    (tx, ty)
                )

                if min(d1, d2) < 80:

                    nearby.append(stroke)

            support_type = classify_support_group(
                nearby,
                ex,
                ey
            )

            if support_type:

                supports.append(
                    {
                        "type": support_type,
                        "position": [ex, ey]
                    }
                )

    return {
        "members": members,
        "loads": load_candidates,
        "supports": supports,
        "strokes": strokes
    }


# =========================================================
# CLEAN STRUCTURAL MODEL
# =========================================================

def draw_pin(
    draw,
    x,
    y
):

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

    draw.line(
        [
            (x - size - 10, y + size),
            (x + size + 10, y + size)
        ],
        fill="black",
        width=3
    )


def draw_roller(
    draw,
    x,
    y
):

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

    r = 7

    draw.ellipse(
        [
            x - 16,
            y + size,
            x - 2,
            y + size + 14
        ],
        outline="black",
        width=2
    )

    draw.ellipse(
        [
            x + 2,
            y + size,
            x + 16,
            y + size + 14
        ],
        outline="black",
        width=2
    )


def draw_fixed(
    draw,
    x,
    y
):

    wall_height = 55

    draw.line(
        [
            (x, y - wall_height),
            (x, y + wall_height)
        ],
        fill="black",
        width=5
    )

    for yy in range(
        int(y - wall_height),
        int(y + wall_height),
        10
    ):

        draw.line(
            [
                (x, yy),
                (x - 15, yy + 10)
            ],
            fill="black",
            width=2
        )


def draw_point_load(
    draw,
    x,
    y
):

    length = 70

    draw.line(
        [
            (x, y - length),
            (x, y)
        ],
        fill="black",
        width=4
    )

    draw.polygon(
        [
            (x, y),
            (x - 9, y - 16),
            (x + 9, y - 16)
        ],
        fill="black"
    )


def render_model(model):

    image = Image.new(
        "RGB",
        (
            int(canvas_width),
            int(canvas_height)
        ),
        "white"
    )

    draw = ImageDraw.Draw(image)

    # -----------------------------------------------------
    # BEAMS
    # -----------------------------------------------------

    for member in model["members"]:

        x1, y1 = member["start"]
        x2, y2 = member["end"]

        draw.line(
            [
                (x1, y1),
                (x2, y2)
            ],
            fill="black",
            width=5
        )

    # -----------------------------------------------------
    # SUPPORTS
    # -----------------------------------------------------

    for support in model["supports"]:

        x, y = support["position"]

        if support["type"] == "Pin Support":

            draw_pin(
                draw,
                x,
                y
            )

        elif support["type"] == "Roller Support":

            draw_roller(
                draw,
                x,
                y
            )

        elif support["type"] == "Fixed Support":

            draw_fixed(
                draw,
                x,
                y
            )

    # -----------------------------------------------------
    # POINT LOADS
    # -----------------------------------------------------

    for load in model["loads"]:

        x, y = load["start"]

        draw_point_load(
            draw,
            x,
            y
        )

    return image


# =========================================================
# INTERPRET BUTTON
# =========================================================

st.divider()

interpret_button = st.button(
    "Interpret Sketch",
    type="primary"
)

# =========================================================
# STRUCTURAL MODEL
# =========================================================

st.header("2. Structural Model")

if interpret_button:

    model = interpret_sketch()

    # -----------------------------------------------------
    # CLEAN MODEL CANVAS
    # -----------------------------------------------------

    structural_image = render_model(
        model
    )

    st.image(
        structural_image,
        width=int(canvas_width)
    )

    # -----------------------------------------------------
    # INTERPRETATION
    # -----------------------------------------------------

    st.subheader(
        "3. Interpretation"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Members",
            len(model["members"])
        )

    with col2:

        st.metric(
            "Point-load candidates",
            len(model["loads"])
        )

    with col3:

        st.metric(
            "Supports",
            len(model["supports"])
        )

    # -----------------------------------------------------
    # DETAILS
    # -----------------------------------------------------

    st.write("### Detected Members")

    if model["members"]:

        for i, member in enumerate(
            model["members"],
            start=1
        ):

            st.write(
                f"**Member {i}** — "
                f"({member['start'][0]:.0f}, "
                f"{member['start'][1]:.0f}) → "
                f"({member['end'][0]:.0f}, "
                f"{member['end'][1]:.0f})"
            )

    else:

        st.write(
            "No members detected."
        )

    st.write("### Detected Supports")

    if model["supports"]:

        for support in model["supports"]:

            st.write(
                f"{support['type']} at "
                f"{support['position']}"
            )

    else:

        st.write(
            "No supports detected yet."
        )

    st.write("### Point-load Candidates")

    if model["loads"]:

        for load in model["loads"]:

            st.write(
                f"Vertical load candidate at "
                f"({load['start'][0]:.0f}, "
                f"{load['start'][1]:.0f})"
            )

    else:

        st.write(
            "No point-load candidates detected."
        )

else:

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
        "Draw a structural sketch above and click "
        "'Interpret Sketch'."
    )
