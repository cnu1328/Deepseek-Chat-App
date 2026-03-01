import streamlit as st
import os
import time
import io
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from gnews import GNews
from googleapiclient.discovery import build
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Daily News Report Generator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS — Clean White / Light Theme
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #f8f9fc !important;
    color: #1a1d23 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e3e6ef !important;
}
[data-testid="stSidebar"] * {
    color: #1a1d23 !important;
}

/* ── Main header ── */
.main-header {
    text-align: center;
    padding: 2.2rem 0 1.4rem;
    border-bottom: 2px solid #e8ecf4;
    margin-bottom: 2rem;
}
.main-header h1 {
    font-family: 'Playfair Display', serif !important;
    font-size: 2.6rem;
    color: #11141c !important;
    letter-spacing: -0.3px;
    margin: 0;
}
.main-header p {
    color: #6b7280 !important;
    font-size: 1rem;
    margin-top: 0.45rem;
    font-weight: 400;
}

/* ── Keyword result cards ── */
.keyword-card {
    background: #ffffff;
    border: 1.5px solid #e3e6ef;
    border-radius: 12px;
    padding: 1.2rem 1.5rem 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.keyword-card:hover {
    border-color: #4f6ef7;
    box-shadow: 0 3px 12px rgba(79,110,247,0.1);
}

/* ── Stat chips ── */
.stat-chip {
    display: inline-block;
    border-radius: 20px;
    padding: 0.22rem 0.85rem;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 0.25rem 0.2rem 0.25rem 0;
}
.stat-chip.en { background: #eff4ff; border: 1px solid #b8caff; color: #2f52c4; }
.stat-chip.te { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; }
.stat-chip.hi { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
.stat-chip.yt { background: #fff1f2; border: 1px solid #fecdd3; color: #be123c; }

/* ── Log box ── */
.log-container {
    background: #fafbfd;
    border: 1px solid #e3e6ef;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #4b5563;
    max-height: 300px;
    overflow-y: auto;
}
.log-line { margin: 3px 0; }
.log-ok   { color: #059669; font-weight: 500; }
.log-err  { color: #dc2626; font-weight: 500; }
.log-info { color: #2563eb; font-weight: 500; }

/* ── Section label ── */
.section-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #9ca3af;
    margin: 1.4rem 0 0.4rem;
    font-weight: 700;
}

/* ── Primary action button ── */
.stButton > button {
    background: #4f6ef7 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    transition: background 0.18s, box-shadow 0.18s !important;
    box-shadow: 0 2px 6px rgba(79,110,247,0.25) !important;
}
.stButton > button:hover {
    background: #3a57e8 !important;
    box-shadow: 0 4px 12px rgba(79,110,247,0.35) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #16a34a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    width: 100% !important;
    box-shadow: 0 2px 6px rgba(22,163,74,0.2) !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #15803d !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input {
    background: #ffffff !important;
    color: #1a1d23 !important;
    border: 1.5px solid #d1d5db !important;
    border-radius: 7px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #4f6ef7 !important;
    box-shadow: 0 0 0 3px rgba(79,110,247,0.12) !important;
}

/* ── Date input ── */
.stDateInput > div > div > input {
    background: #ffffff !important;
    color: #1a1d23 !important;
    border: 1.5px solid #d1d5db !important;
    border-radius: 7px !important;
}

/* ── Labels ── */
label, .stMarkdown p {
    color: #374151 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: #1a1d23 !important;
    font-weight: 600 !important;
}

/* ── Info box ── */
[data-testid="stAlert"] {
    background: #eff6ff !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 8px !important;
    color: #1e40af !important;
}

/* ── Divider ── */
hr { border-color: #e5e7eb !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# STYLES FOR EXCEL
# ============================================================
TITLE_FILL  = PatternFill("solid", start_color="1B2A3B", end_color="1B2A3B")
TITLE_FONT  = Font(bold=True, color="FFFFFF", name="Arial", size=13)
HEADER_FILL = PatternFill("solid", start_color="2E4057", end_color="2E4057")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=10)

PLATFORM_STYLES = {
    "Articles (English)": {
        "fill": PatternFill("solid", start_color="D6EAF8", end_color="D6EAF8"),
        "font": Font(bold=True, color="1A5276", name="Arial", size=10),
    },
    "Articles (Telugu)": {
        "fill": PatternFill("solid", start_color="D1F2EB", end_color="D1F2EB"),
        "font": Font(bold=True, color="117A65", name="Arial", size=10),
    },
    "Articles (Hindi)": {
        "fill": PatternFill("solid", start_color="FDEBD0", end_color="FDEBD0"),
        "font": Font(bold=True, color="7E5109", name="Arial", size=10),
    },
    "Youtube": {
        "fill": PatternFill("solid", start_color="FDEDEC", end_color="FDEDEC"),
        "font": Font(bold=True, color="922B21", name="Arial", size=10),
    },
}

ROW_FILLS   = [PatternFill("solid", start_color="FDFEFE"), PatternFill("solid", start_color="F2F3F4")]
THIN        = Side(border_style="thin", color="BBBBBB")
MEDIUM      = Side(border_style="medium", color="555555")
THIN_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MED_BORDER  = Border(left=MEDIUM, right=MEDIUM, top=MEDIUM, bottom=MEDIUM)
CENTER      = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT        = Alignment(horizontal="left", vertical="center", wrap_text=True)
DATA_FONT   = Font(name="Arial", size=10)
LINK_FONT   = Font(name="Arial", size=10, color="0563C1", underline="single")

# ============================================================
# FETCH FUNCTIONS
# ============================================================

def parse_gnews_date(article):
    pub = article.get("published date") or article.get("published_date") or ""
    if not pub:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(pub).replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(pub[:len(fmt)+5].strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def fetch_all_articles_for_window(keyword, lang, from_date, to_date, start_dt, end_dt, log_lines):
    """
    from_date, to_date: user-selected calendar dates (for GNews RSS query: after/before).
    start_dt, end_dt: UTC datetimes of the IST window (for post-filtering).
    """
    # GNews "period" means "last N days from TODAY" (rolling window). So for 26 Feb we must
    # set period so that "last N days" includes 26 Feb (e.g. if today=28 Feb, use 3d), then
    # we post-filter to start_dt/end_dt so only the selected date(s) are kept.
    today_ist = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    days_back = (today_ist - from_date).days + 1
    period_days = max(1, min(days_back, 30))
    period_str = f"{period_days}d"
    client = GNews(language=lang, country="IN", period=period_str, max_results=1000)
    # Use calendar dates so RSS matches direct URL (e.g. after:2026-02-25 before:2026-02-26)
    client.start_date = (from_date.year, from_date.month, from_date.day)
    # "before" in RSS is exclusive: use day after to_date so 25 Feb → before:2026-02-26
    end_calendar = to_date + timedelta(days=1)
    client.end_date = (end_calendar.year, end_calendar.month, end_calendar.day)

    all_articles = []

    try:
        raw = client.get_news(keyword)
        for a in (raw or []):
            pub_dt = parse_gnews_date(a)
            # Keep only articles whose publish time falls in the IST-derived window (UTC)
            print(f"DEBUG: '{a.get('title', '')[:30]}...' published at '{a.get('published date', '')}' parsed as {pub_dt} UTC")
            if pub_dt is None or not (start_dt <= pub_dt <= end_dt):
                print(f"DEBUG:: Skipping '{a.get('title', '')[:30]}...' as it's outside '{pub_dt}'")
                continue
            url = a.get("url", "")
            all_articles.append({
                "title":     a.get("title", ""),
                "publisher": a.get("publisher", {}).get("title", "") if a.get("publisher") else "",
                "url":       url,
                "pub_date":  str(a.get("published date", "")),
                "pub_dt":    pub_dt,
            })
    except Exception as e:
        log_lines.append(f'<div class="log-line log-err">  [{lang.upper()}] Error: {e}</div>')

    # Sort by published date (oldest first) for easier reading
    _epoch = datetime.min.replace(tzinfo=timezone.utc)
    all_articles.sort(key=lambda x: x.get("pub_dt") or _epoch)
    log_lines.append(f'<div class="log-line log-ok">  [{lang.upper()}] \'{keyword}\' → {len(all_articles)} articles</div>')
    return all_articles


def fetch_all_youtube_videos(keyword, api_key, start_dt, end_dt, log_lines):
    videos = []
    seen_ids = set()

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        published_after  = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        published_before = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        next_page_token  = None
        page = 0
        max_pages = 20
        clean_keyword = keyword.replace('+', ' ')

        while True:
            page += 1
            params = dict(
                q=clean_keyword,
                part="snippet",
                type="video",
                maxResults=50,
                order="date",
                regionCode="IN",
                publishedAfter=published_after,
                publishedBefore=published_before,
            )
            if next_page_token:
                params["pageToken"] = next_page_token

            try:
                response = youtube.search().list(**params).execute()
            except Exception as e:
                log_lines.append(f'<div class="log-line log-err">  [YT] API error page {page}: {e}</div>')
                break

            for item in response.get("items", []):
                vid_id = item["id"].get("videoId", "")
                if not vid_id or vid_id in seen_ids:
                    continue
                snippet = item["snippet"]
                pub_str = snippet.get("publishedAt", "")
                pub_dt = None
                try:
                    pub_dt = datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if not (start_dt <= pub_dt <= end_dt):
                        continue
                except Exception:
                    pass

                seen_ids.add(vid_id)
                videos.append({
                    "title":    snippet.get("title", ""),
                    "channel":  snippet.get("channelTitle", ""),
                    "url":      f"https://www.youtube.com/watch?v={vid_id}",
                    "pub_date": pub_str[:10],
                    "pub_dt":   pub_dt,
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token or page >= max_pages:
                break
            time.sleep(0.15)

    except Exception as e:
        log_lines.append(f'<div class="log-line log-err">  [YT] Build error: {e}</div>')

    # Sort by published date (oldest first)
    _epoch = datetime.min.replace(tzinfo=timezone.utc)
    videos.sort(key=lambda x: x.get("pub_dt") or _epoch)
    log_lines.append(f'<div class="log-line log-ok">  [YT] \'{keyword}\' → {len(videos)} videos</div>')
    return videos

# ============================================================
# EXCEL WRITER
# ============================================================

def write_section(ws, platform_label, rows, start_row):
    if not rows:
        return start_row
    style   = PLATFORM_STYLES[platform_label]
    n       = len(rows)
    end_row = start_row + n - 1

    ws.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
    pc = ws.cell(row=start_row, column=1, value=platform_label)
    pc.font = style["font"]; pc.fill = style["fill"]; pc.alignment = CENTER

    for i, row in enumerate(rows):
        r        = start_row + i
        alt_fill = ROW_FILLS[i % 2]

        for col, key, align in [(2, "sno", CENTER), (3, "headline", LEFT), (4, "channel", LEFT)]:
            c = ws.cell(r, col, row.get(key, ""))
            c.alignment = align; c.fill = alt_fill; c.font = DATA_FONT; c.border = THIN_BORDER

        lk_c = ws.cell(r, 5)
        lk_c.fill = alt_fill; lk_c.alignment = CENTER; lk_c.border = THIN_BORDER
        url = row.get("url", "")
        if url:
            lk_c.hyperlink = url; lk_c.value = "Link"; lk_c.font = LINK_FONT
        else:
            lk_c.value = ""; lk_c.font = DATA_FONT

        ws.cell(r, 1).fill = style["fill"]; ws.cell(r, 1).border = THIN_BORDER
        ws.row_dimensions[r].height = 18

    return end_row + 1


def build_excel(keyword_name, date_str, articles_by_lang, yt_videos):
    wb = Workbook()
    ws = wb.active
    ws.title = keyword_name[:31]

    ws.merge_cells("A1:E1")
    ws["A1"].value = f"Report | {date_str}"
    ws["A1"].font = TITLE_FONT; ws["A1"].fill = TITLE_FILL
    ws["A1"].alignment = CENTER; ws["A1"].border = MED_BORDER
    ws.row_dimensions[1].height = 28

    for col, h in enumerate(["Platform", "S.No", "Headline", "Channel Name", "Link"], 1):
        c = ws.cell(row=2, column=col, value=h)
        c.font = HEADER_FONT; c.fill = HEADER_FILL
        c.alignment = CENTER; c.border = THIN_BORDER
    ws.row_dimensions[2].height = 22

    current_row = 3
    serial_no   = 1

    _epoch = datetime.min.replace(tzinfo=timezone.utc)

    for lang_code, label in [("en", "Articles (English)"), ("te", "Articles (Telugu)"), ("hi", "Articles (Hindi)")]:
        arts = articles_by_lang.get(lang_code, [])
        if not arts:
            continue
        arts_sorted = sorted(arts, key=lambda a: a.get("pub_dt") or _epoch)
        rows = [{"sno": serial_no + i, "headline": a["title"], "channel": a["publisher"], "url": a["url"]} for i, a in enumerate(arts_sorted)]
        serial_no  += len(rows)
        current_row = write_section(ws, label, rows, current_row)

    yt_sorted = sorted(yt_videos, key=lambda v: v.get("pub_dt") or _epoch)
    yt_rows = [{"sno": serial_no + i, "headline": v["title"], "channel": v["channel"], "url": v["url"]} for i, v in enumerate(yt_sorted)]
    write_section(ws, "Youtube", yt_rows, current_row)

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 6
    ws.column_dimensions["C"].width = 58
    ws.column_dimensions["D"].width = 28
    ws.column_dimensions["E"].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# SESSION STATE
# ============================================================
if "keywords" not in st.session_state:
    st.session_state.keywords = [{"en": "", "te": "", "hi": ""}]
if "results"  not in st.session_state:
    st.session_state.results  = []
if "log_html" not in st.session_state:
    st.session_state.log_html = ""
if "report_mode" not in st.session_state:
    st.session_state.report_mode = "single"

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown('<div class="section-label">Date Selection</div>', unsafe_allow_html=True)
    today_local = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    report_mode = st.radio(
        "Report type",
        options=["single", "range"],
        format_func=lambda x: "Single day" if x == "single" else "Date range",
        key="report_mode_radio",
        horizontal=True,
    )
    st.session_state.report_mode = report_mode

    if report_mode == "single":
        selected_date = st.date_input(
            "Report Date",
            value=datetime.now().date(),
            max_value=today_local,
            help="Fetch news/videos published on this date (12:00 AM – 11:59 PM IST, or until now if today)",
            key="single_date",
        )
        from_date = to_date = selected_date
    else:
        col_from, col_to = st.columns(2)
        with col_from:
            from_date = st.date_input(
                "From date",
                value=today_local,
                max_value=today_local,
                key="from_date",
            )
        with col_to:
            to_date = st.date_input(
                "To date",
                value=today_local,
                max_value=today_local,
                key="to_date",
            )
        if from_date > to_date:
            st.warning("From date must be on or before To date.")
        selected_date = from_date  # for filename when range uses same from/to

    yt_api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    st.markdown("---")
    st.markdown('<div class="section-label">Keywords</div>', unsafe_allow_html=True)

    kws = st.session_state.keywords
    for idx, kw in enumerate(kws):
        label = f"Keyword {idx+1}" + (f": {kw['en']}" if kw['en'] else "")
        with st.expander(label, expanded=True):
            kw["en"] = st.text_input("English *", value=kw["en"], key=f"en_{idx}", placeholder="e.g. BRS")
            kw["te"] = st.text_input("Telugu",    value=kw["te"], key=f"te_{idx}", placeholder="e.g. బీఆర్ఎస్")
            kw["hi"] = st.text_input("Hindi (optional)", value=kw["hi"], key=f"hi_{idx}", placeholder="e.g. बीआरएस")
            if len(kws) > 1:
                if st.button("🗑 Remove", key=f"rm_{idx}"):
                    st.session_state.keywords.pop(idx)
                    st.rerun()

    if st.button("➕ Add Keyword", use_container_width=True):
        st.session_state.keywords.append({"en": "", "te": "", "hi": ""})
        st.rerun()

    st.markdown("---")
    generate_btn = st.button("🚀 Generate Reports", use_container_width=True)

# ============================================================
# MAIN AREA
# ============================================================
st.markdown("""
<div class="main-header">
  <h1>📰 Daily News Report Generator</h1>
  <p>Fetch articles &amp; YouTube videos for any keyword — validated by date &amp; exported to Excel</p>
</div>
""", unsafe_allow_html=True)

IST = ZoneInfo("Asia/Kolkata")
today_ist = datetime.now(IST).date()

# Start = 00:00:00 IST on from_date; End = 23:59:59 IST on to_date (or current time if to_date is today)
start_dt_ist = datetime.combine(from_date, datetime.min.time(), tzinfo=IST)
if to_date == today_ist:
    end_dt_ist = datetime.now(IST).replace(second=59, microsecond=0)
    end_label  = end_dt_ist.strftime("%d %b %Y  %I:%M %p IST") + " (now)"
else:
    end_dt_ist = datetime.combine(to_date, datetime.max.time(), tzinfo=IST)
    end_label  = end_dt_ist.strftime("%d %b %Y  11:59 PM IST")

# Convert to UTC for API calls
start_dt = start_dt_ist.astimezone(timezone.utc)
end_dt   = end_dt_ist.astimezone(timezone.utc)

start_label = start_dt_ist.strftime("%d %b %Y  12:00 AM IST")
st.info(f"🕐 Fetching content published between **{start_label}** and **{end_label}** (IST)")

# ============================================================
# GENERATE
# ============================================================
if generate_btn:
    valid_kws = [k for k in st.session_state.keywords if k["en"].strip()]
    if not valid_kws:
        st.error("Please enter at least one keyword (English name is required).")
    elif report_mode == "range" and from_date > to_date:
        st.error("From date must be on or before To date.")
    else:
        st.session_state.results  = []
        st.session_state.log_html = ""
        log_lines = []
        results   = []

        total        = len(valid_kws)
        progress_bar = st.progress(0, text="Starting…")

        if report_mode == "single":
            date_str = from_date.strftime("%d %b %Y").upper()
            file_date_suffix = from_date.strftime("%Y%m%d")
        else:
            date_str = f"{from_date.strftime('%d %b %Y')} – {to_date.strftime('%d %b %Y')}"
            file_date_suffix = f"{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}"

        for ki, kw in enumerate(valid_kws):
            name_en = kw["en"].strip()
            name_te = kw["te"].strip()
            name_hi = kw["hi"].strip()

            log_lines.append(f'<div class="log-line log-info">{"─"*52}</div>')
            log_lines.append(f'<div class="log-line log-info">▶ Processing: {name_en}</div>')

            articles_by_lang = {}

            progress_bar.progress((ki * 4 + 1) / (total * 4), text=f"{name_en}: fetching English articles…")
            articles_by_lang["en"] = fetch_all_articles_for_window(name_en, "en", from_date, to_date, start_dt, end_dt, log_lines)

            progress_bar.progress((ki * 4 + 2) / (total * 4), text=f"{name_en}: fetching Telugu articles…")
            if name_te:
                articles_by_lang["te"] = fetch_all_articles_for_window(name_te, "te", from_date, to_date, start_dt, end_dt, log_lines)

            progress_bar.progress((ki * 4 + 3) / (total * 4), text=f"{name_en}: fetching Hindi articles…")
            if name_hi:
                articles_by_lang["hi"] = fetch_all_articles_for_window(name_hi, "hi", from_date, to_date, start_dt, end_dt, log_lines)

            progress_bar.progress((ki * 4 + 4) / (total * 4), text=f"{name_en}: fetching YouTube videos…")
            yt_videos = []
            if yt_api_key:
                yt_videos = fetch_all_youtube_videos(name_en, yt_api_key, start_dt, end_dt, log_lines)
            else:
                log_lines.append('<div class="log-line log-err">  [YT] YOUTUBE_API_KEY not set in .env — skipping YouTube</div>')

            excel_bytes = build_excel(name_en, date_str, articles_by_lang, yt_videos)

            results.append({
                "name":     name_en,
                "excel":    excel_bytes,
                "filename": f"{name_en}_report_{file_date_suffix}.xlsx",
                "total_en": len(articles_by_lang.get("en", [])),
                "total_te": len(articles_by_lang.get("te", [])),
                "total_hi": len(articles_by_lang.get("hi", [])),
                "total_yt": len(yt_videos),
            })

        progress_bar.progress(1.0, text="✅ All reports generated!")
        st.session_state.results  = results
        st.session_state.log_html = "".join(log_lines)

# ============================================================
# RESULTS
# ============================================================
if st.session_state.results:
    st.markdown("---")
    st.markdown("## 📦 Generated Reports")

    for res in st.session_state.results:
        st.markdown(f"""
        <div class="keyword-card">
            <strong style="font-size:1.05rem; color:#11141c;">{res['name']}</strong><br/>
            <span class="stat-chip en">🌐 EN: {res['total_en']}</span>
            <span class="stat-chip te">🔤 TE: {res['total_te']}</span>
            <span class="stat-chip hi">🔤 HI: {res['total_hi']}</span>
            <span class="stat-chip yt">▶️ YT: {res['total_yt']}</span>
        </div>
        """, unsafe_allow_html=True)

        st.download_button(
            label=f"⬇️ Download  {res['name']}  Report (.xlsx)",
            data=res["excel"],
            file_name=res["filename"],
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_{res['name']}",
        )

# ============================================================
# LOG
# ============================================================
if st.session_state.log_html:
    st.markdown("---")
    st.markdown("### 🔍 Fetch Log")
    st.markdown(f'<div class="log-container">{st.session_state.log_html}</div>', unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style="text-align:center;color:#9ca3af;font-size:0.78rem;margin-top:4rem;
            padding-top:1.5rem;border-top:1px solid #e5e7eb;">
    Daily News Report Generator · Powered by GNews &amp; YouTube Data API v3
</div>
""", unsafe_allow_html=True)