#!/usr/bin/env python3
"""
Script d'extraction des clubs automobiles depuis lva-data.html
Extrait : Nom du club, Adresse, Lien vers fiche détail
"""

import re
import csv

def extract_clubs(html_file, output_csv):
    """Extrait les informations des clubs depuis le fichier HTML avec regex"""
    
    # Lire le fichier HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    clubs = []
    
    # Pattern pour trouver chaque club
    # <h2><a href="annuaire.detail.php?id=C2211&amp;idCategorie=C">NOM DU CLUB</a></h2>
    # suivi de <td class="bdr">ADRESSE</td>
    
    pattern = r'<h2><a href="([^"]+)"[^>]*>([^<]+)</a></h2></td>\s*<td class="bdr">([^<]+)</td>\s*<td>\s*([^<]*(?:<br>[^<]*)*)'
    
    matches = re.findall(pattern, html_content, re.DOTALL)
    
    print(f"🔍 Trouvé {len(matches)} correspondances avec le pattern")
    
    if len(matches) == 0:
        # Essayer un pattern plus simple
        # Trouver tous les liens vers annuaire.detail.php
        pattern2 = r'<h2><a href="(annuaire\.detail\.php\?id=[^"]+)">([^<]+)</a></h2>'
        matches2 = re.findall(pattern2, html_content)
        print(f"🔍 Pattern alternatif: {len(matches2)} clubs trouvés")
        
        # Trouver les adresses séparément
        pattern_addr = r'<td class="bdr">([^<]+)</td>'
        addresses = re.findall(pattern_addr, html_content)
        print(f"🔍 {len(addresses)} adresses trouvées")
        
        # Combiner
        for i, (link, name) in enumerate(matches2):
            club_id = ''
            if 'id=' in link:
                match = re.search(r'id=([^&]+)', link)
                if match:
                    club_id = match.group(1)
            
            address = addresses[i] if i < len(addresses) else ''
            
            clubs.append({
                'id': club_id,
                'nom': name.strip(),
                'adresse': address.strip(),
                'lien': f"https://www.lva.fr/{link}",
                'telephone': '',
                'email': '',
                'bureau': '',
                'site_internet': ''
            })
    else:
        for link, name, address, desc in matches:
            club_id = ''
            if 'id=' in link:
                match = re.search(r'id=([^&]+)', link)
                if match:
                    club_id = match.group(1)
            
            clubs.append({
                'id': club_id,
                'nom': name.strip(),
                'adresse': address.strip(),
                'lien': f"https://www.lva.fr/{link}",
                'telephone': '',
                'email': '',
                'bureau': '',
                'site_internet': ''
            })
    
    # Écrire dans le CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'nom', 'adresse', 'lien', 'telephone', 'email', 'bureau', 'site_internet']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clubs)
    
    print(f"✅ {len(clubs)} clubs extraits vers {output_csv}")
    return clubs

if __name__ == "__main__":
    clubs = extract_clubs('lva-data.html', 'clubs_liste.csv')
    
    # Afficher les 5 premiers pour vérification
    print("\n📋 Aperçu des 5 premiers clubs:")
    for club in clubs[:5]:
        print(f"  - {club['nom']} ({club['adresse']})")
    
    print(f"\n⚠️  NOTE: Les colonnes telephone, email, bureau, site_internet sont vides")
    print(f"   Ces infos sont sur les pages détail individuelles.")
    print(f"   Fournissez les pages détail HTML pour compléter l'extraction.")

