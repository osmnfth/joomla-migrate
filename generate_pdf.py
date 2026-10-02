import os

# ============================================================
# WEASYPRINT - WINDOWS
# ============================================================

os.environ["WEASYPRINT_DLL_DIRECTORIES"] = r"C:\msys64\ucrt64\bin"


# ============================================================
# IMPORTS
# ============================================================

import csv
import re
import html

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from weasyprint import HTML


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_CSV = "input.csv"

OUTPUT_PREFIX = "archive-report"

BASE_URL = "https://www.vo.duth.gr"

REPORT_TITLE = "ΑΝΑΚΟΙΝΩΣΕΙΣ & ΠΡΟΚΗΡΥΞΕΙΣ"

REPORT_SUBTITLE = "Αρχείο δημοσιεύσεων"


# ============================================================
# DATE HELPERS
# ============================================================

def parse_date(value):

    if not value:
        return None

    value = value.strip()

    formats = [

        # Current CSV format
        "%Y-%m-%d %H:%M:%S",

        # Without seconds
        "%Y-%m-%d %H:%M",

        # Old formats
        "%d-%m-%y %H:%M:%S",
        "%d-%m-%y %H:%M",

        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",

    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:

            continue

    return None


def format_date(value):

    """
    Example:

        2026-09-30 12:11:20

    becomes:

        30 ΣΕΠ 2026

    Time is intentionally NOT displayed.
    """

    dt = parse_date(value)

    if not dt:
        return value

    months = {

        1: "ΙΑΝ",
        2: "ΦΕΒ",
        3: "ΜΑΡ",
        4: "ΑΠΡ",
        5: "ΜΑΪ",
        6: "ΙΟΥΝ",
        7: "ΙΟΥΛ",
        8: "ΑΥΓ",
        9: "ΣΕΠ",
        10: "ΟΚΤ",
        11: "ΝΟΕ",
        12: "ΔΕΚ",

    }

    return (
        f"{dt.day:02d} "
        f"{months[dt.month]} "
        f"{dt.year}"
    )


# ============================================================
# URL HELPERS
# ============================================================

def absolute_url(url):

    if not url:
        return ""

    url = html.unescape(
        url.strip()
    )

    if url.startswith("http://"):
        return url

    if url.startswith("https://"):
        return url

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return (
            BASE_URL.rstrip("/")
            + url
        )

    return (
        BASE_URL.rstrip("/")
        + "/"
        + url
    )


def announcement_url(slug):

    """
    Creates the original announcement URL.

    Example:

        my-announcement

    becomes:

        https://www.vo.duth.gr/my-announcement
    """

    if not slug:
        return ""

    slug = slug.strip()

    if not slug:
        return ""

    if slug.startswith("http://"):
        return slug

    if slug.startswith("https://"):
        return slug

    return (
        BASE_URL.rstrip("/")
        + "/"
        + slug.lstrip("/")
    )


# ============================================================
# HTML HELPERS
# ============================================================

def escape(text):

    return html.escape(
        text or ""
    )


def clean_content(content):

    if not content:
        return ""

    content = html.unescape(
        content
    )

    # --------------------------------------------------------
    # Convert relative href URLs to absolute URLs
    # --------------------------------------------------------

    def replace_href(match):

        quote = match.group(1)

        url = match.group(2)

        return (
            f'href={quote}'
            f'{absolute_url(url)}'
            f'{quote}'
        )

    content = re.sub(

        r'href=(["\'])(.*?)\1',

        replace_href,

        content,

        flags=re.IGNORECASE

    )

    # --------------------------------------------------------
    # Remove scripts
    # --------------------------------------------------------

    content = re.sub(

        r'<script\b[^>]*>.*?</script>',

        '',

        content,

        flags=re.IGNORECASE | re.DOTALL

    )

    # --------------------------------------------------------
    # Remove style tags
    # --------------------------------------------------------

    content = re.sub(

        r'<style\b[^>]*>.*?</style>',

        '',

        content,

        flags=re.IGNORECASE | re.DOTALL

    )

    # --------------------------------------------------------
    # Remove empty paragraphs
    # --------------------------------------------------------

    content = re.sub(

        r'<p>\s*(?:&nbsp;|\s)*</p>',

        '',

        content,

        flags=re.IGNORECASE

    )

    # --------------------------------------------------------
    # Remove excessive whitespace
    # --------------------------------------------------------

    content = re.sub(

        r'\n\s*\n\s*\n+',

        '\n\n',

        content

    )

    return content.strip()


# ============================================================
# STYLE LINKS INSIDE CONTENT
# ============================================================

def style_content_links(content):

    if not content:
        return ""

    pattern = re.compile(

        r'<a\s+([^>]*?)href=(["\'])(.*?)\2([^>]*)>'
        r'(.*?)'
        r'</a>',

        re.IGNORECASE | re.DOTALL

    )

    def replace_link(match):

        url = match.group(3)

        label = match.group(5)

        # ----------------------------------------------------
        # Remove HTML from label
        # ----------------------------------------------------

        clean_label = re.sub(

            r"<[^>]+>",

            "",

            label

        ).strip()

        clean_label = html.unescape(
            clean_label
        )

        if not clean_label:

            clean_label = (
                "Άνοιγμα εγγράφου"
            )

        final_url = absolute_url(
            url
        )

        return f"""

        <a
            class="document-link"
            href="{escape(final_url)}"
        >

            <span class="document-icon">
                ↗
            </span>

            <span class="document-info">

                <span class="document-name">
                    {escape(clean_label)}
                </span>

                <span class="document-action">
                    Άνοιγμα εγγράφου
                </span>

            </span>

        </a>

        """

    return pattern.sub(
        replace_link,
        content
    )


# ============================================================
# READ CSV
# ============================================================

rows = []

print()
print("=" * 70)
print("READING CSV")
print("=" * 70)
print()


with open(

    INPUT_CSV,

    "r",

    encoding="utf-8-sig",

    newline=""

) as f:

    sample = f.read(
        8192
    )

    f.seek(0)

    # --------------------------------------------------------
    # Detect delimiter
    # --------------------------------------------------------

    try:

        dialect = csv.Sniffer().sniff(

            sample,

            delimiters=",;\t"

        )

    except csv.Error:

        dialect = csv.excel_tab


    reader = csv.DictReader(

        f,

        dialect=dialect

    )


    print(
        "CSV columns:"
    )

    print(
        reader.fieldnames
    )

    print()


    for row_number, row in enumerate(

        reader,

        start=2

    ):

        title = (
            row.get("title")
            or ""
        ).strip()

        date = (
            row.get("date")
            or ""
        ).strip()

        slug = (
            row.get("slug")
            or ""
        ).strip()

        content = (
            row.get("content")
            or ""
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Year comes from DATE.
        #
        # We do not use the CSV year column.
        # ----------------------------------------------------

        dt = parse_date(
            date
        )

        year = (
            dt.year
            if dt
            else None
        )

        rows.append({

            "title": title,

            "date": date,

            "slug": slug,

            "year": year,

            "content": content,

            "datetime": dt,

            "csv_row": row_number,

        })


# ============================================================
# BASIC CHECK
# ============================================================

print(
    f"Rows read from CSV: {len(rows)}"
)

print()


# ============================================================
# INVALID DATES
# ============================================================

invalid_date_rows = [

    item

    for item in rows

    if item["datetime"] is None

]


if invalid_date_rows:

    print(
        "WARNING:"
    )

    print(
        f"{len(invalid_date_rows)} rows "
        f"have invalid dates."
    )

    print()

    for item in invalid_date_rows[:20]:

        print(

            f"  CSV row {item['csv_row']}: "
            f"{item['date']} | "
            f"{item['title'][:80]}"

        )

    print()

else:

    print(
        "All dates are valid."
    )

    print()


# ============================================================
# GROUP BY YEAR
# ============================================================

rows_by_year = defaultdict(list)


for item in rows:

    year = item["year"]

    if year:

        rows_by_year[
            year
        ].append(item)


# ============================================================
# SORT
# ============================================================

for year in rows_by_year:

    rows_by_year[year].sort(

        key=lambda x:

            x["datetime"]

            if x["datetime"]

            else datetime.min,

        reverse=True

    )


# ============================================================
# YEAR STATISTICS
# ============================================================

print(
    "=" * 70
)

print(
    "PUBLICATIONS BY YEAR"
)

print(
    "=" * 70
)

print()


for year in sorted(
    rows_by_year.keys()
):

    print(

        f"{year}: "
        f"{len(rows_by_year[year])} publications"

    )


print()


if invalid_date_rows:

    print(

        f"Publications without valid year: "
        f"{len(invalid_date_rows)}"

    )

else:

    print(
        "All publications have a valid year."
    )


print()


# ============================================================
# CSS
# ============================================================

CSS = """

@page {

    size: A4;

    margin:
        18mm
        16mm
        20mm
        16mm;

    @bottom-right {

        content:
            "Σελίδα "
            counter(page);

        font-family:
            "DejaVu Sans",
            Arial,
            sans-serif;

        font-size: 8pt;

        color: #999;

    }

}


/* =========================================================
   RESET
   ========================================================= */

* {
    box-sizing: border-box;
}


html,
body {

    margin: 0;
    padding: 0;

}


/* =========================================================
   BODY
   ========================================================= */

body {

    font-family:
        "DejaVu Sans",
        Arial,
        sans-serif;

    color: #171717;

    background: #ffffff;

    font-size: 10pt;

    line-height: 1.5;

}


/* =========================================================
   HEADER
   ========================================================= */

.header {

    padding-bottom: 22px;

    border-bottom:
        2px solid #171717;

    margin-bottom: 28px;

}


.eyebrow {

    font-size: 8pt;

    font-weight: 700;

    letter-spacing: 2px;

    text-transform: uppercase;

    color: #777;

    margin-bottom: 9px;

}


h1 {

    font-size: 25pt;

    line-height: 1.05;

    letter-spacing: -0.7px;

    margin:
        0
        0
        10px
        0;

    font-weight: 800;

}


.subtitle {

    color: #777;

    font-size: 9pt;

}


.report-year {

    margin-top: 12px;

    font-size: 12pt;

    font-weight: 700;

    color: #333;

}


/* =========================================================
   STATISTICS
   ========================================================= */

.stats {

    margin-top: 18px;

    display: flex;

    gap: 28px;

}


.stat {

    font-size: 8pt;

    color: #777;

    text-transform: uppercase;

    letter-spacing: 1px;

}


.stat strong {

    color: #171717;

    font-size: 11pt;

    letter-spacing: 0;

    margin-right: 4px;

}


/* =========================================================
   CARD
   ========================================================= */

.card {

    display: flex;

    gap: 16px;

    padding-bottom: 27px;

    margin-bottom: 27px;

    border-bottom:
        1px solid #dedede;

    page-break-inside: avoid;

}


.card-number {

    width: 34px;

    flex:
        0 0 34px;

    color: #aaa;

    font-size: 8pt;

    font-weight: 700;

    padding-top: 3px;

}


.card-content {

    flex: 1;

    min-width: 0;

}


/* =========================================================
   DATE
   ========================================================= */

.date {

    font-size: 8pt;

    font-weight: 700;

    color: #777;

    letter-spacing: 1.2px;

    text-transform: uppercase;

    margin-bottom: 8px;

}


/* =========================================================
   TITLE
   ========================================================= */

h2 {

    font-size: 15pt;

    line-height: 1.28;

    margin:
        0
        0
        17px
        0;

    font-weight: 700;

    max-width: 650px;

}


/* =========================================================
   CONTENT
   ========================================================= */

.post-content {

    margin-top: 8px;

    font-size: 9.5pt;

    line-height: 1.65;

    color: #333;

}


.post-content p {

    margin:
        0
        0
        13px
        0;

}


.post-content strong {

    font-weight: 700;

    color: #171717;

}


.post-content em {

    font-style: italic;

}


.post-content ul,
.post-content ol {

    margin:
        10px
        0
        15px
        23px;

    padding: 0;

}


.post-content li {

    margin-bottom: 5px;

}


/* =========================================================
   DOCUMENT LINKS
   ========================================================= */

.post-content .document-link {

    display: flex;

    align-items: center;

    gap: 10px;

    text-decoration: none;

    color: #171717;

    border:
        1px solid #d8d8d8;

    border-radius: 6px;

    padding:
        10px
        12px;

    margin:
        8px
        0;

    background: #fafafa;

    page-break-inside: avoid;

}


.document-icon {

    width: 28px;

    height: 28px;

    flex:
        0 0 28px;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 5px;

    background: #171717;

    color: white;

    font-size: 13pt;

    font-weight: 700;

}


.document-info {

    display: flex;

    flex-direction: column;

    min-width: 0;

}


.document-name {

    font-size: 9pt;

    font-weight: 700;

    color: #171717;

}


.document-action {

    font-size: 7.5pt;

    color: #888;

    margin-top: 1px;

}


/* =========================================================
   OTHER LINKS
   ========================================================= */

.post-content a:not(.document-link) {

    color: #2457a6;

    font-weight: 600;

    text-decoration: none;

    border-bottom:
        1px solid #b9c9e5;

}


/* =========================================================
   SOURCE
   ========================================================= */

.source {

    margin-top: 20px;

    padding-top: 10px;

    border-top:
        1px solid #eeeeee;

    font-size: 7.5pt;

    line-height: 1.5;

    color: #888;

}


.source-label {

    font-weight: 700;

    color: #555;

}


.source a {

    color: #2457a6;

    text-decoration: none;

    border-bottom:
        1px solid #b9c9e5;

    word-break: break-all;

}


.source a:hover {

    text-decoration: underline;

}


.source-missing {

    color: #aaa;

    font-style: italic;

}


/* =========================================================
   IMAGES
   ========================================================= */

.post-content img {

    max-width: 100%;

    height: auto;

    display: block;

    margin:
        15px
        0;

}


/* =========================================================
   TABLES
   ========================================================= */

.post-content table {

    width: 100%;

    border-collapse: collapse;

    margin:
        15px
        0;

    font-size: 8.5pt;

}


.post-content th {

    text-align: left;

    background: #f1f1f1;

    font-weight: 700;

}


.post-content th,
.post-content td {

    border:
        1px solid #ddd;

    padding: 7px;

    vertical-align: top;

}


/* =========================================================
   EMPTY
   ========================================================= */

.empty-content {

    color: #999;

    font-style: italic;

}


/* =========================================================
   FOOTER
   ========================================================= */

.report-footer {

    margin-top: 30px;

    padding-top: 12px;

    border-top:
        1px solid #dedede;

    color: #999;

    font-size: 7.5pt;

}

"""


# ============================================================
# CREATE PDF FOR EACH YEAR
# ============================================================

created_files = []


print(
    "=" * 70
)

print(
    "CREATING YEARLY PDF FILES"
)

print(
    "=" * 70
)

print()


for year in sorted(
    rows_by_year.keys()
):

    year_rows = rows_by_year[
        year
    ]


    # --------------------------------------------------------
    # BUILD CARDS
    # --------------------------------------------------------

    cards = []


    for index, item in enumerate(

        year_rows,

        start=1

    ):

        content = clean_content(
            item["content"]
        )

        content = style_content_links(
            content
        )


        if not content:

            content = """
            <p class="empty-content">
                Δεν υπάρχει διαθέσιμο περιεχόμενο.
            </p>
            """


        # ----------------------------------------------------
        # SOURCE URL
        # ----------------------------------------------------

        source_url = announcement_url(
            item["slug"]
        )


        if source_url:

            source_html = f"""

            <div class="source">

                <span class="source-label">

                    Αρχικός σύνδεσμος ανακοίνωσης:

                </span>

                <a
                    href="{escape(source_url)}"
                >

                    {escape(source_url)}

                </a>

            </div>

            """

        else:

            source_html = """

            <div class="source">

                <span class="source-label">

                    Αρχικός σύνδεσμος ανακοίνωσης:

                </span>

                <span class="source-missing">

                    Δεν υπάρχει διαθέσιμος σύνδεσμος.

                </span>

            </div>

            """


        # ----------------------------------------------------
        # CARD
        # ----------------------------------------------------

        cards.append(f"""

        <article class="card">


            <div class="card-number">

                {index:02d}

            </div>


            <div class="card-content">


                <div class="date">

                    {escape(
                        format_date(
                            item["date"]
                        )
                    )}

                </div>


                <h2>

                    {escape(
                        item["title"]
                    )}

                </h2>


                <div class="post-content">

                    {content}

                </div>


                {source_html}


            </div>


        </article>

        """)


    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    total_posts = len(
        year_rows
    )


    total_links = 0


    for item in year_rows:

        content = (
            item["content"]
            or ""
        )

        links = re.findall(

            r'<a\b',

            content,

            flags=re.IGNORECASE

        )

        total_links += len(
            links
        )


    # --------------------------------------------------------
    # DOCUMENT HTML
    # --------------------------------------------------------

    document_html = f"""

    <!DOCTYPE html>

    <html lang="el">

    <head>

        <meta charset="UTF-8">

        <style>

            {CSS}

        </style>

    </head>


    <body>


        <header class="header">


            <div class="eyebrow">

                Archive

            </div>


            <h1>

                {escape(
                    REPORT_TITLE
                )}

            </h1>


            <div class="subtitle">

                {escape(
                    REPORT_SUBTITLE
                )}

            </div>


            <div class="report-year">

                Έτος {year}

            </div>


            <div class="stats">


                <div class="stat">

                    <strong>

                        {total_posts}

                    </strong>

                    δημοσιεύσεις

                </div>


                <div class="stat">

                    <strong>

                        {total_links}

                    </strong>

                    έγγραφα

                </div>


            </div>


        </header>


        <main>

            {''.join(cards)}

        </main>


        <div class="report-footer">

            Δημιουργήθηκε από το αρχείο δημοσιεύσεων.

        </div>


    </body>

    </html>

    """


    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output_pdf = (
        f"{OUTPUT_PREFIX}-{year}.pdf"
    )


    print(
        f"Creating {output_pdf}..."
    )


    HTML(

        string=document_html,

        base_url=str(
            Path.cwd()
        )

    ).write_pdf(

        output_pdf

    )


    created_files.append(
        output_pdf
    )


    print(

        f"  OK - "
        f"{total_posts} publications"

    )

    print()


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("PDF ARCHIVE CREATED SUCCESSFULLY")
print("=" * 70)
print()


for filename in created_files:

    print(
        f"  {filename}"
    )


print()

print(
    f"Total PDFs: {len(created_files)}"
)

print(
    f"Total publications: {len(rows)}"
)

print()

print(
    "Publications assigned to a year: "
    f"{sum(len(v) for v in rows_by_year.values())}"
)

print(
    "Publications without a year: "
    f"{len(invalid_date_rows)}"
)

print()

print("=" * 70)
