#!/usr/bin/env python3
"""
Nettoyage STRICT des emails - Base clubs_fusionnes.csv
"""

import csv
import re
import smtplib
import dns.resolver
import socket
from collections import defaultdict

FILE = "bdd_club/auto/clubs_fusionnes.csv"
OUTPUT_VALID = "bdd_club/auto/clubs_fusionnes_clean.csv"
OUTPUT_NPAI = "bdd_club/auto/clubs_fusionnes_npai.csv"
DELIMITER = ","

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Domaines jetables et suspects
BLACKLIST_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'yopmail.com', 
    'temp-mail.org', 'getnada.com', 'trashmail.com', '10minutemail.com',
    'fakeinbox.com', 'sharklasers.com', 'throwaway.email'
}

# Gros providers fiables (on ne vérifie pas SMTP pour eux)
TRUSTED_PROVIDERS = {
    'gmail.com', 'yahoo.com', 'yahoo.fr', 'hotmail.com', 'hotmail.fr',
    'outlook.com', 'outlook.fr', 'live.com', 'live.fr', 'msn.com',
    'orange.fr', 'wanadoo.fr', 'free.fr', 'sfr.fr', 'laposte.net',
    'neuf.fr', 'bbox.fr', 'numericable.fr', 'aol.com', 'icloud.com',
    'me.com', 'mac.com', 'protonmail.com', 'gmx.fr', 'gmx.com',
    'club-internet.fr', 'cegetel.net', 'aliceadsl.fr', 'nordnet.fr'
}


def get_mx_host(domain: str) -> str:
    """Récupère le serveur MX principal du domaine"""
    try:
        records = dns.resolver.resolve(domain, 'MX', lifetime=5)
        mx_record = sorted(records, key=lambda x: x.preference)[0]
        return str(mx_record.exchange).rstrip('.')
    except:
        return None


def verify_email_smtp(email: str, mx_host: str) -> tuple:
    """Vérifie si l'email existe via SMTP - MODE STRICT"""
    try:
        smtp = smtplib.SMTP(timeout=8)
        smtp.connect(mx_host, 25)
        smtp.helo('verify.local')
        smtp.mail('test@verify.local')
        code, message = smtp.rcpt(email)
        smtp.quit()
        
        # Seulement 250 et 251 sont acceptés en mode strict
        if code in [250, 251]:
            return True, "ok"
        else:
            return False, f"reject_{code}"
            
    except smtplib.SMTPServerDisconnected:
        return False, "disconnected"
    except smtplib.SMTPConnectError:
        return False, "connect_error"
    except socket.timeout:
        return False, "timeout"
    except Exception as e:
        return False, "error"


def validate_email(email: str, mx_cache: dict, smtp_results: dict) -> tuple:
    """Validation STRICTE d'un email"""
    if not email or not email.strip():
        return False, "vide"
    
    email = email.strip().lower()
    
    # Syntaxe
    if not EMAIL_REGEX.match(email):
        return False, "syntaxe"
    
    # Vérifier caractères suspects
    if '..' in email or email.startswith('.') or '@.' in email:
        return False, "syntaxe"
    
    try:
        local, domain = email.split('@')
    except:
        return False, "syntaxe"
    
    # Local part trop court ou trop long
    if len(local) < 2 or len(local) > 64:
        return False, "local_invalide"
    
    # Domaine blacklisté
    if domain in BLACKLIST_DOMAINS:
        return False, "jetable"
    
    # Vérifier MX
    if domain not in mx_cache:
        mx_cache[domain] = get_mx_host(domain)
    
    mx_host = mx_cache[domain]
    if not mx_host:
        return False, "no_mx"
    
    # Pour les providers fiables, on accepte directement
    if domain in TRUSTED_PROVIDERS:
        return True, "ok"
    
    # Pour les autres domaines, vérification SMTP stricte
    if email not in smtp_results:
        is_valid, reason = verify_email_smtp(email, mx_host)
        smtp_results[email] = (is_valid, reason)
    
    return smtp_results[email]


def main():
    print(f"📧 Lecture: {FILE}")
    print("🔒 MODE STRICT ACTIVÉ - Suppression de tout ce qui est douteux\n")
    
    with open(FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=DELIMITER)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"📊 {len(rows)} lignes à traiter")
    print(f"📋 Colonnes: {fieldnames}\n")
    
    # Trouver la colonne email
    email_col = None
    for col in fieldnames:
        if 'email' in col.lower():
            email_col = col
            break
    
    if not email_col:
        print("❌ Colonne email non trouvée!")
        return
    
    print(f"📧 Colonne email détectée: '{email_col}'\n")
    
    mx_cache = {}
    smtp_results = {}
    valid_rows = []
    npai_rows = []
    stats = defaultdict(int)
    
    for i, row in enumerate(rows):
        email = row.get(email_col, '').strip()
        is_valid, reason = validate_email(email, mx_cache, smtp_results)
        
        if is_valid:
            valid_rows.append(row)
            stats['valides'] += 1
        else:
            row['raison_npai'] = reason
            npai_rows.append(row)
            stats[reason] += 1
        
        if (i + 1) % 100 == 0:
            pct_clean = (stats['valides'] / (i+1)) * 100
            print(f"  {i+1}/{len(rows)} - Valides: {stats['valides']} ({pct_clean:.0f}%) - NPAI: {len(npai_rows)}")
    
    # Écrire fichier nettoyé
    with open(OUTPUT_VALID, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=DELIMITER)
        writer.writeheader()
        writer.writerows(valid_rows)
    
    # Écrire NPAI
    if npai_rows:
        npai_fields = list(fieldnames) + ['raison_npai']
        with open(OUTPUT_NPAI, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=npai_fields, delimiter=DELIMITER)
            writer.writeheader()
            writer.writerows(npai_rows)
    
    # Stats finales
    pct_valid = (stats['valides'] / len(rows)) * 100 if rows else 0
    pct_npai = (len(npai_rows) / len(rows)) * 100 if rows else 0
    
    print(f"\n{'='*60}")
    print(f"✅ NETTOYAGE STRICT TERMINÉ")
    print(f"{'='*60}")
    print(f"📊 Total initial:    {len(rows)}")
    print(f"✅ Emails valides:   {stats['valides']} ({pct_valid:.1f}%)")
    print(f"❌ NPAI supprimés:   {len(npai_rows)} ({pct_npai:.1f}%)")
    print(f"\n📁 Fichier propre: {OUTPUT_VALID}")
    print(f"📁 NPAI sauvés:    {OUTPUT_NPAI}")
    
    print(f"\n📋 Détail des suppressions:")
    for reason, count in sorted(stats.items(), key=lambda x: -x[1]):
        if reason != 'valides':
            print(f"   {reason}: {count}")


if __name__ == "__main__":
    main()


