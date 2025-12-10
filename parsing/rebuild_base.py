#!/usr/bin/env python3
"""
Reconstruit Base Club Auto.csv à partir des fichiers sources
"""

import csv
import re

def format_phone(phone):
    """Formate le téléphone en format international"""
    if not phone:
        return ""
    # Nettoyer
    phone = re.sub(r'[^\d]', '', phone)
    # Format français -> international
    if phone.startswith('0') and len(phone) == 10:
        phone = '33' + phone[1:]
    return phone

def main():
    output_file = "bdd_club/auto/Base Club Auto.csv"
    clubs = []
    seen_emails = set()
    
    # 1. Charger lva-auto.csv
    print("📥 Chargement de lva-auto.csv...")
    with open("bdd_club/auto/lva-auto.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip().lower()
            if email and email not in seen_emails:
                seen_emails.add(email)
                clubs.append({
                    'Email': email,
                    'N° de mobile': format_phone(row.get('telephone', '')),
                    'Score d\'engagement': '',
                    'Source': 'File : lva-auto.csv',
                    'site': row.get('site_internet', ''),
                    'representant': row.get('bureau', ''),
                    'adresse': row.get('adresse', ''),
                    'nom': row.get('nom', '')
                })
    print(f"   {len(clubs)} clubs chargés")
    
    # 2. Charger retrocalage.csv
    print("📥 Chargement de retrocalage.csv...")
    count_retro = 0
    with open("bdd_club/auto/retrocalage.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip().lower()
            if email and email not in seen_emails:
                seen_emails.add(email)
                count_retro += 1
                clubs.append({
                    'Email': email,
                    'N° de mobile': format_phone(row.get('telephone', '')),
                    'Score d\'engagement': '',
                    'Source': 'File : retrocalage.csv',
                    'site': row.get('site', ''),
                    'representant': row.get('representant', ''),
                    'adresse': row.get('adresse', ''),
                    'nom': row.get('nom', '')
                })
    print(f"   {count_retro} clubs ajoutés")
    
    # 3. Écrire le fichier final
    print(f"\n📤 Écriture de {output_file}...")
    fieldnames = ['Email', 'N° de mobile', 'Score d\'engagement', 'Source', 'site', 'representant', 'adresse', 'nom']
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(clubs)
    
    print(f"\n✅ Fichier reconstruit: {len(clubs)} clubs")

if __name__ == "__main__":
    main()


