# ============================================================================
# MAKEFILE — Carrier API Health Checker
# Anchanto — Technical Partnerships
#
# Usage : make <commande>
# Aide  : make help
# ============================================================================

.PHONY: help install run run-verbose run-html run-watch test test-cov lint format check clean version

# ---- AIDE ----
help: ## Afficher cette aide
    @echo.
    @echo   Carrier API Health Checker — Commandes disponibles
    @echo   ==================================================
    @echo.
    @echo   make install       Installer les dependances
    @echo   make run           Lancer le health check (defaut)
    @echo   make run-verbose   Lancer en mode verbose
    @echo   make run-html      Lancer et exporter en HTML
    @echo   make run-watch     Lancer en mode watch (5 min)
    @echo   make test          Lancer tous les tests
    @echo   make test-cov      Lancer les tests avec couverture
    @echo   make lint          Lancer ruff (linter)
    @echo   make format        Formater le code avec ruff
    @echo   make check         Lancer tous les hooks pre-commit
    @echo   make clean         Supprimer les fichiers temporaires
    @echo   make version       Afficher la version
    @echo.

# ---- INSTALLATION ----
install: ## Installer les dépendances et les hooks
    pip install -r requirements.txt
    pre-commit install

# ---- EXÉCUTION ----
run: ## Lancer le health check (export JSON par défaut)
    python main.py

run-verbose: ## Lancer en mode verbose
    python main.py --verbose

run-html: ## Lancer et exporter en HTML
    python main.py --verbose --format html

run-watch: ## Lancer en mode watch (toutes les 5 minutes)
    python main.py --watch 5 --verbose

# ---- TESTS ----
test: ## Lancer tous les tests
    pytest tests/ -v

test-cov: ## Lancer les tests avec couverture de code
    pytest tests/ -v --cov=src --cov-report=term-missing

# ---- QUALITÉ DE CODE ----
lint: ## Vérifier le code avec ruff (linter)
    ruff check src/ tests/ main.py

format: ## Formater le code avec ruff
    ruff format src/ tests/ main.py

check: ## Lancer tous les hooks pre-commit
    pre-commit run --all-files

# ---- UTILITAIRES ----
clean: ## Supprimer les fichiers temporaires
    @echo Nettoyage en cours...
    @if exist __pycache__ rmdir /s /q __pycache__
    @if exist src\__pycache__ rmdir /s /q src\__pycache__
    @if exist tests\__pycache__ rmdir /s /q tests\__pycache__
    @if exist .pytest_cache rmdir /s /q .pytest_cache
    @if exist .ruff_cache rmdir /s /q .ruff_cache
    @echo Nettoyage termine.

version: ## Afficher la version
    python main.py --version
