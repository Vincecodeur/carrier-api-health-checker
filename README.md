# 🚚 Carrier API Health Checker

**Anchanto — Technical Partnerships**

Outil CLI de monitoring des endpoints API des transporteurs (Colissimo, Chronopost, DHL, GLS, DPD, FedEx, UPS). Vérifie la disponibilité, mesure la latence, détecte les dégradations et exporte les résultats en CSV, JSON ou HTML.

Projet de formation Python appliqué au monitoring des intégrations transporteurs EMEA.

---

## ⚡ Quick Start

```bash
# Cloner le repo
git clone https://github.com/Vincecodeur/carrier-api-health-checker.git
cd carrier-api-health-checker

# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows PowerShell
source venv/bin/activate     # Linux / Mac

# Installer les dépendances
pip install -r requirements.txt

# Lancer le health check
python main.py
```

---

## 📋 Fonctionnalités

### Phase 1 — Robustesse

- **Health check parallèle** — Vérifie tous les carriers simultanément via `ThreadPoolExecutor` (speedup 3-4x)
- **Retry automatique** — Relance les checks échoués avec backoff exponentiel (1s → 2s → 3s...)
- **Seuils de latence** — Détecte les carriers lents avec seuil configurable par carrier (`max_latency_ms`)
- **Export CSV** — Export horodaté des résultats au format tableur
- **Logging dual** — Console + fichier (`logs/`) avec niveaux configurables (DEBUG → CRITICAL)
- **CLI complète** — 9 flags avec valeurs par défaut, raccourcis, validation et aide intégrée
- **Architecture modulaire** — 9 modules Python, Single Responsibility Principle, séparation config/code
- **9 carriers de production** — Colissimo, La Poste, Chronopost, DHL Express, GLS, DPD, FedEx, UPS

### Phase 2 — Qualité et tests

- **65 tests unitaires (pytest)** — Couvrent config, checker, CLI, export et comparaison
- **Mocking HTTP** — Tests sans réseau grâce à `unittest.mock` (requêtes simulées)
- **Couverture de code** — checker 98%, config 100%, cli 100% via `pytest-cov`
- **Type hints** — Annotations de type sur toutes les fonctions, validées par `mypy` (0 erreur) et Pylance
- **Export JSON** — Format par défaut, types natifs préservés (int, bool, null) avec métadonnées

### Phase 3 — Automatisation et Reporting

- **Exit code conditionnel** — Retourne 1 si un carrier est down — intégration CI/CD et scripts batch
- **Dashboard HTML** — Rapport visuel autonome avec tableau coloré, CSS inline, ouvrable dans tout navigateur
- **Comparaison historique** — Détecte automatiquement les changements entre deux runs (down, recovered, dégradé, amélioré)

---

## 🚀 Utilisation

### Commandes courantes

```bash
# Mode par défaut (export JSON + comparaison historique)
python main.py

# Mode verbose (détails par carrier)
python main.py --verbose

# Dashboard HTML
python main.py --format html

# Export CSV
python main.py --format csv

# Pas d'export (affichage terminal uniquement)
python main.py --no-export --verbose
```

### Flags CLI

```
options:
  -h, --help           Afficher l'aide
  -c, --config FILE    Fichier de config JSON (default: config/carriers.json)
  -v, --verbose        Affichage détaillé par carrier
  --no-export          Désactiver l'export (affichage terminal uniquement)
  -o, --output DIR     Dossier d'export (default: output)
  --log-level LEVEL    Niveau de log : DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
  -w, --workers N      Nombre de threads parallèles (default: 5)
  -r, --retries N      Nombre de retries pour les checks échoués (default: 2)
  --max-latency MS     Seuil de latence global en ms (default: 0 = désactivé)
  -f, --format FORMAT  Format d'export : csv, json ou html (default: json)
```

### Exemples avancés

```bash
# Dashboard HTML avec mode verbose
python main.py --verbose --format html

# 10 threads et 3 retries
python main.py --workers 10 --retries 3

# Alerter si un carrier dépasse 500ms
python main.py --max-latency 500

# Mode debug (logs détaillés)
python main.py --log-level DEBUG

# Mode séquentiel (1 thread, utile pour le debug)
python main.py --workers 1 --verbose

# Intégration script batch (exit code 0=OK, 1=échec)
python main.py && echo "OK" || echo "ALERTE"
```

---

## 📊 Comparaison historique

Le script compare automatiquement les résultats actuels avec le dernier fichier JSON exporté dans `output/`. La comparaison fonctionne quel que soit le format d'export actuel — il suffit qu'un fichier JSON d'un run précédent existe.

### Types de changements détectés

| Icône | Type | Description |
|---|---|---|
| 🔻 | NEW_DOWN | Carrier healthy → unhealthy ou error |
| 🔺 | RECOVERED | Carrier down → healthy |
| 📈 | DEGRADED | Latence augmentée de > 50% |
| 📉 | IMPROVED | Latence diminuée de > 50% |
| 🆕 | NEW | Carrier ajouté à la config |
| ❌ | REMOVED | Carrier supprimé de la config |

### Exemple de sortie

```
================================================================================
  📊 CHANGES SINCE LAST RUN
================================================================================

  🔻 NEW_DOWN — DHL Express (MyDHL API - Production)
     HEALTHY → ERROR (TIMEOUT)

  📉 IMPROVED — DPD Group (Shipping API)
     123 ms → 55 ms (-56%)

  🔻 NEW_DOWN: 1  |  📉 IMPROVED: 1
================================================================================
```

---

## 🔧 Configuration des carriers

Les transporteurs sont définis dans `config/carriers.json` :

```json
{
  "carriers": [
    {
      "name": "Colissimo SLS (La Poste - Étiquetage)",
      "url": "https://ws.colissimo.fr/sls-ws/SlsServiceWSRest/2.0/checkGenerateLabel",
      "method": "GET",
      "expected_status": [200, 401, 403, 405],
      "timeout": 10,
      "retries": 2,
      "max_latency_ms": 400
    }
  ]
}
```

### Champs

| Champ | Requis | Description |
|---|---|---|
| `name` | ✅ | Nom affiché dans le dashboard |
| `url` | ✅ | Endpoint API à vérifier |
| `method` | ✅ | Méthode HTTP (GET) |
| `expected_status` | ✅ | Codes HTTP considérés comme "healthy" |
| `timeout` | ✅ | Timeout de la requête en secondes |
| `retries` | ❌ | Surcharge le défaut CLI `--retries` |
| `max_latency_ms` | ❌ | Surcharge le défaut CLI `--max-latency` |

### 9 carriers configurés

| Carrier | URL | Status attendu | Seuil latence |
|---|---|---|---|
| **Colissimo SLS** | ws.colissimo.fr | 405 (attend POST) | 400 ms |
| **La Poste Suivi** | api.laposte.fr | 401 (pas de clé API) | 300 ms |
| **La Poste Status** | developer.laposte.fr | 200 (page publique) | 400 ms |
| **Chronopost** | ws.chronopost.fr | 200 (WSDL public) | 500 ms |
| **DHL Express** | express.api.dhl.com | 405 (attend POST) | 600 ms |
| **GLS ShipIT** | shipit-wbm-test01.gls-group.eu | 401 (pas de credentials) | 400 ms |
| **DPD Group** | shipping.dpdgroup.com | 401 (pas de credentials) | 500 ms |
| **FedEx** | apis.fedex.com | 405 (attend POST) | 700 ms |
| **UPS** | onlinetools.ups.com | 405 (attend POST) | 500 ms |

> **Sécurité** : le script n'envoie aucun credential. Il fait un GET sans authentification pour vérifier que le serveur **répond**. Un code 401/403/405 signifie que le serveur est UP mais refuse l'accès — c'est le comportement attendu.

---

## 🗂️ Structure du projet

```
carrier-api-health-checker/
├── main.py                  # Point d'entrée — orchestre le pipeline
├── config/
│   └── carriers.json        # Configuration des 9 transporteurs
├── src/
│   ├── __init__.py          # Transforme src/ en package Python
│   ├── checker.py           # Health check HTTP + retry + latence
│   ├── cli.py               # Parsing des arguments CLI (argparse)
│   ├── compare.py           # Comparaison historique entre runs
│   ├── config.py            # Chargement et validation du JSON
│   ├── display.py           # Affichage terminal (dashboard + changements)
│   ├── export.py            # Export CSV, JSON et HTML
│   └── logger.py            # Configuration logging (console + fichier)
├── tests/
│   ├── __init__.py          # Transforme tests/ en package Python
│   ├── conftest.py          # Fixtures partagées (carriers et résultats fictifs)
│   ├── test_checker.py      # 21 tests — health check, retry, latence (mocking)
│   ├── test_cli.py          # 11 tests — flags, défauts, choices, validation
│   ├── test_compare.py      # 16 tests — changements, find_previous_run
│   ├── test_config.py       # 5 tests — chargement JSON, gestion erreurs
│   └── test_export.py       # 12 tests — CSV, JSON, HTML
├── output/                  # Fichiers exportés (gitignored)
├── logs/                    # Fichiers de log (gitignored)
├── requirements.txt         # Dépendances Python
├── .gitignore               # Exclusions Git (venv, output, logs, __pycache__)
└── README.md
```

---

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests (65)
pytest tests/ -v

# Avec couverture de code
pytest tests/ -v --cov=src --cov-report=term-missing

# Un seul fichier de test
pytest tests/test_checker.py -v

# Un seul test spécifique
pytest tests/test_checker.py::TestCheckCarrier::test_healthy_response -v
```

### Couverture de code

| Module | Couverture | Détail |
|---|---|---|
| config.py | **100%** | Tous les cas d'erreur testés |
| cli.py | **100%** | Tous les flags, défauts et choices |
| checker.py | **98%** | Mock HTTP, retry, latence, filet de sécurité |
| compare.py | **~90%** | Tous les types de changements |
| export.py | **75%** | CSV, JSON, HTML + gestion erreurs |
| display.py | 0% | Affichage pur (print) — non testé volontairement |
| logger.py | 0% | Configuration logging — testé indirectement |

### Techniques de test

- **Fixtures** (`conftest.py`) — Données de test partagées (carriers fictifs, résultats simulés)
- **Mocking** (`@patch`, `MagicMock`) — Simulation des appels HTTP sans réseau
- **`side_effect`** — Simulation de retry (1er appel → Timeout, 2ème → succès)
- **`capsys`** — Capture de la sortie `print()` pour tester le feedback terminal
- **`tmp_path`** — Dossiers temporaires pour tester les exports fichier
- **`pytest.raises()`** — Vérification que les exceptions sont bien levées

---

## 📦 Dépendances

| Package | Usage |
|---|---|
| `requests` | Appels HTTP vers les API transporteurs |
| `pytest` | Framework de tests unitaires |
| `pytest-cov` | Mesure de la couverture de code |
| `mypy` | Vérification statique des types (optionnel) |

---

## 📈 Concepts Python couverts

Le projet couvre **162 concepts Python** documentés dans le glossaire (fichier Word séparé) :

| Catégorie | Exemples |
|---|---|
| Fondamentaux | Variables, dicts, listes, f-strings, list comprehension, lambda |
| Modules standard | json, csv, os, time, datetime, argparse, logging |
| Librairie tierce | requests (GET, timeout, exceptions) |
| Gestion d'erreurs | try/except, types d'exceptions, SystemExit |
| Architecture | Modules, packages, `__init__.py`, PEP 8, Single Responsibility |
| CLI | argparse, flags, choices, metavar, Namespace |
| Logging | Handlers, Formatters, niveaux, séparation print/logging |
| Concurrence | ThreadPoolExecutor, Future, as_completed, GIL |
| Tests | pytest, fixtures, mocking, parametrize, couverture |
| Type hints | Annotations, Optional, Union, TypedDict, mypy |
| Git | init, add, commit, push, .gitignore, Conventional Commits |

---

## 👤 Auteur

**Vincent Gueret** — Technical Partnerships Manager 

Projet développé dans le cadre d'une formation Python appliquée, orientée monitoring des intégrations transporteurs pour la région EMEA.
