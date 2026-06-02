import streamlit as st
import anthropic
import json
import time
from datetime import date

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OptSpot — Campaign Generator",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* Hide Streamlit chrome so header isn't cut off */
header[data-testid="stHeader"] { display: none !important; }
#MainMenu, footer, .stDeployButton { display: none !important; }
.block-container { padding-top: 0.75rem !important; padding-bottom: 3rem; max-width: 820px; }
/* Tighten tabs */
div[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 4px; }
/* Month nav button sizing */
div[data-testid="stHorizontalBlock"] .stButton button { font-size: 12px !important; padding: 4px 6px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────
QUARTERS = {
    "Q1": {
        "months": ["jan", "feb", "mar"],
        "label": "Q1 — January · February · March",
        "theme": "New Year · Valentine's · Early Pollen",
        "suggested": "Reset & Renew — start the year clean, dust off the old.",
    },
    "Q2": {
        "months": ["apr", "may", "jun"],
        "label": "Q2 — April · May · June",
        "theme": "Peak Pollen · Mother's Day · Memorial Day · Father's Day",
        "suggested": "Get Ready for the Road — pollen, gifts for Mom and Dad, summer kickoff.",
    },
    "Q3": {
        "months": ["jul", "aug", "sep"],
        "label": "Q3 — July · August · September",
        "theme": "Independence Day · Summer Heat · Back to School",
        "suggested": "Beat the Heat — busy families, big weekends, kids on the move.",
    },
    "Q4": {
        "months": ["oct", "nov", "dec"],
        "label": "Q4 — October · November · December",
        "theme": "Halloween · Thanksgiving · Black Friday · Christmas",
        "suggested": "Give the Gift of Clean — gifting season, year-end push.",
    },
}

MONTHS = {
    "jan": {"name": "January",   "short": "Jan", "q": "Q1", "holidays": "New Year's Day (1/1), MLK Day (3rd Monday)",                        "seasonal": "Fresh start, resolutions, dust off the holidays",             "def": "Fresh-start membership push. 'Start the year with a clean car every week.' Bundle with a small retail item."},
    "feb": {"name": "February",  "short": "Feb", "q": "Q1", "holidays": "Valentine's Day (2/14), Presidents' Day",                            "seasonal": "Gifting, couples and family, last of the winter grit",        "def": "Gift-a-membership Valentine's promo. Two-pack of single washes for couples — 'give the gift of clean.'"},
    "mar": {"name": "March",     "short": "Mar", "q": "Q1", "holidays": "St. Patrick's Day (3/17), Daylight Saving, first day of spring",     "seasonal": "Spring cleaning, pollen begins, spring break",                "def": "Spring cleaning combo — wash with an interior detail add-on. Tie it to 'spring forward, drive cleaner.'"},
    "apr": {"name": "April",     "short": "Apr", "q": "Q2", "holidays": "Easter (varies), Earth Day (4/22), Tax Day (4/15)",                  "seasonal": "Peak pollen, full spring, sustainable wash messaging",         "def": "Pollen season: lean hard into weekly membership. 'We'll keep it clean for you — automatically.'"},
    "may": {"name": "May",       "short": "May", "q": "Q2", "holidays": "Mother's Day (2nd Sunday), Memorial Day (last Monday)",              "seasonal": "Mom, summer kickoff, road-trip prep",                          "def": "Mother's Day gift wash + Memorial Day weekend road-trip promo. Two clean asks back to back."},
    "jun": {"name": "June",      "short": "Jun", "q": "Q2", "holidays": "Father's Day (3rd Sunday), Juneteenth (6/19)",                       "seasonal": "Dad, summer is here, vacation prep",                           "def": "Father's Day gift bundle. Mid-month: 'vacation-ready' detail or full-service upsell."},
    "jul": {"name": "July",      "short": "Jul", "q": "Q3", "holidays": "Independence Day (7/4)",                                              "seasonal": "Summer heat, family travel, busy weekends",                   "def": "4th of July weekend push — red/white/blue creative. Mid-month: heat-of-summer member appreciation."},
    "aug": {"name": "August",    "short": "Aug", "q": "Q3", "holidays": "Back-to-school (dates vary by region)",                               "seasonal": "Carpool clean, busy parents, end of summer",                 "def": "Back-to-school bundle for busy parents. 'One less thing on your list — let us handle the car.'"},
    "sep": {"name": "September", "short": "Sep", "q": "Q3", "holidays": "Labor Day (1st Monday)",                                             "seasonal": "Settling into school routine, fall preview, last of summer", "def": "Labor Day weekend promo. Mid-month: fall preview offer or a member-only thank-you wash."},
    "oct": {"name": "October",   "short": "Oct", "q": "Q4", "holidays": "Halloween (10/31), Columbus/Indigenous Peoples' Day",                "seasonal": "Fall, costumes, pre-winter detail push",                       "def": "Halloween-themed promo with a kid-friendly tie-in. Pre-winter detail or undercarriage offer late in the month."},
    "nov": {"name": "November",  "short": "Nov", "q": "Q4", "holidays": "Veterans Day (11/11), Thanksgiving (4th Thursday), Black Friday",    "seasonal": "Gratitude, gifting kickoff, holiday travel",                  "def": "Gifting season opens. Black Friday membership doorbuster — annual prepay at the year's best price."},
    "dec": {"name": "December",  "short": "Dec", "q": "Q4", "holidays": "Christmas (12/25), New Year's Eve (12/31)",                          "seasonal": "Gift cards as gifts, year-end push, holiday road trips",     "def": "Gift cards and gift memberships front and center. Year-end 'come wash before the new year' nudge in the final week."},
}

ALL_MONTHS = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]

DEMO_OUTPUT = {
    "textClub": [
        {"label": "Send #1 — May 1 (Campaign Launch)",  "text": "Hey! Mother's Day is coming 💐 Give Mom a clean car she'll love. Buy 1 wash, get 1 FREE now through May 11.\nGet yours → sparklecarwash.com/mom\n\nReply STOP to opt out.", "chars": 158},
        {"label": "Send #2 — May 10 (Last Chance)",     "text": "Tomorrow is Mother's Day 💐 Last chance for a BOGO wash for Mom. She'll use it more than flowers.\nGo → sparklecarwash.com/mom\n\nReply STOP to opt out.", "chars": 153},
    ],
    "social": [
        {"label": "Post #1 — Facebook / Instagram (Heartfelt)",    "text": "Mom does a lot. The least we can do is make sure she's driving clean. 💐\n\nThis Mother's Day, buy 1 wash and get 1 FREE for her. Valid May 1–11 at Sparkle Car Wash.", "tags": "#MothersDay #CarWash #GiftIdeas #TulsaLocal #SparkleMom"},
        {"label": "Post #2 — Instagram / TikTok (Fun & Relatable)", "text": "Flowers wilt. Chocolate disappears. A clean car? That lasts all week. 🚗✨\n\nBOGO washes for Mom — May 1–11 only. Link in bio.", "tags": "#MothersDay #CarWashMom #TreatMom #BogoWash #SparkleCarWash"},
        {"label": "Post #3 — Facebook (Direct / Offer-First)",      "text": "Mother's Day special at Sparkle Car Wash: Buy 1 wash, get 1 FREE.\n\nPerfect for Mom, Grandma, or yourself. Grab it in person or online at sparklecarwash.com/mom — offer ends May 11.", "tags": "#SparkleTulsa #MothersDay2026 #CarWash #TulsaDeals"},
    ],
    "onsite": [
        {"label": "Counter Display / POS Sign", "headline": "Give Mom the Gift of Clean.", "sub": "Buy 1 wash, get 1 FREE for her.\nNow through May 11 — ask us at checkout."},
        {"label": "Vacuum Bay Signage",         "headline": "Happy Mother's Day! 🌸",      "sub": "BOGO washes through May 11.\nGift one to Mom at sparklecarwash.com/mom"},
    ],
    "team": [
        "At checkout, let every customer know: \"We're doing a Mother's Day special right now — buy one wash and get one free to give to Mom. Want me to add it on for you?\"",
        "For existing members, say: \"Your membership auto-renews so you're covered, but if you want to gift Mom a wash separately, we have a BOGO deal running through Mother's Day.\"",
        "If someone hesitates: \"Honestly it's the easiest gift — she'll use it and it only takes 10 minutes. The deal ends May 11 so today's a good day to grab it.\"",
    ],
}


# ─────────────────────────────────────────────────────────────
# API KEY
# ─────────────────────────────────────────────────────────────
try:
    API_KEY = st.secrets["ANTHROPIC_API_KEY"]
    is_live = bool(API_KEY)
except Exception:
    API_KEY = None
    is_live = False


# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
DEFAULTS = {
    "view":             "setup",   # setup | planning | output
    "wash_name":        "",
    "mode":             "",        # year | Q1 | Q2 | Q3 | Q4 | month
    "quarter_idea":     {},        # {Q1: "...", Q2: "..."} per-quarter controlling ideas
    "months_in_scope":  [],
    "current_month":    "",
    "month_data":       {},        # {key: {theme, offer, link, instructions, start_date, end_date, notes}}
    "month_outputs":    {},        # {key: output_dict}
    "output_month_sel": "",        # which month is selected in output view
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

s = st.session_state


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def month_status(key):
    if key in s.month_outputs:
        return "✨"
    if s.month_data.get(key, {}).get("theme"):
        return "💾"
    return "○"


def build_prompt(month_key, data):
    m  = MONTHS[month_key]
    q  = m["q"]
    qi = s.quarter_idea.get(q, "")
    return f"""You are a marketing copywriter for a car wash business. Generate campaign content for all 4 channels.

CAR WASH: {s.wash_name}
MONTH: {m['name']}
HOLIDAYS: {m['holidays']}
SEASONAL CONTEXT: {m['seasonal']}
{f"QUARTER CONTROLLING IDEA: {qi}" if qi else ""}
CAMPAIGN THEME: {data.get('theme','')}
OFFER: {data.get('offer','')}
LINK: {data.get('link','')}
CUSTOMER INSTRUCTIONS: {data.get('instructions','')}
CAMPAIGN DATES: {data.get('start_date','')} to {data.get('end_date','')}
{f"ADDITIONAL NOTES: {data.get('notes','')}" if data.get('notes') else ""}

Return ONLY valid JSON in this exact structure (no markdown, no extra text):
{{
  "textClub": [
    {{"label":"Send #1 — [date/occasion]","text":"[SMS text including opt-out line, under 160 chars total]","chars":[number]}},
    {{"label":"Send #2 — [date/occasion]","text":"[SMS text including opt-out line, under 160 chars total]","chars":[number]}}
  ],
  "social": [
    {{"label":"Post #1 — [platform (Tone)]","text":"[post copy]","tags":"[hashtags]"}},
    {{"label":"Post #2 — [platform (Tone)]","text":"[post copy]","tags":"[hashtags]"}},
    {{"label":"Post #3 — [platform (Tone)]","text":"[post copy]","tags":"[hashtags]"}}
  ],
  "onsite": [
    {{"label":"Counter Display / POS Sign","headline":"[bold short headline]","sub":"[2-3 lines supporting copy]"}},
    {{"label":"Vacuum Bay Signage","headline":"[very short headline]","sub":"[1-2 lines]"}}
  ],
  "team": [
    "[Full talking point #1 — word-for-word what a CSA says at checkout]",
    "[Full talking point #2 — for existing members]",
    "[Full talking point #3 — for hesitant customers]"
  ]
}}

Rules:
- Each SMS must be under 160 characters total including the opt-out line. Count carefully.
- Copy should be direct, friendly, action-oriented. Car wash customers respond to urgency and value.
- Use the car wash name naturally.
- Talking points must be conversational — literally what someone says out loud."""


def call_api(month_key, data):
    if not is_live:
        time.sleep(0.4)
        return DEMO_OUTPUT
    prompt  = build_prompt(month_key, data)
    client  = anthropic.Anthropic(api_key=API_KEY)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────
# SHARED COMPONENTS
# ─────────────────────────────────────────────────────────────
def render_header():
    hc1, hc2 = st.columns([5, 1])
    with hc1:
        st.markdown("""
        <div style="background:#1a3a6c;padding:14px 22px;border-radius:10px;margin-bottom:6px;">
          <span style="font-size:16px;font-weight:900;letter-spacing:0.07em;color:#f97316;">OPTSPOT</span>
          <span style="color:rgba(255,255,255,0.25);font-size:18px;margin:0 10px;">|</span>
          <span style="font-size:14px;font-weight:600;color:white;">12-Month Campaign Generator</span>
        </div>""", unsafe_allow_html=True)
    with hc2:
        if is_live:
            st.markdown("<div style='padding-top:10px;text-align:right;'><span style='background:#dcfce7;color:#15803d;font-size:12px;font-weight:700;padding:6px 12px;border-radius:20px;'>✅ Live</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding-top:10px;text-align:right;'><span style='background:#fef3c7;color:#92400e;font-size:12px;font-weight:700;padding:6px 12px;border-radius:20px;'>⚠ Demo</span></div>", unsafe_allow_html=True)

    if not is_live:
        st.warning("**Demo Mode** — Add `ANTHROPIC_API_KEY` in Streamlit Cloud → Settings → Secrets to generate live content.")


def render_channels(output):
    """Render the 4-channel tabs for a given output dict."""
    t1, t2, t3, t4 = st.tabs(["📱  Text Club", "📸  Social", "🪧  Signage", "🗣️  Team"])

    with t1:
        for msg in output["textClub"]:
            st.markdown(f"**{msg['label']}**")
            c = msg["chars"]
            clr = "#16a34a" if c <= 140 else "#d97706" if c <= 160 else "#dc2626"
            ico = "✓" if c <= 140 else "⚠" if c <= 160 else "✗"
            st.markdown(f"<small style='color:{clr};'>{ico} {c} chars</small>", unsafe_allow_html=True)
            st.code(msg["text"], language=None)
            st.markdown("")

    with t2:
        for post in output["social"]:
            st.markdown(f"**{post['label']}**")
            st.code(f"{post['text']}\n\n{post['tags']}", language=None)
            st.markdown("")

    with t3:
        for sign in output["onsite"]:
            st.markdown(f"**{sign['label']}**")
            st.markdown(
                f"<div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;"
                f"padding:14px 16px;margin:6px 0 8px;'>"
                f"<div style='font-size:20px;font-weight:900;color:#0f172a;margin-bottom:4px;'>{sign['headline']}</div>"
                f"<div style='font-size:14px;color:#64748b;'>{sign['sub'].replace(chr(10),'<br>')}</div>"
                f"</div>", unsafe_allow_html=True
            )
            st.code(f"{sign['headline']}\n{sign['sub']}", language=None)
            st.markdown("")

    with t4:
        for i, tp in enumerate(output["team"], 1):
            st.markdown(
                f"<div style='display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #e2e8f0;'>"
                f"<div style='width:26px;height:26px;border-radius:50%;background:#f3e8ff;color:#7e22ce;"
                f"font-size:12px;font-weight:800;display:flex;align-items:center;justify-content:center;"
                f"flex-shrink:0;'>{i}</div>"
                f"<div style='font-size:14px;line-height:1.65;'>{tp}</div>"
                f"</div>", unsafe_allow_html=True
            )
        st.markdown("")
        st.markdown("**Copy all talking points:**")
        st.code("\n\n".join([f"{i+1}. {tp}" for i, tp in enumerate(output["team"])]), language=None)


# ─────────────────────────────────────────────────────────────
# VIEW: SETUP
# ─────────────────────────────────────────────────────────────
def view_setup():
    render_header()
    st.markdown("### Plan Setup")
    st.caption("Tell us who you're planning for and how much of the year to cover.")

    wash_name = st.text_input(
        "Car Wash Name",
        value=s.wash_name,
        placeholder="e.g. Sparkle Car Wash – Tulsa"
    )

    st.markdown("**Planning Scope**")
    mode_opts = {
        "year":  "📅  Full Year (all 12 months)",
        "Q1":    "Q1 — January · February · March",
        "Q2":    "Q2 — April · May · June",
        "Q3":    "Q3 — July · August · September",
        "Q4":    "Q4 — October · November · December",
        "month": "📌  Single Month",
    }
    mode = st.radio(
        "Scope",
        options=list(mode_opts.keys()),
        format_func=lambda x: mode_opts[x],
        index=list(mode_opts.keys()).index(s.mode) if s.mode in mode_opts else 0,
        label_visibility="collapsed"
    )

    # Quarter controlling idea
    quarter_ideas = dict(s.quarter_idea)  # local copy
    if mode in QUARTERS:
        q = QUARTERS[mode]
        st.info(
            f"**{q['label']}**  \n"
            f"*{q['theme']}*  \n\n"
            f"💡 Suggested controlling idea: _{q['suggested']}_"
        )
        qi = st.text_input(
            "Controlling Idea for the Quarter",
            value=quarter_ideas.get(mode, q["suggested"]),
            placeholder=q["suggested"]
        )
        quarter_ideas[mode] = qi

    # For full year — show all 4 quarter ideas
    if mode == "year":
        with st.expander("📋 Set controlling ideas per quarter (optional but recommended)"):
            for qk, qv in QUARTERS.items():
                qi = st.text_input(
                    f"{qv['label']}",
                    value=quarter_ideas.get(qk, qv["suggested"]),
                    placeholder=qv["suggested"],
                    key=f"qi_{qk}"
                )
                quarter_ideas[qk] = qi

    # Single month picker
    single_month = ""
    if mode == "month":
        month_opts = {"": "— Select a month —"} | {k: v["name"] for k, v in MONTHS.items()}
        single_month = st.selectbox(
            "Which Month?",
            options=list(month_opts.keys()),
            format_func=lambda x: month_opts[x],
            index=list(month_opts.keys()).index(s.months_in_scope[0]) if (s.months_in_scope and s.mode == "month") else 0
        )

    st.markdown("")
    if st.button("Start Planning →", type="primary", use_container_width=True):
        if not wash_name.strip():
            st.error("Please enter the car wash name."); return
        if mode == "month" and not single_month:
            st.error("Please select a month."); return

        s.wash_name    = wash_name
        s.mode         = mode
        s.quarter_idea = quarter_ideas

        if mode == "year":
            s.months_in_scope = ALL_MONTHS[:]
        elif mode in QUARTERS:
            s.months_in_scope = QUARTERS[mode]["months"][:]
        else:
            s.months_in_scope = [single_month]

        # Keep existing month data if re-entering setup; set current to first
        if not s.current_month or s.current_month not in s.months_in_scope:
            s.current_month = s.months_in_scope[0]

        s.view = "planning"
        st.rerun()


# ─────────────────────────────────────────────────────────────
# VIEW: PLANNING
# ─────────────────────────────────────────────────────────────
def view_planning():
    render_header()

    # ── Header bar ──
    hb1, hb2 = st.columns([4, 1])
    with hb1:
        scope_label = {"year": "Full Year", "month": "Single Month"}.get(s.mode, s.mode)
        st.markdown(f"**{s.wash_name}** · {scope_label}")
    with hb2:
        if st.button("⚙ Setup", use_container_width=True):
            s.view = "setup"; st.rerun()

    # ── Month navigator ──
    n    = len(s.months_in_scope)
    cols = st.columns(n)
    for i, key in enumerate(s.months_in_scope):
        with cols[i]:
            status    = month_status(key)
            is_active = (key == s.current_month)
            if st.button(
                f"{MONTHS[key]['short']}\n{status}",
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                # Auto-save current form before navigating (form already written to state)
                s.current_month = key
                st.rerun()

    st.markdown("---")

    mk = s.current_month
    m  = MONTHS[mk]

    # Quarter idea banner (if applicable)
    q  = m["q"]
    qi = s.quarter_idea.get(q, "")
    if qi and s.mode != "month":
        st.markdown(
            f"<div style='background:#eff6ff;border-left:3px solid #2952a3;padding:8px 14px;"
            f"border-radius:0 6px 6px 0;font-size:13px;color:#1e40af;margin-bottom:12px;'>"
            f"<strong>{q} Controlling Idea:</strong> {qi}</div>",
            unsafe_allow_html=True
        )

    st.markdown(f"### {m['name']}")
    st.info(
        f"**🗓 Holidays:** {m['holidays']}  \n"
        f"**🌿 Seasonal:** {m['seasonal']}  \n"
        f"**💡 Default move:** {m['def']}"
    )

    saved = s.month_data.get(mk, {})

    theme        = st.text_input("Theme — the controlling idea",               value=saved.get("theme",""),        placeholder="e.g. Give Mom the Gift of Clean")
    offer        = st.text_input("Offer — what the customer gets",             value=saved.get("offer",""),        placeholder="e.g. Buy 1 wash, get 1 FREE")
    link         = st.text_input("Link — landing page or redemption URL",      value=saved.get("link",""),         placeholder="e.g. https://yourwash.com/promo")
    instructions = st.text_input("Customer Instructions — what they do, one line", value=saved.get("instructions",""), placeholder="e.g. Show this text at the kiosk")

    dc1, dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input("Start Date", value=saved.get("start_date") or date.today())
    with dc2:
        end_date   = st.date_input("End Date",   value=saved.get("end_date")   or date.today())

    notes = st.text_area(
        "Additional Notes (optional)",
        value=saved.get("notes",""),
        placeholder="e.g. Tunnel wash, member raffle, local event tie-in.",
        height=80
    )

    def collect():
        return {"theme": theme, "offer": offer, "link": link,
                "instructions": instructions, "start_date": start_date,
                "end_date": end_date, "notes": notes}

    def validate():
        missing = [f for f, v in [("Theme",theme),("Offer",offer),("Link",link),("Instructions",instructions)] if not str(v).strip()]
        if missing:
            st.error(f"Please fill in: {', '.join(missing)}"); return False
        if end_date < start_date:
            st.error("End date must be after start date."); return False
        return True

    st.markdown("")

    # ── Action buttons ──
    ac1, ac2, ac3 = st.columns(3)

    with ac1:
        if st.button("💾 Save Month", use_container_width=True):
            s.month_data[mk] = collect()
            st.success(f"{m['name']} saved!")

    with ac2:
        gen_label = "✨ Re-generate" if mk in s.month_outputs else "✨ Generate This Month"
        if st.button(gen_label, type="primary", use_container_width=True):
            if validate():
                s.month_data[mk] = collect()
                with st.spinner(f"Generating {m['name']} content…"):
                    try:
                        output = call_api(mk, s.month_data[mk])
                        s.month_outputs[mk]  = output
                        s.output_month_sel   = mk
                        s.view               = "output"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

    with ac3:
        ready = [k for k in s.months_in_scope if s.month_data.get(k, {}).get("theme")]
        all_label = f"🚀 Generate All ({len(ready)})" if ready else "🚀 Generate All"
        if st.button(all_label, use_container_width=True, disabled=not ready):
            # Save current form first
            s.month_data[mk] = collect()
            to_run = [k for k in s.months_in_scope if s.month_data.get(k, {}).get("theme")]
            if not to_run:
                st.error("Save at least one month first.")
            else:
                prog = st.progress(0, text="Starting…")
                failed = []
                for i, key in enumerate(to_run):
                    prog.progress((i) / len(to_run), text=f"Generating {MONTHS[key]['name']}…")
                    try:
                        s.month_outputs[key] = call_api(key, s.month_data[key])
                    except Exception as e:
                        failed.append(f"{MONTHS[key]['name']}: {e}")
                prog.progress(1.0, text="Done!")
                if failed:
                    st.error("Some months failed:\n" + "\n".join(failed))
                s.output_month_sel = to_run[0]
                s.view = "output"
                st.rerun()

    # ── Prev / Next ──
    st.markdown("")
    idx    = s.months_in_scope.index(mk)
    nc1, _, nc2 = st.columns([1, 3, 1])
    with nc1:
        if idx > 0:
            prev = s.months_in_scope[idx - 1]
            if st.button(f"← {MONTHS[prev]['short']}", use_container_width=True):
                s.month_data[mk] = collect()   # auto-save on navigate
                s.current_month  = prev
                st.rerun()
    with nc2:
        if idx < len(s.months_in_scope) - 1:
            nxt = s.months_in_scope[idx + 1]
            if st.button(f"{MONTHS[nxt]['short']} →", use_container_width=True):
                s.month_data[mk] = collect()   # auto-save on navigate
                s.current_month  = nxt
                st.rerun()

    # ── Inline output preview (if already generated) ──
    if mk in s.month_outputs:
        st.markdown("---")
        with st.expander(f"📋 View generated content for {m['name']}", expanded=False):
            render_channels(s.month_outputs[mk])
            if st.button("Open full output view →", key=f"goto_out_{mk}"):
                s.output_month_sel = mk
                s.view = "output"
                st.rerun()


# ─────────────────────────────────────────────────────────────
# VIEW: OUTPUT
# ─────────────────────────────────────────────────────────────
def view_output():
    render_header()

    oc1, oc2 = st.columns([1, 4])
    with oc1:
        if st.button("← Edit"):
            s.view = "planning"; st.rerun()

    generated = [k for k in s.months_in_scope if k in s.month_outputs]
    if not generated:
        st.info("No content generated yet. Go back and generate a month.")
        return

    st.markdown("### Generated Content")
    total = len(generated)
    remaining = len([k for k in s.months_in_scope if k not in s.month_outputs and s.month_data.get(k,{}).get("theme")])
    caption = f"{s.wash_name} · {total} month{'s' if total != 1 else ''} generated"
    if remaining:
        caption += f" · {remaining} more saved and ready to generate"
    st.caption(caption)

    if not is_live:
        st.warning("⚠ **Demo output** — Add `ANTHROPIC_API_KEY` in Streamlit Cloud secrets for live content.")

    # ── Month selector ──
    if len(generated) > 1:
        # Group by quarter for display
        current_sel = st.radio(
            "Month",
            options=generated,
            format_func=lambda x: MONTHS[x]["name"],
            index=generated.index(s.output_month_sel) if s.output_month_sel in generated else 0,
            horizontal=True
        )
        s.output_month_sel = current_sel
    else:
        s.output_month_sel = generated[0]

    sel = s.output_month_sel
    m   = MONTHS[sel]

    # Quarter badge
    q   = m["q"]
    qi  = s.quarter_idea.get(q, "")
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin:8px 0 4px;'>"
        f"<span style='background:#1a3a6c;color:white;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;'>{m['name']}</span>"
        f"<span style='background:#f1f5f9;color:#64748b;padding:4px 10px;border-radius:20px;font-size:12px;'>{q}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
    if qi:
        st.markdown(f"<small style='color:#94a3b8;'>Quarter idea: {qi}</small>", unsafe_allow_html=True)

    st.markdown("")
    render_channels(s.month_outputs[sel])

    # Generate remaining
    if remaining:
        st.markdown("---")
        if st.button(f"🚀 Generate {remaining} remaining saved month{'s' if remaining != 1 else ''}", type="primary"):
            to_run = [k for k in s.months_in_scope if k not in s.month_outputs and s.month_data.get(k,{}).get("theme")]
            prog = st.progress(0)
            for i, key in enumerate(to_run):
                prog.progress(i / len(to_run), text=f"Generating {MONTHS[key]['name']}…")
                try:
                    s.month_outputs[key] = call_api(key, s.month_data[key])
                except Exception as e:
                    st.error(f"{MONTHS[key]['name']}: {e}")
            prog.progress(1.0, text="Done!")
            st.rerun()

    st.markdown("---")
    if st.button("Start Over"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ─────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────
if s.view == "setup":
    view_setup()
elif s.view == "planning":
    view_planning()
elif s.view == "output":
    view_output()
