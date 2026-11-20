
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlparse


# =========================
# CONFIGURATION
# =========================

ROOT = Path(__file__).resolve().parent

INDEX = ROOT / "index.html"
PROJECTS_FILE = ROOT / "projects.json"
PERSONAL_FILE = ROOT / "personal-projects.json"

PREVIEW_DIR = ROOT / "Images" / "previews"

COURSE_PLACEHOLDER = "<!-- COURSE_LISTINGS -->"
PERSONAL_PLACEHOLDER = "<!-- PERSONAL_PROJECT_LISTINGS -->"


# =========================
# HELPERS
# =========================

def load_json(path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    except FileNotFoundError:
        raise SystemExit(f"Missing JSON file: {path}")

    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"Invalid JSON in {path}: {exc}"
        )


def safe_filename(name):
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        str(name).lower()
    ).strip("-")


def valid_url(url):
    try:
        parsed = urlparse(str(url))

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


def valid_image(image):
    """Accept local image paths and HTTP(S) image URLs."""

    if not image:
        return False

    image = str(image).strip()

    if not image:
        return False

    parsed = urlparse(image)

    if parsed.scheme:
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    # Prevent paths from escaping the project directory.
    image_path = (ROOT / image).resolve()

    try:
        image_path.relative_to(ROOT.resolve())
    except ValueError:
        return False

    return image_path.is_file()


def get_project_image(project):
    """
    Website and interactive projects:
        1. Automatically generated screenshot.
        2. Manually supplied image as fallback.

    Static projects:
        1. Manually supplied image.
    """

    project_type = str(
        project.get("type", "")
    ).lower()

    manual_image = project.get("image", "")

    if project_type in ("website", "interactive"):

        preview_name = (
            safe_filename(project.get("name", ""))
            + ".png"
        )

        preview_path = PREVIEW_DIR / preview_name

        if preview_path.is_file():
            return "./Images/previews/" + preview_name

    if valid_image(manual_image):
        return str(manual_image).strip()

    return ""


# =========================
# RENDER PROJECT CARD
# =========================

def render_project(project):

    name = escape(
        str(project.get("name", "Untitled project"))
    )

    description = escape(
        str(project.get("description", ""))
    )

    raw_url = str(project.get("url", "")).strip()

    if not valid_url(raw_url):
        raise SystemExit(
            f"Invalid project URL: {project.get('name', 'Unknown project')}"
        )

    url = escape(raw_url, quote=True)

    project_type = str(
        project.get("type", "")
    ).strip().lower()

    # -------------------------
    # PROJECT IMAGE
    # -------------------------

    image = get_project_image(project)

    image_html = ""

    if image:

        image = escape(image, quote=True)

        image_html = (
            '    <div class="project-preview">\n'
            f'      <img src="{image}" '
            f'alt="{name} preview" loading="lazy">\n'
            '    </div>\n'
        )

    # -------------------------
    # PROJECT TYPE
    # -------------------------

    type_html = ""

    if project_type:

        type_label = escape(
            project_type.capitalize()
        )

        type_html = (
            f'    <span class="project-type">'
            f'{type_label}</span>\n'
        )

    # -------------------------
    # DESCRIPTION
    # -------------------------

    description_html = ""

    if description:

        description_html = (
            f'    <p class="project-description">'
            f'{description}</p>\n'
        )

    # -------------------------
    # LANGUAGES
    # -------------------------

    languages = project.get("languages", [])

    if not isinstance(languages, list):
        languages = []

    languages = [
        str(language).strip()
        for language in languages
        if str(language).strip()
    ]

    languages_html = ""

    if languages:

        language_tags = "\n".join(
            f'      <span class="language-tag">'
            f'{escape(language)}</span>'
            for language in languages
        )

        languages_html = (
            '    <div class="project-languages">\n'
            f'{language_tags}\n'
            '    </div>\n'
        )

    # -------------------------
    # FINAL CARD
    # -------------------------

    return (
        '<li class="project-card">\n'
        f'  <a class="project-card-link" href="{url}" '
        'target="_blank" rel="noopener noreferrer">\n'
        f'{image_html}'
        f'    <h4>{name}</h4>\n'
        f'{type_html}'
        f'{description_html}'
        f'{languages_html}'
        '    <span class="project-arrow" '
        'aria-hidden="true">↗</span>\n'
        '  </a>\n'
        '</li>'
    )


# =========================
# RENDER PROJECT LIST
# =========================

def render_project_list(projects):

    if not projects:
        return ""

    items = "\n".join(
        render_project(project)
        for project in projects
    )

    return (
        '<ul class="project-list">\n'
        f'{items}\n'
        '</ul>'
    )


# =========================
# RENDER NESTED CONTENT
# =========================

def render_nested_content(section, heading_level=4):

    content = []

    # Direct projects

    projects = section.get("projects", [])

    if projects:
        content.append(
            render_project_list(projects)
        )

    # Nested subsections

    for subsection in section.get("subsections", []):

        subsection_name = escape(
            str(subsection.get("name", "Untitled section"))
        )

        subcontent = render_nested_content(
            subsection,
            min(heading_level + 1, 6)
        )

        if not subcontent:
            continue

        heading = f"h{heading_level}"

        content.append(
            '<section class="course-subsection">\n'
            f'  <{heading}>{subsection_name}</{heading}>\n'
            f'{subcontent}\n'
            '</section>'
        )

    return "\n".join(content)


# =========================
# RENDER D3.JS COURSE
# =========================

def render_course(data):

    sections_html = []

    for section in data.get("sections", []):

        content = render_nested_content(section)

        if not content:
            continue

        section_name = escape(
            str(section.get("name", "Untitled section"))
        )

        sections_html.append(
            '<section class="course-section">\n'
            f'  <h3>{section_name}</h3>\n'
            f'{content}\n'
            '</section>'
        )

    if not sections_html:

        return (
            '<p class="course-empty">'
            'Projects will appear here as they are added.'
            '</p>'
        )

    return "\n\n".join(sections_html)


# =========================
# RENDER PERSONAL PROJECTS
# =========================

def render_personal_projects(data):

    sections_html = []

    for section in data.get("sections", []):

        content = render_nested_content(section)

        if not content:
            continue

        section_name = escape(
            str(section.get("name", "Untitled section"))
        )

        sections_html.append(
            '<section class="personal-section">\n'
            f'  <h3>{section_name}</h3>\n'
            f'{content}\n'
            '</section>'
        )

    if not sections_html:

        return (
            '<p class="course-empty">'
            'Personal projects will appear here as they are added.'
            '</p>'
        )

    return "\n\n".join(sections_html)


# =========================
# GENERATE HOMEPAGE
# =========================

def main():

    if not INDEX.exists():
        raise SystemExit(
            f"Missing HTML file: {INDEX}"
        )

    html = INDEX.read_text(
        encoding="utf-8"
    )

    # -------------------------
    # VALIDATE PLACEHOLDERS
    # -------------------------

    for placeholder in (
        COURSE_PLACEHOLDER,
        PERSONAL_PLACEHOLDER
    ):

        count = html.count(placeholder)

        if count != 1:
            raise SystemExit(
                f"Expected exactly one {placeholder} "
                f"in {INDEX}, found {count}"
            )

    # -------------------------
    # LOAD JSON
    # -------------------------

    course_data = load_json(PROJECTS_FILE)
    personal_data = load_json(PERSONAL_FILE)

    # -------------------------
    # GENERATE LISTINGS
    # -------------------------

    course_html = render_course(course_data)

    personal_html = render_personal_projects(
        personal_data
    )

    # -------------------------
    # REPLACE PLACEHOLDERS
    # -------------------------

    generated = html.replace(
        COURSE_PLACEHOLDER,
        course_html
    )

    generated = generated.replace(
        PERSONAL_PLACEHOLDER,
        personal_html
    )

    # -------------------------
    # WRITE HOMEPAGE
    # -------------------------

    INDEX.write_text(
        generated,
        encoding="utf-8"
    )

    print("Homepage generated successfully.")

    print(
        "Course sections:",
        len(course_data.get("sections", []))
    )

    print(
        "Personal sections:",
        len(personal_data.get("sections", []))
    )

    print(
        "Preview directory:",
        PREVIEW_DIR
    )


if __name__ == "__main__":
    main()
