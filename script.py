import requests
import pandas as pd
from datetime import datetime, timedelta
from google.colab import auth
from googleapiclient.discovery import build
import smtplib
from email.message import EmailMessage
import os

# 1. Autentizace do Google Colab a Drive
auth.authenticate_user()
from google.colab import drive
drive.mount('/content/drive')

# 2. Nastavení PubMed API dotazu
def fetch_pubmed_articles(days=7):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": "Hradec Kralove[Affiliation] OR Faculty Hospital Hradec Kralove[Affiliation]",
        "reldate": days,
        "datetype": "pdat",
        "retmax": 50,
        "retmode": "json"
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json().get("esearchresult", {}).get("idlist", [])
    return []

# 3. Získání detailů článků
def fetch_article_details(pmids):
    if not pmids:
        return []
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json"
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json().get("result", {})
    return {}

# 4. Načtení databáze časopisů Q1/Q2
def load_q1_q2_journals(filename="/content/drive/MyDrive/q1_q2_journals.csv"):
    try:
        return pd.read_csv(filename)["Journal"].tolist()
    except FileNotFoundError:
        print("Soubor s Q1/Q2 časopisy nenalezen.")
        return []

# 5. Uložení výsledků do Google Drive
def save_to_drive(df, filename="filtered_pubmed_articles.csv"):
    save_path = f"/content/drive/MyDrive/{filename}"
    df.to_csv(save_path, index=False)
    print(f"Výsledky uloženy na Google Drive: {save_path}")

# 6. Odeslání e-mailu přes Gmail SMTP s App Password
def send_email():
    recipient = "lucie.bartosova@fnhk.cz"
    subject = "Týdenní přehled publikací FN HK"
    body = "Dobrý den,\n\nPřikládám týdenní přehled publikací zaměstnanců FN HK v časopisech Q1/Q2.\n\nS pozdravem,\nAutomatizovaný systém"
    sender_email = "your_email@gmail.com"  # Změňte na svou Gmail adresu
    app_password = "your_app_password"  # Vložte vygenerované App Password
    
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient
    msg.set_content(body)
    
    with open("/content/drive/MyDrive/filtered_pubmed_articles.csv", "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="csv", filename="filtered_pubmed_articles.csv")
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        
    print("E-mail byl odeslán na lucie.bartosova@fnhk.cz.")

# 7. Zpracování článků
def process_articles():
    pmids = fetch_pubmed_articles()
    article_data = fetch_article_details(pmids)
    q1_q2_journals = load_q1_q2_journals()
    
    articles = []
    for pmid in pmids:
        article = article_data.get(pmid, {})
        journal = article.get("source", "Unknown")
        
        if journal in q1_q2_journals:
            articles.append({
                "PMID": pmid,
                "Title": article.get("title", "N/A"),
                "Authors": ", ".join(article.get("authors", [])),
                "Journal": journal,
                "PubDate": article.get("pubdate", "N/A"),
                "URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
    
    df = pd.DataFrame(articles)
    save_to_drive(df)
    send_email()

# Spustit skript
if __name__ == "__main__":
    process_articles()
