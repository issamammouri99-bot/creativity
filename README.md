## Fonctionnalités

- Recherche de films par titre
- Recommandation de films similaires avec un score de similarité en %
- Affichage du top des films les mieux notés
- Statistiques globales (nombre de films, utilisateurs, notes)
- Téléchargement automatique du dataset au premier lancement

---

## Technologies utilisées

| Outil | Rôle |
|---|---|
| Python 3.x | Langage principal |
| Django | Framework web |
| Pandas | Lecture et manipulation des données CSV |
| MovieLens Small | Dataset de films et de notes |

---

> Le dataset MovieLens se télécharge automatiquement au premier lancement. Aucune manipulation manuelle nécessaire.

---

## Comment fonctionne l'algorithme

L'algorithme compare les **genres** de chaque film pour mesurer leur similarité.

**Formule utilisée :**

```
score = genres en commun / total des genres
```

**Exemple concret :**

```
Toy Story  →  Animation · Children · Comedy
Shrek      →  Animation · Children · Comedy · Fantasy

Genres en commun = 3  (Animation, Children, Comedy)
Total des genres = 4  (Animation, Children, Comedy, Fantasy)

Score = 3 / 4 = 0.75 → 75% similaire ✅
```

Un score de **100%** signifie que les deux films ont exactement les mêmes genres.
Un score de **0%** signifie qu'ils n'ont aucun genre en commun.

---

## Dataset

**MovieLens Small** — fourni par GroupLens Research (Université du Minnesota)

| Élément | Valeur |
|---|---|
| Nombre de films | 9 742 |
| Nombre d'utilisateurs | 610 |
| Nombre de notes | 100 836 |
| Échelle des notes | 0.5 à 5 étoiles |

Lien officiel : https://grouplens.org/datasets/movielens/

---

## Utilisation

1. Tapez le nom d'un film dans la barre de recherche (ex: `Toy Story`)
2. Cliquez sur **Rechercher**
3. Dans les résultats, cliquez sur **Choisir →** à côté du film voulu
4. L'application affiche les films les plus similaires avec leur score

---

## Auteur

Réalisé dans le cadre du Projet de Fin d'Année (PFA)
Deuxième Licence — Spécialité Data Science
