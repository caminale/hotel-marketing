#!/usr/bin/env python3
"""
=============================================================================
SCRAPER RETROCALAGE.COM - Annuaire des Clubs
=============================================================================

Stratégie :
1. Selenium : ouvre le site, clique sur "Afficher plus" jusqu'à épuisement
2. Récupère le HTML complet
3. Selenium se ferme
4. BeautifulSoup : extrait les données de chaque club

Usage:
    python3 scrape_retrocalage.py

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
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"❌ Module manquant: {e}")
    print("   pip3 install selenium beautifulsoup4")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

URL = "https://retrocalage.com/clubs?mode=list"
OUTPUT_FILE = "bdd_club/auto/retrocalage.csv"


# =============================================================================
# SELENIUM - Charger toutes les données
# =============================================================================

def load_all_clubs():
    """
    Ouvre le site, clique sur 'Afficher plus' jusqu'à ce qu'il n'y en ait plus,
    puis retourne le HTML complet.
    """
    print("=" * 60)
    print("🚗 SCRAPER RETROCALAGE.COM")
    print("=" * 60)
    print()
    
    print("🌐 Lancement de Selenium...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print(f"📄 Chargement de {URL}")
        driver.get(URL)
        
        # Attendre que la page charge
        time.sleep(3)
        
        click_count = 0
        
        print("🔄 Clic sur 'Afficher plus' jusqu'à épuisement...")
        
        while True:
            try:
                # Chercher le bouton "Afficher plus"
                # On essaie plusieurs sélecteurs possibles
                button = None
                
                # Essayer différents sélecteurs
                selectors = [
                    "//button[contains(text(), 'Afficher plus')]",
                    "//a[contains(text(), 'Afficher plus')]",
                    "//button[contains(text(), 'afficher plus')]",
                    "//a[contains(text(), 'afficher plus')]",
                    "//button[contains(@class, 'load-more')]",
                    "//a[contains(@class, 'load-more')]",
                    "//button[contains(text(), 'Voir plus')]",
                    "//a[contains(text(), 'Voir plus')]",
                ]
                
                for selector in selectors:
                    try:
                        button = driver.find_element(By.XPATH, selector)
                        if button.is_displayed():
                            break
                        button = None
                    except NoSuchElementException:
                        continue
                
                if button is None:
                    print(f"\n✅ Plus de bouton 'Afficher plus' trouvé après {click_count} clics")
                    break
                
                # Scroller jusqu'au bouton
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                
                # Cliquer
                button.click()
                click_count += 1
                
                print(f"   Clic #{click_count}...", end="\r")
                
                # Attendre le chargement
                time.sleep(1.5)
                
            except Exception as e:
                print(f"\n✅ Fin du chargement après {click_count} clics ({type(e).__name__})")
                break
        
        print()
        print("📥 Récupération du HTML...")
        html = driver.page_source
        
        return html
        
    finally:
        print("🔒 Fermeture de Selenium")
        driver.quit()


# =============================================================================
# BEAUTIFULSOUP - Extraire les données
# =============================================================================

def extract_clubs(html):
    """
    Parse le HTML et extrait les informations de chaque club.
    """
    print()
    print("🔍 Analyse du HTML avec BeautifulSoup...")
    
    soup = BeautifulSoup(html, 'html.parser')
    clubs = []
    
    # Sauvegarder le HTML pour debug si besoin
    with open('retrocalage_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("   💾 HTML sauvegardé dans retrocalage_debug.html pour debug")
    
    # Chercher les cartes de clubs
    # On va d'abord identifier la structure
    
    # Essayer différents sélecteurs pour trouver les clubs
    club_cards = soup.find_all('div', class_=re.compile(r'club|card', re.I))
    
    if not club_cards:
        # Essayer de trouver par la structure
        club_cards = soup.find_all('article')
    
    if not club_cards:
        # Chercher des liens ou divs contenant les infos
        club_cards = soup.find_all('div', class_=re.compile(r'list|item', re.I))
    
    print(f"   Trouvé {len(club_cards)} éléments potentiels")
    
    # Analyser la structure pour trouver le bon pattern
    # On va chercher des patterns communs: nom, adresse, téléphone, email
    
    # Méthode alternative: chercher tous les éléments avec des patterns reconnaissables
    # Emails
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    # Téléphones français
    phone_pattern = re.compile(r'(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}')
    
    # Chercher la structure réelle
    # D'abord, trouvons le premier club mentionné: TEAM MOBYLETTE SALUCÉENS
    first_club = soup.find(string=re.compile(r'TEAM MOBYLETTE', re.I))
    
    if first_club:
        print(f"   ✅ Premier club trouvé: {first_club.strip()[:50]}...")
        # Remonter pour trouver le conteneur parent
        parent = first_club.parent
        for _ in range(5):
            if parent and parent.parent:
                parent = parent.parent
        if parent:
            print(f"   Structure parent: {parent.name}, classes: {parent.get('class', [])}")
    
    # Chercher tous les clubs par leur structure
    # On va chercher des éléments qui contiennent les infos de contact
    
    all_text = soup.get_text()
    
    # Compter les emails trouvés pour avoir une idée du nombre de clubs
    emails_found = email_pattern.findall(all_text)
    print(f"   📧 {len(emails_found)} emails trouvés dans la page")
    
    # Stratégie: trouver tous les conteneurs qui ont un titre (h2, h3, h4) 
    # suivi d'infos de contact
    
    # Chercher les sections de clubs
    sections = []
    
    # Pattern 1: Chercher par titres
    for heading in soup.find_all(['h2', 'h3', 'h4', 'h5']):
        section = {
            'nom': heading.get_text(strip=True),
            'adresse': '',
            'representant': '',
            'telephone': '',
            'email': '',
            'site': ''
        }
        
        # Chercher les infos dans les éléments suivants
        container = heading.find_parent(['div', 'article', 'section', 'li'])
        if container:
            text = container.get_text()
            
            # Email
            email_match = email_pattern.search(text)
            if email_match:
                section['email'] = email_match.group()
            
            # Téléphone
            phone_match = phone_pattern.search(text)
            if phone_match:
                section['telephone'] = phone_match.group()
            
            # Site web
            for link in container.find_all('a', href=True):
                href = link['href']
                if href.startswith('http') and 'retrocalage' not in href and 'mailto:' not in href:
                    section['site'] = href
                    break
            
            # Adresse - chercher des patterns d'adresse
            # Chercher des codes postaux français
            cp_match = re.search(r'\d{5}\s+[\w-]+', text)
            if cp_match:
                section['adresse'] = cp_match.group()
            
            if section['email'] or section['telephone']:
                sections.append(section)
    
    if sections:
        clubs = sections
        print(f"   ✅ {len(clubs)} clubs extraits par méthode titres")
    else:
        print("   ⚠️ Méthode titres n'a rien trouvé, analyse manuelle du HTML nécessaire")
        print("   Consultez retrocalage_debug.html pour voir la structure")
    
    return clubs


def save_to_csv(clubs, filename):
    """
    Sauvegarde les clubs dans un fichier CSV.
    """
    if not clubs:
        print("⚠️ Aucun club à sauvegarder")
        return
    
    print()
    print(f"💾 Sauvegarde dans {filename}...")
    
    fieldnames = ['nom', 'adresse', 'representant', 'telephone', 'email', 'site']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clubs)
    
    print(f"✅ {len(clubs)} clubs sauvegardés!")


# =============================================================================
# MAIN
# =============================================================================

def main():
    start_time = datetime.now()
    
    # Étape 1: Charger toutes les données avec Selenium
    html = load_all_clubs()
    
    # Étape 2: Extraire les données avec BeautifulSoup
    clubs = extract_clubs(html)
    
    # Étape 3: Sauvegarder
    save_to_csv(clubs, OUTPUT_FILE)
    
    # Résumé
    duration = datetime.now() - start_time
    print()
    print("=" * 60)
    print(f"🏁 Terminé en {duration.total_seconds():.1f} secondes")
    print(f"📊 {len(clubs)} clubs trouvés")
    print("=" * 60)


if __name__ == "__main__":
    main()

