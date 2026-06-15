"""
Scans UC-*/ folders, parses INSTRUCTIONS.txt, and writes training-hub/data.json.
Preserves existing youtube_id and screenshot values already in data.json.
"""

import json
import os
import re

REPO = "dkbholusaria/pq-usecases"
TOPIC = "Power Query"
BRANCH = "main"
OUTPUT = "training-hub/data.json"

RAW_BASE = f"https://github.com/{REPO}/raw/{BRANCH}"
ZIP_BASE = "https://download-directory.github.io/?url=https://github.com/{repo}/tree/{branch}/{folder}"

IGNORED_FILES = {"INSTRUCTIONS.txt", ".gitkeep"}
IGNORED_EXTENSIONS = {".py", ".yml", ".json", ".md", ".identifier"}
IGNORED_DIRS = {"screenshots", ".github"}


def folder_to_id(folder_name):
    """UC-01-Bank-Recon → uc-01"""
    parts = folder_name.split("-")
    return f"{parts[0]}-{parts[1]}".lower()


def folder_to_title(folder_name):
    """UC-01-Bank-Recon → Bank Recon"""
    parts = folder_name.split("-", 2)
    if len(parts) < 3:
        return folder_name
    return parts[2].replace("-", " ")


def parse_instructions(path):
    """Parse INSTRUCTIONS.txt → objective, description, parts list, key_learning list."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Objective block — text between OBJECTIVE and the next ─── line or section
    obj_match = re.search(
        r"OBJECTIVE\s*[-─]+\s*(.*?)(?=\n[-─]{3,}|\nFILES|\nSTEP|\nPART|\nKEY LEARNING|\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    objective = ""
    if obj_match:
        objective = " ".join(obj_match.group(1).split()).strip()

    # One-line description = first sentence of objective
    description = objective.split(".")[0].strip() if objective else ""

    # PART headings — "PART A — Load the Bank Statement" style
    parts = []
    for m in re.finditer(r"^(PART [A-Z\d]+ ?[—\-–].+)$", text, re.MULTILINE):
        title = m.group(1).strip()
        # Normalise dash variants to em-dash
        title = re.sub(r"\s*[—\-–]+\s*", " — ", title, count=1)
        parts.append({"title": title, "screenshot": ""})

    # KEY LEARNING bullets
    key_match = re.search(
        r"KEY LEARNING\s*[-─]*\s*(.*?)(?=\Z)",
        text, re.DOTALL | re.IGNORECASE
    )
    key_learning = []
    if key_match:
        for line in key_match.group(1).splitlines():
            line = line.strip().lstrip("✔✓•*-").strip()
            if line:
                key_learning.append(line)

    return objective, description, parts, key_learning


def list_files(folder_path, folder_name):
    """List downloadable files in the UC folder (non-hidden, non-ignored)."""
    files = []
    for f in sorted(os.listdir(folder_path)):
        if f.startswith("."):
            continue
        if f in IGNORED_FILES:
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in IGNORED_EXTENSIONS:
            continue
        full = os.path.join(folder_path, f)
        if os.path.isdir(full) and f in IGNORED_DIRS:
            continue
        if os.path.isfile(full):
            files.append(f)
    # Always append INSTRUCTIONS.txt last
    instr = os.path.join(folder_path, "INSTRUCTIONS.txt")
    if os.path.exists(instr):
        files.append("INSTRUCTIONS.txt")
    return files


def build_uc_entry(folder_name, folder_path, existing):
    """Build a single UC entry, preserving existing youtube_id and screenshot values."""
    uc_id = folder_to_id(folder_name)
    title = folder_to_title(folder_name)

    instr_path = os.path.join(folder_path, "INSTRUCTIONS.txt")
    if os.path.exists(instr_path):
        objective, description, parts, key_learning = parse_instructions(instr_path)
    else:
        objective, description, parts, key_learning = "", "", [], []

    files = list_files(folder_path, folder_name)

    # Preserve existing youtube_id
    youtube_id = existing.get("youtube_id", "")

    # Preserve existing screenshot values per part title
    existing_parts_map = {p["title"]: p.get("screenshot", "") for p in existing.get("parts", [])}
    for part in parts:
        part["screenshot"] = existing_parts_map.get(part["title"], "")

    return {
        "id": uc_id,
        "folder": folder_name,
        "title": title,
        "description": description,
        "objective": objective,
        "youtube_id": youtube_id,
        "files": files,
        "parts": parts,
        "key_learning": key_learning,
    }


def main():
    # Load existing data.json to preserve manual fields
    existing_map = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as f:
            existing_data = json.load(f)
        for uc in existing_data.get("usecases", []):
            existing_map[uc["id"]] = uc

    # Scan UC-*/ folders
    uc_folders = sorted(
        d for d in os.listdir(".")
        if re.match(r"UC-\d+", d, re.IGNORECASE) and os.path.isdir(d)
    )

    usecases = []
    for folder_name in uc_folders:
        uc_id = folder_to_id(folder_name)
        entry = build_uc_entry(folder_name, folder_name, existing_map.get(uc_id, {}))
        usecases.append(entry)

    data = {
        "topic": TOPIC,
        "github_repo": REPO,
        "branch": BRANCH,
        "raw_base": RAW_BASE,
        "usecases": usecases,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Written {len(usecases)} use cases to {OUTPUT}")


if __name__ == "__main__":
    main()
