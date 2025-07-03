
from flask import Flask, render_template, request, send_file
import os
import pandas as pd
import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

CAREER_KEYWORDS = ['career', "careers", 'jobs', "join", 'join-us', 'work-with-us', 'we-are-hiring', 'vacancy', "hiring", "openings", 'recruit']

def try_fetch(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        return requests.get(url, headers=headers, timeout=8)
    except:
        return None

def is_probable_career_link(href, text):
    href = href.lower()
    text = (text or "").lower()

    if any(kw in href or kw in text for kw in CAREER_KEYWORDS):
        return True
    parts = href.strip("/").split("/")
    return any(kw in part for part in parts for kw in CAREER_KEYWORDS)

def find_careers_link(domain):
    base_variants = [f"https://{domain}", f"http://{domain}"]
    for base_url in base_variants:
        resp = try_fetch(base_url)
        if not resp or resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if is_probable_career_link(href, text):
                return urljoin(base_url, href)
    return None

def parse_domains(domain_str):
    try:
        return json.loads(domain_str.replace("'", '"'))
    except:
        return []

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process_file():
    file = request.files['file']
    if not file:
        return "No file uploaded", 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    df = pd.read_csv(filepath)
    results = []
    logs = []

    for index, row in df.iterrows():
        company_id = row['id']
        company_name = row['name']
        domains = parse_domains(row['domains'])

        for domain in domains:
            log_msg = f"🔍 Searching {company_name} - {domain}..."
            print(log_msg)
            logs.append(log_msg)

            link = find_careers_link(domain)

            if link:
                logs.append(f"✅ Found: {link}")
            else:
                logs.append("❌ Not Found")

            results.append({
                "id": company_id,
                "company_name": company_name,
                "domain": domain,
                "careers_page_url": link or "Not Found"
            })
            time.sleep(1)

    output_path = os.path.join(RESULT_FOLDER, "output.csv")
    pd.DataFrame(results).to_csv(output_path, index=False)

    return render_template("index.html", download_url="/download", logs=logs)

@app.route("/download", methods=["GET"])
def download_file():
    return send_file("results/output.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
