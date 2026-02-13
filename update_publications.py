#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update index.jemdoc Recent Publications (keep at most 5, merge with temp list)
and publication.jemdoc (add new entries from temp list, no duplicates).
"""

import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_LIST = os.path.join(SCRIPT_DIR, "temp-publication-list.txt")
INDEX_JEMDOC = os.path.join(SCRIPT_DIR, "index.jemdoc")
PUBLICATION_JEMDOC = os.path.join(SCRIPT_DIR, "publication.jemdoc")


def normalize_title(s):
    """Normalize title for duplicate comparison."""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s.strip().lower())
    s = re.sub(r"[^\w\s]", "", s)
    return s


def extract_year_from_line(line):
    """From 4th line like '2025' or '285\\t2025' or '3\\t2024', return year (last number)."""
    parts = re.findall(r"\d+", line.strip())
    return int(parts[-1]) if parts else None


def parse_temp_list(path):
    """Parse temp-publication-list.txt. Returns list of dicts: title, authors, venue, year."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f.readlines()]
    entries = []
    i = 0
    while i + 4 <= len(lines):
        title = lines[i].strip()
        authors = lines[i + 1].strip()
        venue = lines[i + 2].strip()
        year_line = lines[i + 3]
        year = extract_year_from_line(year_line)
        if title and year is not None:
            entries.append({
                "title": title,
                "authors": authors,
                "venue": venue,
                "year": year,
            })
        i += 4
    return entries


def venue_abbreviation(venue, year):
    """Extract or guess abbreviation for venue. Returns (abbr, full_venue). full_venue is cleaned (no duplicate year, no pages)."""
    venue = venue.strip()
    # Already has (XXX) with letters e.g. "2025 Winter Simulation Conference (WSC), 558-569"
    # Skip single digit or pure numbers (e.g. volume/issue (3), (1))
    m = re.search(r"\(([A-Za-z][A-Za-z0-9]+)\)", venue)
    if m:
        abbr = m.group(1).upper()
        return abbr, clean_venue_display(venue, year)
    # arXiv
    if "arxiv" in venue.lower():
        return "arXiv", clean_venue_display(venue, year)
    # Proceedings of the Nth ACM XXX Conference / International Conference on YYY
    if "Proceedings" in venue or "Conference" in venue or "Symposium" in venue:
        if "SIGKDD" in venue or "KDD" in venue:
            return "KDD", clean_venue_display(venue, year)
        if "Parallel Processing" in venue or "ICPP" in venue:
            return "ICPP", clean_venue_display(venue, year)
        if "Knowledge Graph" in venue or "ICKG" in venue:
            return "ICKG", clean_venue_display(venue, year)
        if "Winter Simulation" in venue or "WSC" in venue:
            return "WSC", clean_venue_display(venue, year)
        # Generic: take first acronym-like part or first word
        words = re.findall(r"[A-Z][a-z]+|[A-Z]+", venue)
        if words:
            abbr = "".join(w[0] for w in words[:4]).upper()
            if len(abbr) >= 2:
                return abbr, clean_venue_display(venue, year)
    # Journal: IEEE Transactions on X -> TX or known
    if "Transactions" in venue or "Journal" in venue or "Computing Surveys" in venue:
        if "Parallel and Distributed" in venue:
            return "TPDS", clean_venue_display(venue, year)
        if "Networking" in venue:
            return "ToN", clean_venue_display(venue, year)
        if "Computing Surveys" in venue:
            return "CSUR", clean_venue_display(venue, year)
        if "Internet Technology" in venue:
            return "TOIT", clean_venue_display(venue, year)
        words = re.findall(r"\b[A-Z][a-z]*\b", venue)
        if words:
            abbr = "".join(w[0] for w in words[:4]).upper()
            if len(abbr) >= 2:
                return abbr, clean_venue_display(venue, year)
    # Fallback: first 4-6 chars of first word
    first = re.match(r"^[\w]+", venue)
    if first:
        abbr = first.group(0)[:6].upper()
        return abbr, clean_venue_display(venue, year)
    return "Venue", clean_venue_display(venue, year)


def format_authors(authors_str):
    """Replace 'H Wang' with '*Haoyu Wang*' (word-boundary aware)."""
    # Replace "H Wang" only when it's a distinct author (after comma+space or start)
    s = authors_str.strip()
    s = re.sub(r"(^|,\s*)H Wang(\s*,|\s*$|$)", r"\1*Haoyu Wang*\2", s)
    s = re.sub(r"(^|,\s*)H\. Wang(\s*,|\s*$|$)", r"\1*Haoyu Wang*\2", s)
    return s


def clean_venue_display(venue_str, year=None):
    """Remove duplicate leading year and trailing page numbers from venue string."""
    s = venue_str.strip()
    if year is not None:
        s = re.sub(r"^%d\s+" % year, "", s)
    s = re.sub(r"^\d{4}\s+", "", s)
    s = re.sub(r",\s*\d+-\d+\s*$", "", s)
    s = re.sub(r",\s*pp\.\s*\d+-\d+\s*$", "", s, flags=re.IGNORECASE)
    return s.strip().rstrip(",").strip()


def clean_jemdoc_venues_in_content(content):
    """In jemdoc file content: remove duplicate year after *ABBR'YEAR*: and trailing page ranges."""
    content = re.sub(r"(\*[^*]+'\d{4}\*:\s*)\d{4}\s+", r"\1", content)
    content = re.sub(r",\s*\d+-\d+\s*$", "", content, flags=re.MULTILINE)
    return content


def is_journal(venue):
    """Classify as journal if venue looks like journal."""
    v = venue.lower()
    if "transactions" in v or "journal" in v or "computing surveys" in v or "survey" in v:
        return True
    if "proceedings" in v or "conference" in v or "symposium" in v:
        return False
    if "arxiv" in v:
        return False
    return False


def format_jemdoc_line(entry, bold_venue=True, use_ordered_list=False):
    """Format one entry as index.jemdoc single line. use_ordered_list: . for numbered, else - for bullet."""
    prefix = ". " if use_ordered_list else "- "
    authors = format_authors(entry["authors"])
    title = entry["title"].strip()
    abbr, full_venue = venue_abbreviation(entry["venue"], entry["year"])
    year = entry["year"]
    if bold_venue:
        venue_part = "*%s'%d*: %s" % (abbr, year, full_venue)
    else:
        venue_part = "%s'%d: %s" % (abbr, year, full_venue)
    return "%s%s\\n %s\\n %s" % (prefix, authors, title, venue_part)


def format_publication_block(entry, bold_venue=True):
    """Format one entry for publication.jemdoc (multi-line block)."""
    authors = format_authors(entry["authors"])
    title = entry["title"].strip()
    abbr, full_venue = venue_abbreviation(entry["venue"], entry["year"])
    year = entry["year"]
    if bold_venue:
        venue_part = "*%s'%d*: %s" % (abbr, year, full_venue)
    else:
        venue_part = "%s'%d: %s" % (abbr, year, full_venue)
    return ". %s\\n\n%s\n%s" % (authors, title, venue_part)


def parse_index_recent(path):
    """Parse index.jemdoc: return list of {title_norm, year, raw_line} for Recent Publications."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    entries = []
    in_section = False
    for line in content.splitlines():
        if line.strip().startswith("== Recent Publications"):
            in_section = True
            continue
        if in_section:
            if line.strip().startswith("[publication.html"):
                break
            stripped = line.strip()
            if stripped.startswith(". ") or stripped.startswith("- "):
                raw = stripped
                parts = raw.split("\\n ")
                if len(parts) >= 2:
                    title_part = parts[1].strip()
                    title_norm = normalize_title(title_part)
                    year = None
                    if len(parts) >= 3:
                        m = re.search(r"'(\d{4})", parts[2])
                        if m:
                            year = int(m.group(1))
                    entries.append({"title_norm": title_norm, "year": year, "raw": raw})
    return entries


def parse_publication_entries(path):
    """Parse publication.jemdoc. Return (conference_entries, journal_entries) each list of {title_norm, year, raw_block}."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    conference = []
    journal = []
    current_section = None
    current_block = []
    current_started = False

    for i, line in enumerate(lines):
        if line.strip().startswith("== Conference"):
            current_section = "conference"
            current_block = []
            current_started = False
            continue
        if line.strip().startswith("== Journal"):
            current_section = "journal"
            current_block = []
            current_started = False
            continue
        if line.strip().startswith(". "):
            if current_block and current_started:
                text = "".join(current_block)
                title_norm, year = _extract_title_year_from_block(text)
                entry_dict = {"title_norm": title_norm, "year": year, "raw": text}
                if current_section == "conference":
                    conference.append(entry_dict)
                elif current_section == "journal":
                    journal.append(entry_dict)
            current_block = [line]
            current_started = True
            continue
        if current_started and current_section and not line.strip().startswith("#"):
            current_block.append(line)

    if current_block and current_started:
        text = "".join(current_block)
        title_norm, year = _extract_title_year_from_block(text)
        entry_dict = {"title_norm": title_norm, "year": year, "raw": text}
        if current_section == "conference":
            conference.append(entry_dict)
        elif current_section == "journal":
            journal.append(entry_dict)

    return conference, journal


def _extract_title_year_from_block(block):
    """From a jemdoc entry block text, extract normalized title and year."""
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    if not lines:
        return "", None
    year = None
    title_parts = []
    for line in lines[1:]:
        if re.search(r"'?\d{4}'?", line) or re.search(r"\d{4}:", line):
            m = re.search(r"'?(\d{4})'?", line)
            if m:
                year = int(m.group(1))
            break
        title_parts.append(line)
    title_part = " ".join(title_parts)
    if not title_part and len(lines) >= 2:
        first = lines[0]
        if "\\n" in first:
            rest = first.split("\\n", 1)[-1].strip()
            if rest and not re.search(r"\d{4}", rest):
                title_part = rest
    return normalize_title(title_part), year


def main():
    temp_entries = parse_temp_list(TEMP_LIST)
    if not temp_entries:
        print("No entries in temp-publication-list.txt")
        return

    index_recent = parse_index_recent(INDEX_JEMDOC)
    conf_entries, journal_entries = parse_publication_entries(PUBLICATION_JEMDOC)
    existing_titles_index = {e["title_norm"] for e in index_recent}
    existing_titles_pub = set()
    for e in conf_entries + journal_entries:
        if e["title_norm"]:
            existing_titles_pub.add(e["title_norm"])

    # Build list for Recent: existing (with year from raw) + new from temp
    recent_items = []
    for e in index_recent:
        title_norm = e["title_norm"]
        year = e["year"] or 0
        recent_items.append({"title_norm": title_norm, "year": year, "raw": e["raw"], "from_existing": True})
    for t in temp_entries:
        tn = normalize_title(t["title"])
        if tn in existing_titles_index:
            continue
        recent_items.append({
            "title_norm": tn,
            "year": t["year"],
            "raw": None,
            "from_existing": False,
            "entry": t,
        })

    recent_items.sort(key=lambda x: (-x["year"], x["title_norm"]))
    recent_top5 = recent_items[:5]

    # Build new Recent Publications section lines (use "-" for unnumbered list)
    recent_lines = []
    for item in recent_top5:
        if item.get("from_existing"):
            raw = item["raw"].strip()
            if raw.startswith(". "):
                raw = "- " + raw[2:]
            recent_lines.append(raw)
        else:
            recent_lines.append(format_jemdoc_line(item["entry"], use_ordered_list=False))

    # Update index.jemdoc
    with open(INDEX_JEMDOC, "r", encoding="utf-8") as f:
        index_content = f.read()
    new_index = re.sub(
        r"(== Recent Publications \([^)]+\))\n(.*?)(\n\[publication\.html Full list of publications\]\.)",
        lambda m: m.group(1) + "\n" + "\n".join(recent_lines) + "\n\n" + m.group(3),
        index_content,
        flags=re.DOTALL,
    )
    with open(INDEX_JEMDOC, "w", encoding="utf-8") as f:
        f.write(new_index)
    with open(INDEX_JEMDOC, "r", encoding="utf-8") as f:
        index_content = f.read()
    with open(INDEX_JEMDOC, "w", encoding="utf-8") as f:
        f.write(clean_jemdoc_venues_in_content(index_content))
    print("Updated index.jemdoc Recent Publications (top 5).")

    # Add new entries to publication.jemdoc (no duplicate)
    new_conf = [t for t in temp_entries if not is_journal(t["venue"]) and normalize_title(t["title"]) not in existing_titles_pub]
    new_journal = [t for t in temp_entries if is_journal(t["venue"]) and normalize_title(t["title"]) not in existing_titles_pub]
    for t in new_conf + new_journal:
        existing_titles_pub.add(normalize_title(t["title"]))

    with open(PUBLICATION_JEMDOC, "r", encoding="utf-8") as f:
        pub_content = f.read()

    if new_conf or new_journal:
        seen_conf = {_extract_title_year_from_block(e["raw"])[0] for e in conf_entries}
        seen_journal = {_extract_title_year_from_block(e["raw"])[0] for e in journal_entries}
        all_conf = [{"year": _extract_title_year_from_block(e["raw"])[1] or 0, "raw": e["raw"]} for e in conf_entries]
        for t in new_conf:
            tn = normalize_title(t["title"])
            if tn and tn not in seen_conf:
                seen_conf.add(tn)
                all_conf.append({"year": t["year"], "raw": format_publication_block(t)})
        all_journal = [{"year": _extract_title_year_from_block(e["raw"])[1] or 0, "raw": e["raw"]} for e in journal_entries]
        for t in new_journal:
            tn = normalize_title(t["title"])
            if tn and tn not in seen_journal:
                seen_journal.add(tn)
                all_journal.append({"year": t["year"], "raw": format_publication_block(t)})
        all_conf.sort(key=lambda x: -x["year"])
        all_journal.sort(key=lambda x: -x["year"])

        def replace_section(content, header_pattern, entries_with_raw):
            """Replace section body with new list of entries. Each entry raw is multi-line string."""
            m = re.search(r"(" + re.escape(header_pattern) + r")\s*\n(.*?)(?=\n== |\Z)", content, re.DOTALL)
            if not m:
                return content
            new_body_lines = []
            for x in entries_with_raw:
                new_body_lines.extend(x["raw"].strip().split("\n"))
            new_body = "\n".join(new_body_lines)
            return content[: m.start(2)] + new_body + content[m.end(2) :]

        pub_content = replace_section(pub_content, "== Conference publications", all_conf)
        pub_content = replace_section(pub_content, "== Journal publications", all_journal)

        with open(PUBLICATION_JEMDOC, "w", encoding="utf-8") as f:
            f.write(pub_content)
        with open(PUBLICATION_JEMDOC, "r", encoding="utf-8") as f:
            pub_content = f.read()
        with open(PUBLICATION_JEMDOC, "w", encoding="utf-8") as f:
            f.write(clean_jemdoc_venues_in_content(pub_content))
        print("Updated publication.jemdoc: added %d conference, %d journal." % (len(new_conf), len(new_journal)))
    else:
        with open(PUBLICATION_JEMDOC, "r", encoding="utf-8") as f:
            pub_content = f.read()
        with open(PUBLICATION_JEMDOC, "w", encoding="utf-8") as f:
            f.write(clean_jemdoc_venues_in_content(pub_content))
        print("No new publication entries to add (all duplicates); venue lines cleaned.")


if __name__ == "__main__":
    main()
