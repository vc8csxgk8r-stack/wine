from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = '/data/cave.db'

# Initialisation DB au démarrage — exécuté par Gunicorn au chargement du module
os.makedirs('/data', exist_ok=True)
_conn = sqlite3.connect(DB_PATH)
_conn.execute('''
    CREATE TABLE IF NOT EXISTS vins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        region TEXT,
        appellation TEXT,
        cepage TEXT,
        millesime INTEGER,
        quantite INTEGER DEFAULT 1,
        prix_achat REAL,
        note TEXT,
        date_ajout TEXT DEFAULT CURRENT_TIMESTAMP,
        image_url TEXT,
        type_vin TEXT DEFAULT "Rouge"
    )
''')
_conn.commit()
_conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs('/data', exist_ok=True)
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            region TEXT,
            appellation TEXT,
            cepage TEXT,
            millesime INTEGER,
            quantite INTEGER DEFAULT 1,
            prix_achat REAL,
            note TEXT,
            date_ajout TEXT DEFAULT CURRENT_TIMESTAMP,
            image_url TEXT,
            type_vin TEXT DEFAULT 'Rouge'
        )
    ''')
    conn.commit()
    conn.close()

# Données de maturité par région/appellation (base de connaissance viticole)
MATURITE_DATA = {
    # ── France ───────────────────────────────────────────────
    "Bordeaux": {
        "Rouge": {"debut": 5, "apogee_debut": 10, "apogee_fin": 25, "declin": 35},
        "Blanc": {"debut": 3, "apogee_debut": 7, "apogee_fin": 15, "declin": 20},
    },
    "Bourgogne": {
        "Rouge": {"debut": 5, "apogee_debut": 8, "apogee_fin": 20, "declin": 30},
        "Blanc": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 25},
    },
    "Champagne": {
        "Blanc": {"debut": 3, "apogee_debut": 7, "apogee_fin": 20, "declin": 30},
        "Rosé": {"debut": 3, "apogee_debut": 5, "apogee_fin": 15, "declin": 20},
    },
    "Rhône": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 20, "declin": 30},
        "Blanc": {"debut": 2, "apogee_debut": 5, "apogee_fin": 12, "declin": 18},
    },
    "Loire": {
        "Blanc": {"debut": 3, "apogee_debut": 7, "apogee_fin": 20, "declin": 30},
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 20},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 5, "declin": 8},
    },
    "Alsace": {
        "Blanc": {"debut": 3, "apogee_debut": 7, "apogee_fin": 20, "declin": 30},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 5, "declin": 8},
    },
    "Languedoc-Roussillon": {
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 22},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 4, "declin": 6},
    },
    "Provence": {
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 5, "declin": 8},
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 20},
        "Blanc": {"debut": 2, "apogee_debut": 3, "apogee_fin": 8, "declin": 12},
    },
    "Sud-Ouest": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 20, "declin": 28},
        "Blanc": {"debut": 2, "apogee_debut": 5, "apogee_fin": 12, "declin": 18},
        "Mousseux": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
    },
    "Jura": {
        "Blanc": {"debut": 4, "apogee_debut": 8, "apogee_fin": 25, "declin": 40},
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 22},
    },
    "Savoie": {
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
        "Rouge": {"debut": 2, "apogee_debut": 5, "apogee_fin": 12, "declin": 18},
    },
    "Corse": {
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 20},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 5, "declin": 7},
    },
    # ── Espagne ──────────────────────────────────────────────
    "Rioja": {
        "Rouge": {"debut": 5, "apogee_debut": 8, "apogee_fin": 20, "declin": 28},
        "Blanc": {"debut": 2, "apogee_debut": 5, "apogee_fin": 12, "declin": 18},
    },
    "Ribera del Duero": {
        "Rouge": {"debut": 5, "apogee_debut": 10, "apogee_fin": 22, "declin": 30},
    },
    "Priorat": {
        "Rouge": {"debut": 5, "apogee_debut": 10, "apogee_fin": 25, "declin": 35},
    },
    # ── Italie ───────────────────────────────────────────────
    "Toscane": {
        "Rouge": {"debut": 5, "apogee_debut": 10, "apogee_fin": 25, "declin": 35},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
    },
    "Piémont": {
        "Rouge": {"debut": 6, "apogee_debut": 12, "apogee_fin": 30, "declin": 40},
        "Mousseux": {"debut": 1, "apogee_debut": 3, "apogee_fin": 8, "declin": 12},
    },
    "Vénétie": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 20, "declin": 28},
        "Blanc": {"debut": 1, "apogee_debut": 3, "apogee_fin": 8, "declin": 12},
        "Mousseux": {"debut": 1, "apogee_debut": 2, "apogee_fin": 6, "declin": 10},
    },
    # ── Nouveau Monde ─────────────────────────────────────────
    "Napa Valley": {
        "Rouge": {"debut": 5, "apogee_debut": 10, "apogee_fin": 20, "declin": 30},
        "Blanc": {"debut": 2, "apogee_debut": 5, "apogee_fin": 10, "declin": 15},
    },
    "Mendoza": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 18, "declin": 25},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 8, "declin": 12},
    },
    "Barossa Valley": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 20, "declin": 28},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 14},
    },
    "Marlborough": {
        "Blanc": {"debut": 1, "apogee_debut": 3, "apogee_fin": 8, "declin": 12},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 4, "declin": 6},
    },
    # ── Autres ───────────────────────────────────────────────
    "Portugal": {
        "Rouge": {"debut": 4, "apogee_debut": 8, "apogee_fin": 20, "declin": 28},
        "Blanc": {"debut": 1, "apogee_debut": 3, "apogee_fin": 8, "declin": 12},
        "Mousseux": {"debut": 2, "apogee_debut": 5, "apogee_fin": 15, "declin": 25},
    },
    "Allemagne": {
        "Blanc": {"debut": 3, "apogee_debut": 8, "apogee_fin": 25, "declin": 40},
        "Mousseux": {"debut": 2, "apogee_debut": 5, "apogee_fin": 15, "declin": 25},
    },
    "Default": {
        "Rouge": {"debut": 3, "apogee_debut": 6, "apogee_fin": 15, "declin": 20},
        "Blanc": {"debut": 2, "apogee_debut": 4, "apogee_fin": 10, "declin": 15},
        "Rosé": {"debut": 1, "apogee_debut": 2, "apogee_fin": 4, "declin": 6},
        "Mousseux": {"debut": 1, "apogee_debut": 3, "apogee_fin": 10, "declin": 15},
        "Liquoreux": {"debut": 5, "apogee_debut": 10, "apogee_fin": 30, "declin": 50},
    }
}

# Cotes des grands millésimes par région
MILLESIMES_NOTES = {
    "Bordeaux": {
        2022: 98, 2021: 88, 2020: 98, 2019: 97, 2018: 96, 2017: 88, 2016: 99,
        2015: 97, 2014: 92, 2013: 82, 2012: 88, 2011: 88, 2010: 100, 2009: 99,
        2008: 89, 2007: 85, 2006: 90, 2005: 100, 2004: 89, 2003: 91, 2001: 90,
        2000: 99, 1998: 90, 1996: 93, 1995: 94, 1990: 100, 1989: 97, 1988: 90,
        1986: 89, 1985: 90, 1982: 100
    },
    "Bourgogne": {
        2022: 96, 2021: 97, 2020: 97, 2019: 98, 2018: 93, 2017: 90, 2016: 94,
        2015: 96, 2014: 90, 2013: 87, 2012: 90, 2011: 88, 2010: 96, 2009: 95,
        2008: 90, 2007: 91, 2006: 89, 2005: 99, 2004: 88, 2003: 92, 2002: 94,
        2001: 85, 1999: 94, 1996: 98, 1995: 93, 1993: 90, 1990: 99, 1988: 95
    },
    "Champagne": {
        2018: 97, 2015: 98, 2013: 94, 2012: 97, 2008: 99, 2006: 94, 2004: 95,
        2002: 98, 1996: 100, 1995: 96, 1990: 99, 1988: 97, 1985: 96, 1982: 99
    },
    "Rhône": {
        2022: 98, 2021: 94, 2020: 99, 2019: 99, 2018: 95, 2017: 91, 2016: 93,
        2015: 95, 2014: 88, 2013: 90, 2012: 97, 2011: 91, 2010: 99, 2009: 100,
        2007: 98, 2006: 91, 2005: 95, 2004: 88, 2003: 95, 2001: 95, 1999: 94
    },
    "Loire": {
        2022: 95, 2021: 90, 2020: 94, 2019: 97, 2018: 92, 2017: 88, 2016: 90,
        2015: 95, 2014: 90, 2010: 96, 2009: 94, 2005: 95, 2003: 90, 2002: 94,
        1997: 96, 1996: 95, 1990: 98, 1989: 97
    },
    "Alsace": {
        2021: 94, 2020: 96, 2019: 97, 2018: 96, 2017: 90, 2016: 92, 2015: 96,
        2014: 91, 2010: 97, 2008: 96, 2007: 93, 2005: 98, 2001: 97, 2000: 94,
        1998: 98, 1990: 99, 1989: 97
    },
    "Languedoc-Roussillon": {
        2022: 94, 2021: 90, 2020: 95, 2019: 96, 2018: 93, 2017: 89, 2016: 91,
        2015: 94, 2014: 88, 2012: 93, 2010: 94, 2009: 95, 2007: 93, 2005: 95,
        2003: 91, 2001: 90
    },
    "Provence": {
        2022: 93, 2021: 91, 2020: 94, 2019: 95, 2018: 92, 2017: 89, 2016: 90,
        2015: 93, 2013: 90, 2012: 91, 2010: 93, 2009: 94, 2007: 90
    },
    "Sud-Ouest": {
        2022: 94, 2021: 89, 2020: 95, 2019: 96, 2018: 93, 2016: 92, 2015: 95,
        2014: 89, 2010: 95, 2009: 96, 2005: 95, 2003: 92, 2000: 94, 1995: 93
    },
    "Jura": {
        2021: 95, 2020: 94, 2019: 96, 2018: 93, 2015: 95, 2014: 90, 2010: 94,
        2009: 95, 2005: 96, 2002: 93
    },
    "Rioja": {
        2022: 96, 2020: 97, 2019: 98, 2018: 95, 2017: 90, 2016: 96, 2015: 97,
        2014: 91, 2012: 93, 2010: 98, 2009: 96, 2005: 97, 2004: 94, 2001: 96,
        1995: 98, 1994: 97, 1991: 96
    },
    "Ribera del Duero": {
        2022: 95, 2020: 96, 2019: 97, 2018: 94, 2016: 95, 2015: 96, 2012: 94,
        2010: 97, 2009: 95, 2005: 96, 2004: 95, 1999: 97, 1994: 98
    },
    "Toscane": {
        2021: 97, 2020: 96, 2019: 97, 2018: 93, 2016: 98, 2015: 97, 2013: 96,
        2012: 93, 2011: 91, 2010: 95, 2009: 93, 2007: 97, 2006: 94, 2004: 96,
        2001: 97, 1999: 97, 1997: 99, 1995: 95, 1990: 99, 1988: 97, 1985: 98
    },
    "Piémont": {
        2021: 97, 2020: 96, 2019: 99, 2018: 94, 2017: 90, 2016: 100, 2015: 97,
        2014: 86, 2013: 95, 2012: 92, 2010: 98, 2008: 95, 2006: 93, 2004: 97,
        2001: 96, 2000: 97, 1999: 95, 1996: 97, 1990: 99, 1989: 98
    },
    "Napa Valley": {
        2022: 95, 2021: 93, 2019: 97, 2018: 96, 2016: 97, 2015: 95, 2014: 96,
        2013: 95, 2012: 97, 2010: 94, 2009: 95, 2007: 96, 2005: 95, 2002: 96,
        2001: 95, 1997: 97, 1994: 98, 1991: 98
    },
    "Mendoza": {
        2021: 94, 2019: 96, 2018: 95, 2017: 91, 2016: 94, 2015: 95, 2013: 93,
        2010: 96, 2009: 95, 2007: 96, 2006: 94
    },
    "Default": {
        2022: 92, 2021: 90, 2020: 93, 2019: 94, 2018: 91, 2017: 88, 2016: 92,
        2015: 94, 2014: 88, 2013: 84, 2012: 88, 2011: 87, 2010: 93, 2009: 94,
        2008: 86, 2007: 87, 2006: 88, 2005: 96, 2004: 86, 2003: 88
    }
}

def get_maturite_info(region, type_vin, millesime):
    age = datetime.now().year - millesime
    
    # Trouver les données de maturité
    region_data = MATURITE_DATA.get(region, MATURITE_DATA["Default"])
    maturite = region_data.get(type_vin, MATURITE_DATA["Default"].get(type_vin, MATURITE_DATA["Default"]["Rouge"]))
    
    # Note du millésime
    region_notes = MILLESIMES_NOTES.get(region, MILLESIMES_NOTES["Default"])
    note_millesime = region_notes.get(millesime, 88)  # 88 par défaut
    
    # Calculer le statut de maturité
    if age < maturite["debut"]:
        statut = "trop_jeune"
        label = "Trop jeune"
        couleur = "#3b82f6"
        pourcentage = int((age / maturite["debut"]) * 30)
        conseil = f"Attendre encore {maturite['debut'] - age} an(s) minimum avant d'ouvrir."
    elif age < maturite["apogee_debut"]:
        statut = "en_evolution"
        label = "En évolution"
        couleur = "#f59e0b"
        p = (age - maturite["debut"]) / (maturite["apogee_debut"] - maturite["debut"])
        pourcentage = int(30 + p * 40)
        conseil = f"Sera à son apogée dans {maturite['apogee_debut'] - age} an(s)."
    elif age <= maturite["apogee_fin"]:
        statut = "apogee"
        label = "À l'apogée"
        couleur = "#10b981"
        pourcentage = 100
        conseil = "Moment idéal pour déguster ! Encore buvable {0} an(s).".format(maturite["apogee_fin"] - age)
    elif age <= maturite["declin"]:
        statut = "declin"
        label = "En déclin"
        couleur = "#f97316"
        p = (age - maturite["apogee_fin"]) / (maturite["declin"] - maturite["apogee_fin"])
        pourcentage = int(100 - p * 40)
        conseil = f"À boire rapidement, encore {maturite['declin'] - age} an(s) de garde possible."
    else:
        statut = "trop_vieux"
        label = "Dépassé"
        couleur = "#ef4444"
        pourcentage = 20
        conseil = "Ce vin a probablement dépassé son apogée."
    
    return {
        "statut": statut,
        "label": label,
        "couleur": couleur,
        "pourcentage": pourcentage,
        "conseil": conseil,
        "age": age,
        "note_millesime": note_millesime,
        "apogee_debut": millesime + maturite["apogee_debut"],
        "apogee_fin": millesime + maturite["apogee_fin"],
    }

def search_wine_price(nom, millesime, region=""):
    """Recherche le prix via l'API publique Wine-Searcher ou estimation"""
    try:
        # Utiliser l'API Open Drinks / Wine données libres
        query = f"{nom} {millesime}"
        url = f"https://api.api-ninjas.com/v1/wine?name={requests.utils.quote(nom)}"
        # On utilise une estimation basée sur la note du millésime
        region_notes = MILLESIMES_NOTES.get(region, MILLESIMES_NOTES["Default"])
        note = region_notes.get(millesime, 88)
        
        # Formule d'estimation de prix
        base_price = 15
        if note >= 98:
            multiplier = 20
        elif note >= 96:
            multiplier = 10
        elif note >= 94:
            multiplier = 5
        elif note >= 92:
            multiplier = 3
        elif note >= 90:
            multiplier = 2
        else:
            multiplier = 1.2
        
        age = datetime.now().year - millesime
        age_multiplier = 1 + (age * 0.05)  # +5% par an de vieillissement
        
        prix_estime = round(base_price * multiplier * age_multiplier, 2)
        return {
            "prix_estime": prix_estime,
            "source": "estimation",
            "note_millesime": note
        }
    except Exception as e:
        return {"prix_estime": None, "source": "erreur", "error": str(e)}

@app.route('/api/vins', methods=['GET'])
def get_vins():
    conn = get_db()
    vins = conn.execute('SELECT * FROM vins ORDER BY date_ajout DESC').fetchall()
    result = []
    for v in vins:
        vin = dict(v)
        if vin['millesime']:
            vin['maturite'] = get_maturite_info(
                vin.get('region', 'Default'),
                vin.get('type_vin', 'Rouge'),
                vin['millesime']
            )
            # Prix marché estimé basé sur note du millésime et âge
            prix_info = search_wine_price(
                vin.get('nom', ''),
                vin['millesime'],
                vin.get('region', 'Default')
            )
            vin['prix_estime'] = prix_info.get('prix_estime')
        result.append(vin)
    conn.close()
    return jsonify(result)

@app.route('/api/vins', methods=['POST'])
def add_vin():
    data = request.json
    conn = get_db()
    conn.execute('''
        INSERT INTO vins (nom, region, appellation, cepage, millesime, quantite, prix_achat, note, image_url, type_vin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('nom'), data.get('region'), data.get('appellation'),
        data.get('cepage'), data.get('millesime'), data.get('quantite', 1),
        data.get('prix_achat'), data.get('note'), data.get('image_url'),
        data.get('type_vin', 'Rouge')
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/vins/<int:id>', methods=['DELETE'])
def delete_vin(id):
    conn = get_db()
    conn.execute('DELETE FROM vins WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/vins/<int:id>', methods=['PUT'])
def update_vin(id):
    data = request.json
    conn = get_db()
    conn.execute('''
        UPDATE vins SET nom=?, region=?, appellation=?, cepage=?, millesime=?,
        quantite=?, prix_achat=?, note=?, type_vin=?
        WHERE id=?
    ''', (
        data.get('nom'), data.get('region'), data.get('appellation'),
        data.get('cepage'), data.get('millesime'), data.get('quantite'),
        data.get('prix_achat'), data.get('note'), data.get('type_vin'), id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/recherche-vin', methods=['POST'])
def recherche_vin():
    data = request.json
    nom = data.get('nom', '')
    millesime = data.get('millesime')
    region = data.get('region', 'Default')
    
    prix_info = search_wine_price(nom, millesime, region)
    
    maturite_info = None
    if millesime:
        maturite_info = get_maturite_info(region, data.get('type_vin', 'Rouge'), int(millesime))
    
    return jsonify({
        "prix": prix_info,
        "maturite": maturite_info
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    stats = {}
    stats['total_bouteilles'] = conn.execute('SELECT SUM(quantite) FROM vins').fetchone()[0] or 0
    stats['total_vins'] = conn.execute('SELECT COUNT(*) FROM vins').fetchone()[0] or 0
    stats['valeur_estimee'] = conn.execute('SELECT SUM(prix_achat * quantite) FROM vins').fetchone()[0] or 0
    stats['par_type'] = {}
    for row in conn.execute('SELECT type_vin, COUNT(*) as cnt FROM vins GROUP BY type_vin'):
        stats['par_type'][row[0]] = row[1]
    conn.close()
    return jsonify(stats)

@app.route('/api/millesimes', methods=['GET'])
def get_millesimes():
    """Retourne les notes des millésimes pour toutes les régions"""
    return jsonify(MILLESIMES_NOTES)

@app.route('/api/regions', methods=['GET'])
def get_regions():
    regions = list(MATURITE_DATA.keys())
    regions.remove("Default")
    return jsonify(regions)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
