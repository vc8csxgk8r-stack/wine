# 🍷 Cave à Vin

Application de gestion de cave à vin avec base de données viticole mondiale intégrée.

## Déploiement Portainer (Git repository)

### 1. Pusher ce repo sur GitHub ou Gitea

```bash
git init
git add .
git commit -m "init cave à vin"
git remote add origin https://github.com/VOUS/cave-a-vin.git
git push -u origin main
```

### 2. Dans Portainer

- **Stacks** → **Add Stack**
- Nommer : `cave-a-vin`
- Sélectionner **Repository**
- Renseigner l'URL de votre repo Git
- Repository reference : `refs/heads/main`
- Compose path : `docker-compose.yml`
- Activer **GitOps updates** si vous souhaitez le déploiement automatique
- Cliquer **Deploy the stack**

### Variable d'environnement optionnelle

| Variable | Défaut | Description         |
|----------|--------|---------------------|
| `PORT`   | `8080` | Port d'écoute HTTP  |

---

## Structure

```
cave-a-vin/
├── docker-compose.yml     ← Stack Portainer
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py             ← API Flask + logique viticole
└── frontend/
    ├── Dockerfile
    ├── nginx.conf          ← Reverse proxy vers le backend
    └── index.html          ← Interface utilisateur
```

## Accès

```
http://votre-serveur:8080
```

## Fonctionnalités

- Gestion complète de la collection (ajout, modification, suppression)
- Calcul automatique de la **maturité** selon région, type et millésime
- **Notes des millésimes** 1982–2022 (Bordeaux, Bourgogne, Rhône…)
- **Estimation de prix** selon la cote du millésime et l'âge
- Filtres par type, état de maturité, recherche libre
- Interface thème cave — design sombre bordeaux & or
