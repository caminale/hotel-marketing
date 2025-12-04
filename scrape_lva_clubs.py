#!/usr/bin/env python3
"""
=============================================================================
SCRAPER LVA-AUTO.FR - Annuaire des Clubs Automobiles
=============================================================================

Stratégie optimisée :
1. Selenium : ouvre le site, clique sur Clubs, Chercher, récupère les liens
2. Selenium se ferme
3. Requests/BeautifulSoup : parcourt chaque lien (rapide et stable)

Usage:
    python3 scrape_lva_clubs.py

=============================================================================
"""

import csv
import re
import time
import sys
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"❌ Module manquant: {e}")
    print("   pip3 install selenium requests beautifulsoup4")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.lva-auto.fr"
OUTPUT_FILE = "bdd_club/auto/lva-auto.csv"
DELAY = 0.25  # Délai entre requêtes (secondes)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}


# =============================================================================
# ÉTAPE 1 : SELENIUM - Récupérer la liste des liens
# =============================================================================

def get_club_links_with_selenium():
    """
    Utilise Safari pour :
    1. Aller sur l'annuaire
    2. Cliquer sur CLUBS
    3. Cliquer sur CHERCHER
    4. Extraire tous les liens
    """
    print("🚀 Démarrage de Safari...")
    driver = webdriver.Safari()
    links = []
    
    try:
        # Aller sur l'annuaire
        print("📍 Navigation vers l'annuaire...")
        driver.get(f"{BASE_URL}/annuaire.php")
        time.sleep(2)
        
        # Cliquer sur CLUBS
        print("🔘 Clic sur CLUBS...")
        clubs_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "CLUBS"))
        )
        clubs_link.click()
        time.sleep(1)
        
        # Cliquer sur CHERCHER
        print("🔍 Clic sur CHERCHER...")
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'CHERCHER')]"))
        )
        search_btn.click()
        time.sleep(3)
        
        # Extraire tous les liens
        print("📋 Extraction des liens...")
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        for a in soup.find_all('a', href=re.compile(r'annuaire\.detail\.php\?id=')):
            href = a.get('href')
            name = a.get_text(strip=True)
            
            if not name or not href:
                continue
            
            # URL complète
            full_url = f"{BASE_URL}/{href}" if not href.startswith('http') else href
            
            # ID du club
            id_match = re.search(r'id=([^&]+)', href)
            club_id = id_match.group(1) if id_match else ''
            
            # Adresse (td suivant)
            parent_td = a.find_parent('td')
            address = ''
            if parent_td:
                next_td = parent_td.find_next_sibling('td')
                if next_td:
                    address = next_td.get_text(strip=True)
            
            links.append({
                'id': club_id,
                'nom': name,
                'adresse': address,
                'lien': full_url
            })
        
        print(f"✅ {len(links)} liens récupérés")
        
    finally:
        driver.quit()
        print("🛑 Safari fermé")
    
    return links


# =============================================================================
# ÉTAPE 2 : REQUESTS - Parcourir chaque fiche
# =============================================================================

def decode_cloudflare_email(encoded):
    """Décode les emails protégés par Cloudflare."""
    try:
        r = int(encoded[:2], 16)
        return ''.join([chr(int(encoded[i:i+2], 16) ^ r) for i in range(2, len(encoded), 2)])
    except:
        return ''


def fix_encoding(text):
    """Corrige l'encodage UTF-8 cassé."""
    if not text:
        return ''
    fixes = {
        'Ã©': 'é', 'Ã¨': 'è', 'Ã ': 'à', 'Ã§': 'ç',
        'Ã´': 'ô', 'Ã¢': 'â', 'Ãª': 'ê', 'Ã®': 'î',
        'Ã»': 'û', 'Ã¹': 'ù', 'Ã«': 'ë', 'Ã¯': 'ï',
        'Ã‰': 'É', 'Ã€': 'À', 'Ã"': 'Ô',
        'Ã¼': 'ü', 'Ã¶': 'ö', 'Ã¤': 'ä', 'Â': '',
    }
    for bad, good in fixes.items():
        text = text.replace(bad, good)
    return text


def scrape_club_details(session, url):
    """Extrait les détails d'une fiche club avec requests."""
    try:
        response = session.get(url, timeout=10)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        details = {
            'telephone': '',
            'email': '',
            'bureau': '',
            'site_internet': ''
        }
        
        # TÉLÉPHONE
        tel_match = re.search(
            r'T[eéÃ©]+l\.?\s*(0\d[\s\.]*\d{2}[\s\.]*\d{2}[\s\.]*\d{2}[\s\.]*\d{2})',
            html, re.IGNORECASE
        )
        if tel_match:
            tel = re.sub(r'[^\d\s]', '', tel_match.group(1))
            details['telephone'] = re.sub(r'\s+', ' ', tel).strip()
        
        # EMAIL (Cloudflare)
        cf = soup.find('span', class_='__cf_email__')
        if cf and cf.get('data-cfemail'):
            details['email'] = decode_cloudflare_email(cf.get('data-cfemail'))
        else:
            em = re.search(r'[\w\.-]+@[\w\.-]+\.\w{2,}', soup.get_text())
            if em:
                details['email'] = em.group(0)
        
        # BUREAU
        bureau = re.search(r'Bureau\s*:\s*</strong>([^<]+)', html)
        if bureau:
            details['bureau'] = fix_encoding(bureau.group(1).strip()[:250])
        
        # SITE INTERNET
        site = re.search(r'Site Internet\s*:\s*<a[^>]*href="([^"]+)"', html)
        if site and site.group(1) not in ('http://', 'https://', ''):
            details['site_internet'] = site.group(1)
        
        return details
        
    except Exception as e:
        return None


def scrape_all_details(clubs):
    """Parcourt tous les clubs avec requests (rapide et stable)."""
    print(f"\n📡 Scraping des {len(clubs)} fiches avec requests...")
    print(f"⏱️  Temps estimé: ~{len(clubs) * DELAY / 60:.0f} minutes")
    print("-" * 60)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    success = 0
    errors = 0
    
    for i, club in enumerate(clubs):
        details = scrape_club_details(session, club['lien'])
        
        if details:
            club.update(details)
            if details.get('email'):
                success += 1
        else:
            errors += 1
        
        # Progression tous les 50 + sauvegarde intermédiaire tous les 200
        if (i + 1) % 50 == 0:
            pct = (i + 1) * 100 // len(clubs)
            print(f"📊 [{i+1}/{len(clubs)}] {pct}% - ✉️ {success} emails")
        
        if (i + 1) % 200 == 0:
            save_csv(clubs)
            print(f"💾 Sauvegarde intermédiaire ({i+1} clubs)")
        
        time.sleep(DELAY)
    
    print("-" * 60)
    return clubs


# =============================================================================
# SAUVEGARDE CSV
# =============================================================================

def save_csv(clubs):
    """Sauvegarde en CSV avec bon encodage."""
    print(f"💾 Sauvegarde dans {OUTPUT_FILE}...")
    
    # Corriger l'encodage de tous les champs texte
    for club in clubs:
        club['nom'] = fix_encoding(club.get('nom', ''))
        club['adresse'] = fix_encoding(club.get('adresse', ''))
        club['bureau'] = fix_encoding(club.get('bureau', ''))
    
    fieldnames = ['id', 'nom', 'adresse', 'telephone', 'email', 'bureau', 'site_internet', 'lien']
    
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clubs)
    
    print(f"✅ Fichier créé: {OUTPUT_FILE}")


def print_stats(clubs):
    """Affiche les statistiques."""
    total = len(clubs)
    emails = sum(1 for c in clubs if c.get('email'))
    phones = sum(1 for c in clubs if c.get('telephone'))
    sites = sum(1 for c in clubs if c.get('site_internet'))
    bureaux = sum(1 for c in clubs if c.get('bureau'))
    
    print(f"""
{'='*60}
📊 STATISTIQUES FINALES
{'='*60}
   Total clubs  : {total}
   Emails       : {emails:>4} ({emails*100//total}%)
   Téléphones   : {phones:>4} ({phones*100//total}%)
   Sites web    : {sites:>4} ({sites*100//total}%)
   Bureau       : {bureaux:>4} ({bureaux*100//total}%)
{'='*60}
""")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"""
{'='*60}
🏎️  SCRAPER LVA-AUTO.FR
{'='*60}
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📁 Sortie: {OUTPUT_FILE}
{'='*60}
""")
    
    try:
        # ÉTAPE 1: Selenium récupère les liens
        clubs = get_club_links_with_selenium()
        
        if not clubs:
            print("❌ Aucun lien récupéré")
            sys.exit(1)
        
        # ÉTAPE 2: Requests parcourt les fiches
        clubs = scrape_all_details(clubs)
        
        # ÉTAPE 3: Sauvegarde
        save_csv(clubs)
        print_stats(clubs)
        
        print("🎉 Terminé !")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrompu")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
