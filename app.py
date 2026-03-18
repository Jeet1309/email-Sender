import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re, json, time

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Poetry Mailer 🌸", page_icon="🌸", layout="centered")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2 { font-family: 'Playfair Display', serif !important; color: #3d1a4f !important; }
.stTextArea textarea {
    font-family: 'Playfair Display', serif !important; font-style: italic;
    font-size: 1.05rem; line-height: 1.8; background: #2d1b4e;
    border: 1px solid #e8c8d8; border-radius: 12px;
}
.stTextInput input { border-radius: 10px; border: 1px solid #e0b8cc; }
.stButton > button {
    background: linear-gradient(135deg, #9b4dca, #c0392b) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    padding: 0.6rem 2rem !important; font-size: 1rem !important;
    font-weight: 500 !important; width: 100%;
}
.recipient-card {
    background: white; border-left: 4px solid #9b4dca; border-radius: 8px;
    padding: 0.6rem 1rem; margin: 0.4rem 0; font-size: 0.9rem; color: #444;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.success-msg { background:#f0fdf4; border:1px solid #86efac; border-radius:10px; padding:1rem; color:#166534; margin:0.5rem 0; }
.error-msg   { background:#fef2f2; border:1px solid #fca5a5; border-radius:10px; padding:1rem; color:#991b1b; margin:0.5rem 0; }
.info-box    { background:#fffbeb; border:1px solid #fcd34d; border-radius:10px; padding:0.8rem 1rem; color:#78350f; font-size:0.85rem; }
.tag { display:inline-block; background:#f3e8ff; color:#6b21a8; border-radius:6px; padding:2px 8px; font-size:0.8rem; font-family:monospace; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_and_parse_json(raw: str) -> dict:
    text = raw.strip().lstrip("\ufeff").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text).strip()
    if text.startswith('"') and text.endswith('"'):
        try: text = json.loads(text)
        except Exception: pass
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at position {exc.pos}: {exc.msg}. "
                         "Open the .json key file in a text editor, Select All, Copy, paste here.") from exc
    missing = {"type","project_id","private_key","client_email"} - result.keys()
    if missing:
        raise ValueError(f"Missing service account fields: {', '.join(missing)}")
    return result


def get_recipients(sheet_url: str, creds_dict: dict) -> list[dict]:
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
              "https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    ws = gc.open_by_url(sheet_url).sheet1
    all_values = ws.get_all_values()
    if not all_values:
        raise ValueError("Sheet is empty.")
    headers   = [h.strip().lower() for h in all_values[0]]
    name_col  = next((i for i,h in enumerate(headers) if "your name" in h), None)
    email_col = next((i for i,h in enumerate(headers) if "send you my poems" in h or "email" in h), None)
    if email_col is None:
        raise ValueError(f"No Email column found. Headers seen: {all_values[0]}")
    recipients = []
    for row in all_values[1:]:
        while len(row) <= max(name_col or 0, email_col): row.append("")
        email = row[email_col].strip()
        name  = (row[name_col].strip() if name_col is not None else "") or email.split("@")[0]
        if email and "@" in email:
            recipients.append({"name": name, "email": email})
    return recipients


def build_message(sender: str, to: str, subject: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to
    msg.attach(MIMEText(body, "plain", "utf-8"))
    html = f"""<html><body style="margin:0;padding:0;background:#fdf6f0;">
      <table width="100%"><tr><td align="center" style="padding:40px 20px;">
        <table width="600" style="background:#fff;border-radius:16px;padding:40px;
               font-family:Georgia,serif;box-shadow:0 4px 24px rgba(0,0,0,.08);">
          <tr><td style="text-align:center;padding-bottom:20px;font-size:1.2rem;">🌻</td></tr>
          <tr><td style="color:#3d1a4f;font-size:1.4rem;font-weight:bold;
                         text-align:center;padding-bottom:24px;">{subject}</td></tr>
          <tr><td style="color:#333;font-size:1.05rem;line-height:2;
                         white-space:pre-wrap;text-align:left;">{body}</td></tr>
          <tr><td style="padding-top:28px;text-align:center;color:#bbb;font-size:.8rem;">
            from my thoughts to your  </td></tr>
        </table>
      </td></tr></table>
    </body></html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_via_smtp(sender: str, app_password: str, to: str, msg: MIMEMultipart):
    """SMTP over SSL port 465 — works on Streamlit Cloud."""
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=20) as srv:
        srv.login(sender, app_password)
        srv.sendmail(sender, to, msg.as_string())


def personalise(text: str, name: str) -> str:
    return re.sub(r"<n>", name, text, flags=re.IGNORECASE)


def secret(key: str, default=""):
    try: return st.secrets.get(key, default)
    except Exception: return default


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("## 🌸 Poetry Mailer")
st.markdown("*Send personalised poems to all your readers — in one click.*")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    sender_email = st.text_input("Your Gmail address",
                                 value=secret("SENDER_EMAIL"),
                                 placeholder="you@gmail.com")
    app_password = st.text_input("Gmail App Password",
                                 value=secret("APP_PASSWORD"),
                                 type="password",
                                 placeholder="xxxx xxxx xxxx xxxx",
                                 help="myaccount.google.com → Security → App passwords")
    st.markdown("---")
    st.markdown("**Google Service Account JSON**")
    st.markdown("<div class='info-box'>Paste the full contents of your downloaded JSON key file.</div>",
                unsafe_allow_html=True)
    creds_json = st.text_area("Service Account JSON",
                               value=secret("GCP_SERVICE_ACCOUNT"),
                               height=120,
                               placeholder='{"type": "service_account", ...}')
    st.markdown("---")
    st.markdown("<div class='info-box'>📋 Sheet must have headers: "
                "<span class='tag'>Name</span> <span class='tag'>Email</span></div>",
                unsafe_allow_html=True)

# ── Sheet loader ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    sheet_url = st.text_input("📊 Google Sheet URL",
                              value=secret("SHEET_URL"),
                              placeholder="https://docs.google.com/spreadsheets/d/...")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    load_btn = st.button("Load")

recipients = []
if load_btn:
    if not sheet_url:
        st.warning("Enter a Google Sheet URL.")
    elif not creds_json:
        st.warning("Paste your Service Account JSON in the sidebar.")
    else:
        try:
            cd = clean_and_parse_json(creds_json)
            with st.spinner("Fetching recipients…"):
                recipients = get_recipients(sheet_url, cd)
            st.session_state["recipients"] = recipients
            st.success(f"✅ Loaded **{len(recipients)}** recipient(s).")
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("Sheet not found — check the URL and make sure it's shared with the service account email.")
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error: {e}")

if "recipients" in st.session_state:
    recipients = st.session_state["recipients"]
    with st.expander(f"👥 Recipients ({len(recipients)})", expanded=False):
        for r in recipients:
            st.markdown(f"<div class='recipient-card'>🌷 <b>{r['name']}</b> — {r['email']}</div>",
                        unsafe_allow_html=True)

st.divider()

# ── Compose ───────────────────────────────────────────────────────────────────
subject_template = st.text_input("✉️ Subject",
                                 placeholder="Dear <n>, a poem for you 🌸",
                                 help="Use <n> for each reader's name")

st.markdown("**📜 Your Poem**")
st.markdown("<div class='info-box' style='margin-bottom:8px;'>Use <span class='tag'>&lt;n&gt;</span> "
            "anywhere — it becomes each reader's name.</div>", unsafe_allow_html=True)
poem = st.text_area("Poem", height=300,
                    placeholder="Dear <n>,\n\nIn the bloom of April's light,\n...",
                    label_visibility="collapsed")

if poem and recipients:
    with st.expander("👁️ Preview — first recipient", expanded=False):
        first = recipients[0]
        st.markdown(f"**Subject:** {personalise(subject_template, first['name'])}\n\n"
                    f"---\n\n{personalise(poem, first['name'])}")

st.divider()
send_btn = st.button("🚀 Send Poems to Everyone", use_container_width=True)

# ── Send ──────────────────────────────────────────────────────────────────────
if send_btn:
    problems = []
    if not sender_email:     problems.append("Gmail address missing (sidebar).")
    if not app_password:     problems.append("App Password missing (sidebar).")
    if not creds_json:       problems.append("Service Account JSON missing (sidebar).")
    if not recipients:       problems.append("No recipients — load the sheet first.")
    if not subject_template: problems.append("Subject is empty.")
    if not poem:             problems.append("Poem is empty.")

    for p in problems:
        st.warning(p)

    if not problems:
        try:
            creds_dict = clean_and_parse_json(creds_json)
        except ValueError as ve:
            st.error(str(ve))
            creds_dict = None

        if creds_dict:
            bar = st.progress(0, text="Starting…")
            ok_list, err_list = [], []

            for i, r in enumerate(recipients):
                subj = personalise(subject_template, r["name"])
                body = personalise(poem, r["name"])
                try:
                    msg = build_message(sender_email, r["email"], subj, body)
                    send_via_smtp(sender_email, app_password, r["email"], msg)
                    ok_list.append(r)
                except Exception as exc:
                    err_list.append((r, str(exc)))
                bar.progress((i + 1) / len(recipients), text=f"Sending {i+1}/{len(recipients)}…")
                time.sleep(0.3)

            bar.empty()

            if ok_list:
                st.markdown(f"<div class='success-msg'>🎉 Sent to <b>{len(ok_list)}</b> reader(s)!</div>",
                            unsafe_allow_html=True)
            if err_list:
                st.markdown(f"<div class='error-msg'>⚠️ Failed for <b>{len(err_list)}</b> recipient(s):</div>",
                            unsafe_allow_html=True)
                for r, exc in err_list:
                    st.markdown(f"- **{r['name']}** ({r['email']}): `{exc}`")
