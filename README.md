# 🌸 Poetry Mailer — Setup Guide

Send personalised poems to all your readers with one click.

---

## 1 · Prerequisites

- Python 3.10+
- A Gmail account
- A Google Sheet with columns **Name** and **Email** (row 1 = headers)
- A Google Cloud Service Account (free, takes ~5 min)

---

## 2 · Gmail App Password

You need an **App Password** (not your regular Gmail password).

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. **Security → 2-Step Verification** — enable it if not already on
3. **Security → App passwords**
4. Choose *Mail* + *Windows/Mac* → **Generate**
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

---

## 3 · Google Sheet

Create a sheet with this structure:

| Name     | Email              |
|----------|--------------------|
| Aisha    | aisha@example.com  |
| Rahul    | rahul@example.com  |

Row 1 must be exactly `Name` and `Email` (case-insensitive).

---

## 4 · Google Cloud Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create**
5. Give it any name, skip optional steps, click **Done**
6. Click the service account → **Keys → Add Key → JSON** — download the file
7. **Share your Google Sheet** with the service account email  
   (looks like `something@project-id.iam.gserviceaccount.com`) as **Viewer**

---

## 5 · Install & Run Locally

```bash
cd poetry_mailer
pip install -r requirements.txt
streamlit run app.py
```

---

## 6 · Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo + `app.py` → **Deploy**
4. Your app is live at a public URL!

> **Tip:** On Streamlit Cloud you can store secrets via  
> *Settings → Secrets* so you don't paste credentials every time.

---

## 7 · Using the App

| Field | What to enter |
|-------|---------------|
| **Gmail address** | your@gmail.com |
| **App Password** | 16-char password from step 2 |
| **Service Account JSON** | Paste the full contents of the downloaded JSON key |
| **Sheet URL** | Full URL of your Google Sheet |
| **Subject** | e.g. `Dear <n>, a poem for you 🌸` |
| **Poem** | Your poetry — use `<n>` wherever you want the reader's name |

---

## 8 · Personalisation Placeholder

Use `<n>` in both the **subject** and the **poem body**.  
It will be replaced with each reader's name from the sheet.

**Example:**

```
Subject: Dear <n>, petals for you 🌸

Dear <n>,

In the bloom of April's light,
your name echoes through the night...
```

---

## Tips

- Gmail allows ~500 emails/day on a free account
- The app adds a small delay between sends to avoid rate limits
- Preview the personalised email before sending (expander in the UI)
