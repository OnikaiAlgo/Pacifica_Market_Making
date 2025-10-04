# Installation sur Serveur - Pacifica Market Making Bot

## 📦 Fichier Fourni

**Archive**: `Pacifica_Market_Making.tar.gz` (75 KB)

## 🚀 Installation Rapide

### 1. Transférer l'Archive sur le Serveur

```bash
# Depuis votre machine locale
scp Pacifica_Market_Making.tar.gz user@votre-serveur:~/

# OU via FTP/SFTP avec FileZilla, WinSCP, etc.
```

### 2. Se Connecter au Serveur

```bash
ssh user@votre-serveur
```

### 3. Extraire l'Archive

```bash
cd ~
tar -xzf Pacifica_Market_Making.tar.gz
cd Pacifica_Market_Making
```

### 4. Installer les Dépendances

```bash
# Vérifier Python 3.8+
python3 --version

# Installer pip si nécessaire
sudo apt update
sudo apt install python3-pip -y

# Installer les dépendances du projet
pip3 install -r requirements.txt
```

### 5. Configurer le Bot

```bash
# Créer le fichier de configuration
cp .env.example .env
nano .env
```

**Remplir obligatoirement:**
```bash
PRIVATE_KEY=votre_clé_privée_solana_base58
SYMBOL=BTC
```

### 6. Tester la Connexion

```bash
python3 -c "from api_client import ApiClient; import asyncio; import os; from dotenv import load_dotenv; load_dotenv(); print('Test connexion...'); asyncio.run(ApiClient(os.getenv('PRIVATE_KEY')).__aenter__())"
```

Si ça fonctionne: ✅ "Test connexion..." apparaît sans erreur

## 🐳 Option A: Avec Docker (Recommandé)

### Installation Docker

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo apt install docker-compose -y

# Vérifier
docker --version
docker-compose --version
```

### Lancer le Bot avec Docker

```bash
# Construire les images
docker-compose build

# Lancer tous les services (data-collector, avellaneda-params, trend-finder, market-maker)
docker-compose up -d

# Voir les logs
docker-compose logs -f market-maker

# Arrêter
docker-compose down
```

## 💻 Option B: Sans Docker (Manuel)

### Avec Screen (Recommandé)

```bash
# Installer screen
sudo apt install screen -y

# Créer une session pour chaque service
screen -S data-collector
python3 data_collector.py
# Ctrl+A puis D pour détacher

screen -S avellaneda
while true; do python3 calculate_avellaneda_parameters.py --symbol BTC --minutes 5; sleep 10m; done
# Ctrl+A puis D

screen -S trend
while true; do python3 find_trend.py --symbol BTC --interval 5m; sleep 5m; done
# Ctrl+A puis D

screen -S market-maker
python3 market_maker.py --symbol BTC
# Ctrl+A puis D

# Réattacher une session
screen -r market-maker

# Lister les sessions
screen -ls
```

### Avec Systemd (Service)

Créer `/etc/systemd/system/pacifica-bot.service`:

```ini
[Unit]
Description=Pacifica Market Making Bot
After=network.target

[Service]
Type=simple
User=votre_user
WorkingDirectory=/home/votre_user/Pacifica_Market_Making
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 market_maker.py --symbol BTC
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pacifica-bot
sudo systemctl start pacifica-bot
sudo systemctl status pacifica-bot
sudo journalctl -u pacifica-bot -f
```

## 📊 Surveillance

### Dashboard Terminal

```bash
python3 dashboard.py
```

### Logs

```bash
# Docker
docker-compose logs -f

# Manuel
tail -f market_maker.log
```

### Volume de Trading

```bash
python3 get_my_trading_volume.py --symbol BTC --days 7
```

## ⚠️ Configuration Importante AVANT de Lancer

### 1. Paramètres de Sécurité

Éditer `market_maker.py`:

```python
# LIGNE 21 - IMPORTANT!
DEFAULT_BALANCE_FRACTION = 0.05  # 5% du solde (PAS 20%!)

# LIGNE 22
POSITION_THRESHOLD_USD = 15.0    # Limite position

# LIGNE 44
RELEASE_MODE = True              # Logs minimaux
```

### 2. Symbole dans .env

```bash
SYMBOL=BTC  # ou ETH, SOL, etc.
```

## 🔧 Commandes Utiles

### Docker

```bash
# Statut
docker-compose ps

# Logs d'un service
docker-compose logs -f data-collector
docker-compose logs -f avellaneda-params
docker-compose logs -f trend-finder
docker-compose logs -f market-maker

# Redémarrer un service
docker-compose restart market-maker

# Arrêter tout
docker-compose down

# Voir l'utilisation ressources
docker stats
```

### Manuel

```bash
# Tuer un processus
pkill -f market_maker.py

# Sessions screen
screen -ls
screen -r market-maker
# Ctrl+A puis D pour détacher
# Ctrl+A puis K pour tuer

# Surveiller CPU/RAM
htop
```

## 🐛 Dépannage

### "Invalid Solana private key"
→ Vérifier format dans .env (base58, pas JSON)

### "No module named 'solders'"
→ `pip3 install -r requirements.txt`

### "Permission denied" Docker
→ `sudo usermod -aG docker $USER` puis relogger

### Bot s'arrête
→ Voir logs: `tail -f market_maker.log`

### Pas de données collectées
→ Vérifier data-collector: `docker-compose logs data-collector`

## 📈 Recommandations Serveur

### Minimum
- CPU: 1 vCore
- RAM: 1 GB
- Stockage: 5 GB
- OS: Ubuntu 20.04+ / Debian 11+

### Recommandé
- CPU: 2 vCores
- RAM: 2 GB
- Stockage: 10 GB
- Région: Proche de l'infrastructure Pacifica

### Providers
- AWS (Tokyo, Singapore)
- Google Cloud (asia-northeast1)
- DigitalOcean (Singapore)
- Hetzner (Finlande)

## 🔐 Sécurité Serveur

```bash
# Firewall
sudo ufw allow 22/tcp
sudo ufw enable

# Mises à jour
sudo apt update && sudo apt upgrade -y

# Backup .env
cp .env .env.backup
chmod 600 .env .env.backup

# Surveiller accès
sudo tail -f /var/log/auth.log
```

## ✅ Checklist Avant Production

- [ ] Archive extraite
- [ ] Dépendances installées
- [ ] .env configuré avec clé Solana
- [ ] DEFAULT_BALANCE_FRACTION = 0.05 (5%)
- [ ] Test connexion réussi
- [ ] Docker installé (si option Docker)
- [ ] Logs accessibles
- [ ] Dashboard testé
- [ ] Petit montant sur le compte bot

## 🚀 Démarrage Production

1. **Tester 24h** avec balance fraction = 0.05 (5%)
2. **Surveiller** logs et dashboard activement
3. **Analyser** performances
4. **Ajuster** paramètres si besoin
5. **Augmenter** progressivement après succès

---

**Support**: Voir README.md et GUIDE_FRANCAIS.md pour plus de détails.
