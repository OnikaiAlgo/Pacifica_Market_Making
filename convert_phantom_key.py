#!/usr/bin/env python3
"""
Script pour convertir une clé privée Phantom en format base58 pour Solana.

Phantom peut exporter la clé dans deux formats :
1. Array de bytes (ex: [234,12,56,...]) - à copier depuis Phantom
2. String hex - moins courant

Ce script convertit vers le format base58 requis par solana-py.
"""

import base58
import sys

def convert_array_to_base58(array_str):
    """Convertit un array de bytes en base58."""
    # Nettoyer la string et extraire les nombres
    array_str = array_str.strip().replace('[', '').replace(']', '')
    bytes_array = [int(x.strip()) for x in array_str.split(',')]

    # Vérifier la longueur
    if len(bytes_array) != 64:
        print(f"⚠️  ERREUR: La clé doit contenir 64 bytes, trouvé {len(bytes_array)}")
        return None

    # Convertir en base58
    private_key_bytes = bytes(bytes_array)
    base58_key = base58.b58encode(private_key_bytes).decode('ascii')

    return base58_key

def main():
    print("=" * 80)
    print("CONVERSION CLÉ PRIVÉE PHANTOM → BASE58")
    print("=" * 80)
    print()
    print("📋 COMMENT OBTENIR VOTRE CLÉ DEPUIS PHANTOM:")
    print()
    print("1. Ouvrir l'extension Phantom dans votre navigateur")
    print("2. Cliquer sur les 3 lignes (menu hamburger) en haut à gauche")
    print("3. Aller dans 'Settings' (Paramètres)")
    print("4. Cliquer sur 'Security & Privacy' (Sécurité et Confidentialité)")
    print("5. Cliquer sur 'Export Private Key' (Exporter la Clé Privée)")
    print("6. Entrer votre mot de passe")
    print("7. Copier le ARRAY DE NOMBRES qui apparaît")
    print("   Format: [234, 12, 56, 89, ...]")
    print()
    print("-" * 80)
    print()

    # Demander l'input
    print("Collez votre clé privée (array de nombres) ci-dessous:")
    print("Exemple: [234,12,56,89,...]")
    print()

    try:
        if len(sys.argv) > 1:
            # Clé passée en argument
            array_input = ' '.join(sys.argv[1:])
        else:
            # Demander interactivement
            array_input = input("Clé privée: ").strip()

        if not array_input:
            print("❌ Aucune clé fournie.")
            return

        # Convertir
        print()
        print("🔄 Conversion en cours...")
        base58_key = convert_array_to_base58(array_input)

        if base58_key:
            print()
            print("=" * 80)
            print("✅ CONVERSION RÉUSSIE!")
            print("=" * 80)
            print()
            print("Votre clé au format base58:")
            print("-" * 80)
            print(base58_key)
            print("-" * 80)
            print()
            print(f"Longueur: {len(base58_key)} caractères")
            print()
            print("📝 PROCHAINES ÉTAPES:")
            print()
            print("1. Copiez la clé ci-dessus")
            print("2. Ouvrez le fichier .env")
            print("3. Remplacez la ligne PRIVATE_KEY=... par:")
            print(f"   PRIVATE_KEY={base58_key}")
            print()
            print("⚠️  SÉCURITÉ: Gardez cette clé SECRÈTE et ne la partagez JAMAIS!")
            print()

    except Exception as e:
        print(f"❌ ERREUR lors de la conversion: {e}")
        print()
        print("Assurez-vous que:")
        print("- Vous avez copié le format correct (array de nombres)")
        print("- Le array contient exactement 64 nombres")
        print("- Les nombres sont séparés par des virgules")

if __name__ == "__main__":
    main()
