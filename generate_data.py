"""
Scans UC-*/ folders, parses INSTRUCTIONS.txt, and writes data.json in the same repo.
Preserves existing youtube_id and screenshot values already in data.json.
"""

import json
import os
import re

REPO = "dkbholusaria/pq-usecases"
TOPIC = "Power Query"
BRANCH = "main"
OUTPUT = "data.json"
UC_DIR = "UC"

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

    # PART headings + their step content
    parts = []
    part_pattern = re.compile(r"^(PART [A-Z\d]+ ?[—\-–].+)$", re.MULTILINE)
    part_matches = list(part_pattern.finditer(text))
    for i, m in enumerate(part_matches):
        title = m.group(1).strip()
        title = re.sub(r"\s*[—\-–]+\s*", " — ", title, count=1)
        # Extract lines between this PART heading and the next (or KEY LEARNING / end)
        start = m.end()
        end = part_matches[i + 1].start() if i + 1 < len(part_matches) else len(text)
        block = text[start:end]
        # Strip the underline row and collect non-empty lines
        steps = []
        for line in block.splitlines():
            stripped = line.strip().lstrip("─—–-").strip()
            if stripped and not re.match(r"^KEY LEARNING", stripped, re.IGNORECASE):
                steps.append(stripped)
        parts.append({"title": title, "steps": steps, "screenshot": ""})

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
        "folder": f"{UC_DIR}/{folder_name}",
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

    # Scan UC/UC-*/ folders
    uc_folders = sorted(
        d for d in os.listdir(UC_DIR)
        if re.match(r"UC-\d+", d, re.IGNORECASE) and os.path.isdir(os.path.join(UC_DIR, d))
    )

    usecases = []
    for folder_name in uc_folders:
        uc_id = folder_to_id(folder_name)
        folder_path = os.path.join(UC_DIR, folder_name)
        entry = build_uc_entry(folder_name, folder_path, existing_map.get(uc_id, {}))
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
