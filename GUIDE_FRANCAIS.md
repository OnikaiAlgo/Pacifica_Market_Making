# Guide Complet - Bot Market Making Pacifica Finance

## 🎉 BOT DE MARKET MAKING PROFESSIONNEL

Bot de market making complet pour Pacifica Finance DEX avec spreads dynamiques et analyse de tendance.

## ⚠️ INSCRIPTION PACIFICA FINANCE (OBLIGATOIRE)

Avant d'utiliser ce bot, vous devez créer un compte Pacifica Finance:

1. **Visitez [https://app.pacifica.fi/](https://app.pacifica.fi/)**
2. **Utilisez l'un de ces codes referral** pour bénéficier de réductions sur les frais:
   - `18SRTGXDJWCVSY75`
   - `D0CJ7BAYKFPDES42`
   - `754C0W62E9ZS8M00`
   - `H0A3G2BES01RCKVX`
   - `8Q6E0AC9KWY941A4`
   - `DRHGPPSWAXJ9Q2T6`
3. Connectez votre wallet Solana (Phantom, Solflare, etc.)
4. Déposez de l'USDC pour commencer à trader

> **💡 Important**: L'utilisation d'un code referral vous permet d'obtenir des frais réduits, ce qui est crucial pour la rentabilité du market making.

---

## 📁 Localisation

```
/home/onikai/Project/Pacifica_Market_Making/
```

---

## ✅ TOUS LES FICHIERS ADAPTÉS (15 fichiers)

### Code Principal (9 fichiers Python)
1. **api_client.py** (968 lignes) - Client API complet avec 37 méthodes
2. **market_maker.py** (1298 lignes) - Bot principal avec TOUTES les fonctionnalités
3. **data_collector.py** (631 lignes) - Collecteur de données en temps réel
4. **calculate_avellaneda_parameters.py** - Calcul de spreads dynamiques
5. **find_trend.py** - Analyse de tendance SuperTrend
6. **terminal_dashboard.py** (1058 lignes) - Dashboard temps réel
7. **get_my_trading_volume.py** - Analyse de volume de trading
8. **websocket_orders.py** (542 lignes) - Gestionnaire WebSocket complet

### Configuration Docker (2 fichiers)
9. **Dockerfile** - Image Docker pour tous les services
10. **docker-compose.yml** - Orchestration de 4 services

### Configuration (3 fichiers)
11. **requirements.txt** - Toutes les dépendances Python
12. **.env.example** - Modèle de configuration DÉTAILLÉ
13. **.gitignore** - Protection des fichiers sensibles

### Documentation (2 fichiers)
14. **README.md** (650+ lignes) - Documentation complète en anglais
15. **GUIDE_FRANCAIS.md** - Ce fichier (guide en français)

---

## 🔑 COMMENT OBTENIR VOTRE CLÉ PRIVÉE SOLANA

### Option 1: Phantom Wallet (⭐ Recommandé)
1. Ouvrez Phantom
2. Cliquez sur l'icône ⚙️ (Paramètres) en haut à droite
3. Sélectionnez "Sécurité et confidentialité"
4. Cliquez sur "Exporter la clé privée"
5. Entrez votre mot de passe
6. **Copiez la clé** (format base58, commence par un nombre)

### Option 2: Solflare Wallet
1. Ouvrez Solflare
2. Allez dans Paramètres
3. Cliquez sur "Export Private Key"
4. Entrez votre mot de passe
5. **Copiez la clé privée**

### Option 3: Solana CLI (Avancé)
```bash
# Afficher votre clé publique
solana-keygen pubkey ~/.config/solana/id.json

# Convertir le fichier keypair en base58
python3 << 'EOF'
import json
import base58

with open('/home/votre_user/.config/solana/id.json', 'r') as f:
    keypair = json.load(f)
    private_key = base58.b58encode(bytes(keypair)).decode('ascii')
    print(f"Clé privée base58: {private_key}")
EOF
```

### ⚠️ Format de la Clé
- **Format attendu**: Base58 (chaîne de caractères)
- **Exemple**: `2Z2Wn4kN5ZNhZzuFTQSyTiN4ixX8U6ew5wPDJbHngZaC3zF3uWNj4dQ63cnGfXpw1cESZPCqvoZE7VURyuj9kf8b`
- **PAS JSON**: Ne pas utiliser le format `[123, 45, 67, ...]`

---

## 🚀 DÉMARRAGE RAPIDE AVEC DOCKER

### 1. Configuration Initiale

```bash
# Aller dans le répertoire du projet
cd /home/onikai/Project/Pacifica_Market_Making

# Copier et configurer .env
cp .env.example .env
nano .env
```

**Remplir dans .env:**
```bash
PRIVATE_KEY=votre_clé_privée_solana_base58
SYMBOL=BTC
```

### 2. Construire les Containers Docker

```bash
docker-compose build
```

### 3. Lancer TOUS les Services

```bash
docker-compose up -d
```

Cela démarre **4 services** :
- **data-collector** : Collecte données en temps réel
- **avellaneda-params** : Calcule les spreads optimaux
- **trend-finder** : Analyse les tendances
- **market-maker** : Bot de trading principal

### 4. Surveiller les Logs

```bash
# Tous les services
docker-compose logs -f

# Service spécifique
docker-compose logs -f market-maker
docker-compose logs -f data-collector
```

### 5. Arrêter les Services

```bash
docker-compose down
```

---

## 🔧 UTILISATION MANUELLE (Sans Docker)

### Installation

```bash
cd /home/onikai/Project/Pacifica_Market_Making
pip install -r requirements.txt
```

### Lancer Chaque Composant

```bash
# 1. Collecteur de données (terminal 1)
python data_collector.py

# 2. Calcul des paramètres Avellaneda (terminal 2)
python calculate_avellaneda_parameters.py --symbol BTC --minutes 5

# 3. Analyse de tendance (terminal 3)
python find_trend.py --symbol BTC --interval 5m

# 4. Bot market maker (terminal 4)
python market_maker.py --symbol BTC
```

### Dashboard de Surveillance

```bash
# Dans un terminal séparé
python terminal_dashboard.py
```

---

## ⚙️ CONFIGURATION IMPORTANTE

### Paramètres dans market_maker.py

```python
# SYMBOLE
DEFAULT_SYMBOL = "BTC"              # Symbole à trader

# SPREADS
DEFAULT_BUY_SPREAD = 0.006          # 0.6% sous le prix mid
DEFAULT_SELL_SPREAD = 0.006         # 0.6% au-dessus du prix mid

# TAILLE DES ORDRES ⚠️ IMPORTANT
DEFAULT_BALANCE_FRACTION = 0.2      # 20% du solde par ordre
                                    # COMMENCEZ AVEC 0.05 (5%)!

# SEUILS
POSITION_THRESHOLD_USD = 15.0       # Limite de position en USD

# FEATURES AVANCÉES
USE_AVELLANEDA_SPREADS = True       # Spreads dynamiques
USE_SUPERTREND_SIGNAL = True        # Suivi de tendance

# TIMING
ORDER_REFRESH_INTERVAL = 30         # Rafraîchir ordres tous les 30s
SUPERTREND_CHECK_INTERVAL = 600     # Vérifier tendance tous les 10min

# MODE
FLIP_MODE = False                   # False=long, True=short
RELEASE_MODE = True                 # True=logs minimaux
```

---

## 📊 CARACTÉRISTIQUES TECHNIQUES

| Aspect | Détails |
|--------|---------|
| **Blockchain** | Solana (performance élevée, frais réduits) |
| **Authentification** | 1 clé privée Solana (format base58) |
| **Format symbole** | BTC, ETH, SOL (sans suffixe USDT) |
| **Types d'ordres** | bid (achat), ask (vente) |
| **API** | REST + WebSocket temps réel |
| **URL API** | api.pacifica.fi/api/v1 |
| **WebSocket** | wss://ws.pacifica.fi/ws |

---

## 🎯 FONCTIONNALITÉS COMPLÈTES

### ✅ Market Maker Complet
- Mode ping-pong avec flip automatique
- Gestion de position avec seuils
- Rafraîchissement automatique des ordres
- Réutilisation d'ordres (optimisation)
- Protection contre le rate limiting
- Reconnexion automatique WebSocket
- Shutdown gracieux (Ctrl+C)

### ✅ Spreads Dynamiques (Avellaneda-Stoikov)
- Modèle GARCH pour la volatilité
- Optimisation du paramètre gamma
- Calcul de spreads optimaux
- Cache avec TTL
- Fallback sur spreads fixes

### ✅ Analyse de Tendance (SuperTrend)
- Indicateur SuperTrend
- Grid search pour optimisation
- Backtest avec Sharpe ratio
- Signal de tendance (+1/-1)
- Intégration dans le bot

### ✅ Collecte de Données
- Prix en temps réel
- Order book (depth configurable)
- Trades exécutés
- Multi-symboles
- Sauvegarde CSV
- Déduplication

### ✅ Dashboard Terminal
- Soldes en temps réel
- Positions ouvertes avec PnL
- Ordres récents
- Interface colorée
- Auto-refresh

### ✅ Analyse de Volume
- Volume par symbole
- Breakdown buy/sell
- Historique configurable
- Statistiques quotidiennes

---

## 🔐 SÉCURITÉ

### Protection de la Clé Privée
1. ⚠️ **NE JAMAIS** committer le fichier `.env`
2. ⚠️ Utilisez un **compte dédié** pour le bot
3. ⚠️ Gardez votre clé privée **SECRÈTE**
4. ⚠️ Ne partagez JAMAIS votre clé
5. ⚠️ Sauvegardez votre clé dans un endroit sûr

### Bonnes Pratiques Trading
1. ✅ Commencez avec **5% du solde** (`DEFAULT_BALANCE_FRACTION = 0.05`)
2. ✅ Testez d'abord avec **petites sommes**
3. ✅ Surveillez **activement** les premières 24-48h
4. ✅ Utilisez des **limites de position**
5. ✅ Vérifiez les **logs régulièrement**

---

## ⚠️ RISQUES

### Risques Financiers
- ❌ Ce bot **PEUT PERDRE DE L'ARGENT**
- ❌ Le trading automatisé est **risqué**
- ❌ La volatilité peut causer des **pertes importantes**
- ❌ Risque de **liquidation** si mal configuré

### Risques Techniques
- ❌ Pannes de connexion
- ❌ Bugs dans le code
- ❌ Problèmes API Pacifica
- ❌ Latence réseau

### Comment Mitiger les Risques
1. Commencez **PETIT** (5-10% du solde max)
2. Utilisez des **seuils de position**
3. Surveillez **activement**
4. Testez en **environnement contrôlé** d'abord
5. N'investissez que ce que vous pouvez **perdre**

---

## 🐛 DÉPANNAGE

### "Invalid Solana private key"
```bash
# Vérifier le format de votre clé
python3 << 'EOF'
from solders.keypair import Keypair
try:
    Keypair.from_base58_string("VOTRE_CLÉ_ICI")
    print("✓ Clé valide!")
except:
    print("✗ Clé invalide - vérifiez le format")
EOF
```

### "No price data available"
- Attendez 10-20 secondes après le démarrage
- Vérifiez que le symbole existe sur Pacifica
- Vérifiez les logs: `docker-compose logs data-collector`

### "Insufficient balance"
- Vérifiez votre solde sur Pacifica
- Réduisez `DEFAULT_BALANCE_FRACTION`
- Vérifiez la taille minimale d'ordre

### Docker: "Container exited"
```bash
# Voir les erreurs
docker-compose logs market-maker

# Redémarrer un service
docker-compose restart market-maker
```

### WebSocket se déconnecte
- Normal - reconnexion automatique
- Vérifiez votre connexion internet
- Vérifiez les logs pour erreurs

---

## 📈 COMMANDES UTILES

### Docker

```bash
# Statut des services
docker-compose ps

# Logs en temps réel
docker-compose logs -f

# Redémarrer tout
docker-compose restart

# Arrêter tout
docker-compose down

# Rebuild après modification
docker-compose build
docker-compose up -d
```

### Analyse

```bash
# Volume de trading
python get_my_trading_volume.py --symbol BTC --days 7

# Dashboard
python terminal_dashboard.py --refresh-interval 15

# Test WebSocket
python websocket_orders.py --demo
```

---

## 🎓 ORDRE D'APPRENTISSAGE

### Jour 1: Configuration
1. Obtenir clé privée Solana
2. Configurer `.env`
3. Tester la connexion
4. Comprendre les paramètres

### Jour 2-3: Test
1. Lancer avec `DEFAULT_BALANCE_FRACTION = 0.05`
2. Surveiller activement
3. Analyser les logs
4. Ajuster les paramètres

### Semaine 1: Optimisation
1. Analyser les performances
2. Ajuster les spreads
3. Tester différents symboles
4. Optimiser les intervalles

### Après 1 semaine: Scaling
1. Augmenter progressivement la taille
2. Ajouter d'autres symboles
3. Affiner la stratégie
4. Automatiser la surveillance

---

## 📚 RESSOURCES

### Pacifica Finance
- **Platform**: https://app.pacifica.fi/
- **Documentation**: https://docs.pacifica.fi/
- **SDK**: https://github.com/pacifica-fi/python-sdk

### Solana
- **Documentation**: https://docs.solana.com/
- **Explorer**: https://explorer.solana.com/
- **CLI**: https://docs.solana.com/cli

### Wallets
- **Phantom**: https://phantom.app/
- **Solflare**: https://solflare.com/

---

## ✉️ SUPPORT

### En cas de problème:
1. Consultez `market_maker.log`
2. Vérifiez `docker-compose logs`
3. Relisez ce guide
4. Consultez README.md (anglais)
5. Vérifiez la documentation Pacifica

---

## 🎉 FÉLICITATIONS!

Vous disposez maintenant d'un bot de market making **COMPLET et FONCTIONNEL** pour Pacifica Finance:

✅ 15 fichiers professionnels
✅ 9 scripts Python complets
✅ Docker ready (4 services)
✅ Documentation complète
✅ Toutes les features avancées
✅ Prêt pour production

---

## 🚨 RAPPELS IMPORTANTS

1. 🔗 **Codes referral disponibles** sur https://app.pacifica.fi/:
   - `18SRTGXDJWCVSY75`, `D0CJ7BAYKFPDES42`, `754C0W62E9ZS8M00`
   - `H0A3G2BES01RCKVX`, `8Q6E0AC9KWY941A4`, `DRHGPPSWAXJ9Q2T6`
2. 🔑 **1 seule clé** Solana (format base58)
3. 📝 **Format symbole**: BTC, ETH, SOL (sans USDT)
4. 💰 **Commencez PETIT**: 5% du solde max
5. 👀 **Surveillez** activement au début
6. 🔐 **Sécurité** avant tout
7. ⚠️ **Risques** à comprendre et accepter

---

**Bonne chance avec votre market making!** 🚀

*Projet: Pacifica_Market_Making*
*Auteur: Onikai*
*Date: Octobre 2025*