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

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 780px; }
/* Tighten tab spacing */
div[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 4px; }
/* Code block — reduce padding */
.stCodeBlock { margin-top: 4px; }
/* Step indicator */
.step-wrap { text-align: center; padding: 8px 4px; font-size: 13px; }
.step-active  { color: #1a3a6c; font-weight: 700; border-bottom: 2px solid #1a3a6c; }
.step-done    { color: #16a34a; font-weight: 600; }
.step-pending { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────
MONTHS = {
    "jan": {"name": "January",   "holidays": "New Year's Day (1/1), MLK Day (3rd Monday)",                        "seasonal": "Fresh start, resolutions, dust off the holidays",              "def": "Reset & Renew — fresh-start membership push"},
    "feb": {"name": "February",  "holidays": "Valentine's Day (2/14), Presidents' Day",                            "seasonal": "Gifting, couples and family, last of the winter grit",         "def": "Gift-a-membership Valentine's promo — two-pack for couples"},
    "mar": {"name": "March",     "holidays": "St. Patrick's Day (3/17), Daylight Saving, first day of spring",     "seasonal": "Spring cleaning, pollen begins, spring break",                 "def": "Spring cleaning combo — wash + interior detail add-on"},
    "apr": {"name": "April",     "holidays": "Easter (varies), Earth Day (4/22), Tax Day (4/15)",                  "seasonal": "Peak pollen, full spring, sustainable wash messaging",          "def": "Pollen season membership push"},
    "may": {"name": "May",       "holidays": "Mother's Day (2nd Sunday), Memorial Day (last Monday)",              "seasonal": "Mom, summer kickoff, road-trip prep",                           "def": "Mother's Day gift wash + Memorial Day road-trip promo"},
    "jun": {"name": "June",      "holidays": "Father's Day (3rd Sunday), Juneteenth (6/19)",                       "seasonal": "Dad, summer is here, vacation prep",                            "def": "Father's Day gift bundle + vacation-ready upsell"},
    "jul": {"name": "July",      "holidays": "Independence Day (7/4)",                                              "seasonal": "Summer heat, family travel, busy weekends",                    "def": "4th of July push + summer member appreciation"},
    "aug": {"name": "August",    "holidays": "Back-to-school (dates vary by region)",                               "seasonal": "Carpool clean, busy parents, end of summer",                  "def": "Back-to-school bundle — 'One less thing on your list'"},
    "sep": {"name": "September", "holidays": "Labor Day (1st Monday)",                                             "seasonal": "Settling into school routine, fall preview, last of summer",  "def": "Labor Day weekend promo + fall preview member offer"},
    "oct": {"name": "October",   "holidays": "Halloween (10/31), Columbus/Indigenous Peoples' Day",                "seasonal": "Fall, costumes, pre-winter detail push",                        "def": "Halloween promo + pre-winter detail/undercarriage offer"},
    "nov": {"name": "November",  "holidays": "Veterans Day (11/11), Thanksgiving (4th Thursday), Black Friday",    "seasonal": "Gratitude, gifting kickoff, holiday travel",                   "def": "Black Friday membership doorbuster — annual prepay"},
    "dec": {"name": "December",  "holidays": "Christmas (12/25), New Year's Eve (12/31)",                          "seasonal": "Gift cards as gifts, year-end push, holiday road trips",      "def": "Gift cards and memberships + year-end clean nudge"},
}

MONTH_OPTIONS = {"": "— Select a month —"} | {k: v["name"] for k, v in MONTHS.items()}

DEMO_OUTPUT = {
    "textClub": [
        {
            "label": "Send #1 — May 1 (Campaign Launch)",
            "text": "Hey! Mother's Day is coming 💐 Give Mom a clean car she'll love. Buy 1 wash, get 1 FREE now through May 11.\nGet yours → sparklecarwash.com/mom\n\nReply STOP to opt out.",
            "chars": 158
        },
        {
            "label": "Send #2 — May 10 (Last Chance)",
            "text": "Tomorrow is Mother's Day 💐 Last chance for a BOGO wash for Mom. She'll use it more than flowers.\nGo → sparklecarwash.com/mom\n\nReply STOP to opt out.",
            "chars": 153
        }
    ],
    "social": [
        {
            "label": "Post #1 — Facebook / Instagram (Heartfelt)",
            "text": "Mom does a lot. The least we can do is make sure she's driving clean. 💐\n\nThis Mother's Day, buy 1 wash and get 1 FREE for her. Valid May 1–11 at Sparkle Car Wash.",
            "tags": "#MothersDay #CarWash #GiftIdeas #TulsaLocal #SparkleMom"
        },
        {
            "label": "Post #2 — Instagram / TikTok (Fun & Relatable)",
            "text": "Flowers wilt. Chocolate disappears. A clean car? That lasts all week. 🚗✨\n\nBOGO washes for Mom — May 1–11 only. Link in bio.",
            "tags": "#MothersDay #CarWashMom #TreatMom #BogoWash #SparkleCarWash"
        },
        {
            "label": "Post #3 — Facebook (Direct / Offer-First)",
            "text": "Mother's Day special at Sparkle Car Wash: Buy 1 wash, get 1 FREE.\n\nPerfect for Mom, Grandma, or yourself. Grab it in person or online at sparklecarwash.com/mom — offer ends May 11.",
            "tags": "#SparkleTulsa #MothersDay2026 #CarWash #TulsaDeals"
        }
    ],
    "onsite": [
        {
            "label": "Counter Display / POS Sign",
            "headline": "Give Mom the Gift of Clean.",
            "sub": "Buy 1 wash, get 1 FREE for her.\nNow through May 11 — ask us at checkout."
        },
        {
            "label": "Vacuum Bay Signage",
            "headline": "Happy Mother's Day! 🌸",
            "sub": "BOGO washes through May 11.\nGift one to Mom at sparklecarwash.com/mom"
        }
    ],
    "team": [
        "At checkout, let every customer know: \"We're doing a Mother's Day special right now — buy one wash and get one free to give to Mom. Want me to add it on for you?\"",
        "For existing members, say: \"Your membership auto-renews so you're covered, but if you want to gift Mom a wash separately, we have a BOGO deal running through Mother's Day.\"",
        "If someone hesitates: \"Honestly it's the easiest gift — she'll use it and it only takes 10 minutes. The deal ends May 11 so today's a good day to grab it.\""
    ]
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def build_prompt(s, m):
    return f"""You are a marketing copywriter for a car wash business. Generate campaign content for all 4 channels.

CAR WASH: {s.wash_name}
MONTH: {m['name']}
HOLIDAYS: {m['holidays']}
SEASONAL CONTEXT: {m['seasonal']}
THEME: {s.theme}
OFFER: {s.offer}
LINK: {s.link}
CUSTOMER INSTRUCTIONS: {s.instructions}
CAMPAIGN DATES: {s.start_date} to {s.end_date}
{f"ADDITIONAL NOTES: {s.notes}" if s.notes else ""}

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
- Use the car wash name naturally — don't make it sound generic.
- Talking points must be conversational — literally what someone says out loud."""


def step_html(label, num, state):
    styles = {
        "active":  "color:#1a3a6c;font-weight:700;border-bottom:2px solid #1a3a6c;padding-bottom:4px;",
        "done":    "color:#16a34a;font-weight:600;",
        "pending": "color:#94a3b8;"
    }
    prefix = "✓" if state == "done" else str(num)
    return f"<div class='step-wrap'><span style='{styles[state]}'>{prefix}. {label}</span></div>"


# ─────────────────────────────────────────────────────────────
# API KEY CHECK
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
defaults = {
    "step":         1,
    "wash_name":    "",
    "month":        "",
    "theme":        "",
    "offer":        "",
    "link":         "",
    "instructions": "",
    "start_date":   None,
    "end_date":     None,
    "notes":        "",
    "output":       None,
    "is_demo":      False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([5, 1])
with hc1:
    st.markdown("""
    <div style="background:#1a3a6c;padding:14px 22px;border-radius:10px;margin-bottom:6px;">
      <span style="font-size:16px;font-weight:900;letter-spacing:0.07em;color:#f97316;">OPTSPOT</span>
      <span style="color:rgba(255,255,255,0.25);font-size:18px;margin:0 10px;">|</span>
      <span style="font-size:14px;font-weight:600;color:white;">12-Month Campaign Generator</span>
    </div>
    """, unsafe_allow_html=True)
with hc2:
    badge_style = "background:#dcfce7;color:#15803d;" if is_live else "background:#fef3c7;color:#92400e;"
    badge_text  = "✅ Live" if is_live else "⚠ Demo"
    st.markdown(
        f"<div style='padding-top:10px;text-align:right;'>"
        f"<span style='{badge_style}font-size:12px;font-weight:700;padding:6px 12px;border-radius:20px;'>{badge_text}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

if not is_live:
    st.warning(
        "**Demo Mode** — No `ANTHROPIC_API_KEY` found. Output uses hardcoded examples.  \n"
        "To go live: Streamlit Cloud → your app → **Settings → Secrets** → add `ANTHROPIC_API_KEY = \"sk-ant-...\"`"
    )


# ─────────────────────────────────────────────────────────────
# PROGRESS INDICATOR
# ─────────────────────────────────────────────────────────────
step = st.session_state.step
if isinstance(step, int):
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown(step_html("Wash Info",         1, "done" if step > 1 else "active" if step == 1 else "pending"), unsafe_allow_html=True)
    with sc2:
        st.markdown(step_html("Campaign Details",  2, "done" if step > 2 else "active" if step == 2 else "pending"), unsafe_allow_html=True)
    with sc3:
        st.markdown(step_html("Review & Generate", 3, "done" if step > 3 else "active" if step == 3 else "pending"), unsafe_allow_html=True)
    st.markdown("---")


# ─────────────────────────────────────────────────────────────
# STEP 1 — WASH INFO
# ─────────────────────────────────────────────────────────────
if st.session_state.step == 1:
    st.markdown("### Car Wash Info")
    st.caption("Start with the location and the month you're planning for.")

    wash_name = st.text_input(
        "Car Wash Name",
        value=st.session_state.wash_name,
        placeholder="e.g. Sparkle Car Wash – Tulsa"
    )

    month_sel = st.selectbox(
        "Month",
        options=list(MONTH_OPTIONS.keys()),
        format_func=lambda x: MONTH_OPTIONS[x],
        index=list(MONTH_OPTIONS.keys()).index(st.session_state.month) if st.session_state.month else 0
    )

    if month_sel:
        m = MONTHS[month_sel]
        st.info(
            f"**🗓 Holidays:** {m['holidays']}  \n"
            f"**🌿 Seasonal:** {m['seasonal']}  \n"
            f"**💡 Default move:** {m['def']}"
        )

    st.markdown("")
    if st.button("Next: Campaign Details →", type="primary", use_container_width=True):
        if not wash_name.strip():
            st.error("Please enter the car wash name.")
        elif not month_sel:
            st.error("Please select a month.")
        else:
            st.session_state.wash_name = wash_name
            st.session_state.month     = month_sel
            st.session_state.step      = 2
            st.rerun()


# ─────────────────────────────────────────────────────────────
# STEP 2 — CAMPAIGN DETAILS
# ─────────────────────────────────────────────────────────────
elif st.session_state.step == 2:
    st.markdown("### Campaign Details")
    st.caption("These five fields are the bones of your campaign. Without all of them, the copy won't land.")

    theme        = st.text_input("Theme — the controlling idea",               value=st.session_state.theme,        placeholder="e.g. Give Mom the Gift of Clean")
    offer        = st.text_input("Offer — what the customer gets",             value=st.session_state.offer,        placeholder="e.g. Buy 1 wash, get 1 FREE this Mother's Day")
    link         = st.text_input("Link — landing page or redemption URL",      value=st.session_state.link,         placeholder="e.g. https://yourwash.com/mothers-day")
    instructions = st.text_input("Customer Instructions — what they do, in one line", value=st.session_state.instructions, placeholder="e.g. Text MOM to 55555 or show this at the kiosk")

    dc1, dc2 = st.columns(2)
    with dc1:
        start_date = st.date_input("Campaign Start Date", value=st.session_state.start_date or date.today())
    with dc2:
        end_date = st.date_input("Campaign End Date", value=st.session_state.end_date or date.today())

    notes = st.text_area(
        "Additional Notes (optional)",
        value=st.session_state.notes,
        placeholder="e.g. Mention we have a tunnel wash. Running a raffle for members.",
        height=80
    )

    st.markdown("")
    bc1, bc2 = st.columns([1, 3])
    with bc1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with bc2:
        if st.button("Next: Review →", type="primary", use_container_width=True):
            errors = [f for f, v in [("Theme", theme), ("Offer", offer), ("Link", link), ("Customer Instructions", instructions)] if not v.strip()]
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            elif end_date < start_date:
                st.error("End date must be after start date.")
            else:
                st.session_state.theme        = theme
                st.session_state.offer        = offer
                st.session_state.link         = link
                st.session_state.instructions = instructions
                st.session_state.start_date   = start_date
                st.session_state.end_date     = end_date
                st.session_state.notes        = notes
                st.session_state.step         = 3
                st.rerun()


# ─────────────────────────────────────────────────────────────
# STEP 3 — REVIEW & GENERATE
# ─────────────────────────────────────────────────────────────
elif st.session_state.step == 3:
    s = st.session_state
    m = MONTHS[s.month]

    st.markdown("### Review & Generate")
    st.caption("Double-check everything, then hit Generate.")

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown(f"**Car Wash**  \n{s.wash_name}")
        st.markdown(f"**Theme**  \n{s.theme}")
        st.markdown(f"**Link**  \n{s.link}")
        st.markdown(f"**Start Date**  \n{s.start_date.strftime('%b %d, %Y') if s.start_date else '—'}")
    with rc2:
        st.markdown(f"**Month**  \n{m['name']}")
        st.markdown(f"**Offer**  \n{s.offer}")
        st.markdown(f"**Instructions**  \n{s.instructions}")
        st.markdown(f"**End Date**  \n{s.end_date.strftime('%b %d, %Y') if s.end_date else '—'}")
    if s.notes:
        st.markdown(f"**Notes**  \n{s.notes}")

    st.markdown("---")
    gc1, gc2 = st.columns([1, 3])
    with gc1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with gc2:
        if st.button("✨ Generate Campaign Content", type="primary", use_container_width=True):
            if is_live:
                prompt = build_prompt(s, m)
                with st.spinner("Generating content with Claude… (10–15 seconds)"):
                    try:
                        client  = anthropic.Anthropic(api_key=API_KEY)
                        message = client.messages.create(
                            model="claude-opus-4-5",
                            max_tokens=2000,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        raw = message.content[0].text.strip()
                        # Strip markdown code fences if present
                        if raw.startswith("```"):
                            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                        output = json.loads(raw)
                        st.session_state.output  = output
                        st.session_state.is_demo = False
                        st.session_state.step    = "output"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {e}  \nTry again or check your API key.")
            else:
                with st.spinner("Loading demo content…"):
                    time.sleep(2)
                st.session_state.output  = DEMO_OUTPUT
                st.session_state.is_demo = True
                st.session_state.step    = "output"
                st.rerun()


# ─────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────
elif st.session_state.step == "output":
    s      = st.session_state
    output = s.output
    m      = MONTHS.get(s.month, MONTHS["may"])

    # Header
    oc1, oc2 = st.columns([3, 1])
    with oc1:
        st.markdown("### Campaign Content")
        st.caption(f"{s.wash_name} · {s.theme}")
    with oc2:
        st.markdown(
            f"<div style='text-align:right;padding-top:10px;'>"
            f"<span style='background:#1a3a6c;color:white;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:700;'>{m['name']}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    if s.is_demo:
        st.warning("⚠ **Demo output** — Add `ANTHROPIC_API_KEY` in Streamlit Cloud secrets to generate live content.")

    # ── 4 Channel Tabs ──
    tab_sms, tab_social, tab_sign, tab_team = st.tabs(["📱  Text Club", "📸  Social", "🪧  Signage", "🗣️  Team"])

    # ── Text Club ──
    with tab_sms:
        for msg in output["textClub"]:
            st.markdown(f"**{msg['label']}**")
            chars = msg["chars"]
            if chars <= 140:
                st.markdown(f"<small style='color:#16a34a;'>✓ {chars} chars</small>", unsafe_allow_html=True)
            elif chars <= 160:
                st.markdown(f"<small style='color:#d97706;'>⚠ {chars} chars</small>", unsafe_allow_html=True)
            else:
                st.markdown(f"<small style='color:#dc2626;'>✗ {chars} chars (over 160!)</small>", unsafe_allow_html=True)
            st.code(msg["text"], language=None)
            st.markdown("")

    # ── Social ──
    with tab_social:
        for post in output["social"]:
            st.markdown(f"**{post['label']}**")
            st.code(f"{post['text']}\n\n{post['tags']}", language=None)
            st.markdown("")

    # ── Signage ──
    with tab_sign:
        for sign in output["onsite"]:
            st.markdown(f"**{sign['label']}**")
            st.markdown(
                f"<div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 16px;margin:6px 0 12px;'>"
                f"<div style='font-size:20px;font-weight:900;color:#0f172a;margin-bottom:4px;'>{sign['headline']}</div>"
                f"<div style='font-size:14px;color:#64748b;'>{sign['sub'].replace(chr(10), '<br>')}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.code(f"{sign['headline']}\n{sign['sub']}", language=None)
            st.markdown("")

    # ── Team Talking Points ──
    with tab_team:
        for i, tp in enumerate(output["team"], 1):
            st.markdown(
                f"<div style='display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #e2e8f0;'>"
                f"<div style='width:26px;height:26px;border-radius:50%;background:#f3e8ff;color:#7e22ce;font-size:12px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;'>{i}</div>"
                f"<div style='font-size:14px;line-height:1.65;'>{tp}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("")
        st.markdown("**Copy all talking points:**")
        st.code("\n\n".join([f"{i+1}. {tp}" for i, tp in enumerate(output["team"])]), language=None)

    # Start Over
    st.markdown("---")
    if st.button("← Start Over"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
