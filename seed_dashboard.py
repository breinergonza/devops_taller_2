#!/usr/bin/env python
"""
Script para popular la base de datos con datos de ejemplo para el dashboard.
"""
import os
import sys
from datetime import datetime, timedelta

# Asegurar que el directorio está en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import create_app, db
from src.models.blacklist import Blacklist

# Crear app
app = create_app()

def seed_database():
    """Agrega datos de ejemplo a la base de datos."""
    with app.app_context():
        # Borrar datos existentes
        Blacklist.query.delete()
        db.session.commit()

        # Emails de ejemplo para el seed
        domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'example.com', 'spam.com']
        names = ['spam', 'phishing', 'malware', 'botnet', 'scam', 'fraud', 'abuse']
        reasons = ['phishing', 'spam', 'malware', 'botnet', 'fraud', 'abuse']

        # Crear 50 registros de ejemplo con timestamps distribuidos en las últimas 24 horas
        now = datetime.utcnow()
        entries = []

        for i in range(50):
            hours_ago = (i % 24)
            email = f"{names[i % len(names)]}{i}@{domains[i % len(domains)]}"
            reason = reasons[i % len(reasons)]
            timestamp = now - timedelta(hours=hours_ago, minutes=(i % 60))

            entry = Blacklist(
                email=email,
                app_uuid=f"app-{i:04d}-uuid-{i:04d}",
                blocked_reason=reason,
                created_at=timestamp,
                request_ip=f"192.168.{i % 256}.{(i * 7) % 256}"
            )
            entries.append(entry)

        db.session.bulk_save_objects(entries)
        db.session.commit()

        print(f"✓ Base de datos poblada con {len(entries)} registros de ejemplo")
        print(f"✓ Total de registros en blacklist: {Blacklist.query.count()}")

if __name__ == "__main__":
    seed_database()
