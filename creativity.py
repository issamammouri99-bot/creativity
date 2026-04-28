import os, sys, urllib.request, zipfile, warnings
warnings.filterwarnings("ignore")

import pandas as pd

# Configuration Django 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__main__")
from django.conf import settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "OPTIONS": {"string_if_invalid": "", "context_processors": []},
        }],
    )
import django
django.setup()
from django.http import HttpResponse
from django.urls import path
from django.template import Template, Context
from django.core.management import execute_from_command_line


#  ÉTAPE 1 — TÉLÉCHARGER ET CHARGER LES DONNÉES


def telecharger_dataset():
    """Télécharge le dataset MovieLens si pas encore présent."""
    if not os.path.exists("ml-latest-small"):
        print("Téléchargement du dataset...")
        urllib.request.urlretrieve(
            "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
            "movielens.zip"
        )
        with zipfile.ZipFile("movielens.zip") as z:
            z.extractall(".")
        os.remove("movielens.zip")
        print("Dataset prêt ✓")

telecharger_dataset()

# On charge deux fichiers CSV :
# - movies  : movieId | title | genres
# - ratings : userId  | movieId | rating (0.5 à 5)
movies  = pd.read_csv("ml-latest-small/movies.csv")
ratings = pd.read_csv("ml-latest-small/ratings.csv")

print(f"Films chargés   : {len(movies)}")
print(f"Notes chargées  : {len(ratings)}")

def calculer_similarite_genres():
    """
    Pour chaque film, on crée une liste de ses genres.
    On compare ensuite les genres entre les films pour trouver les plus proches.

    La similarité = (genres en commun) / (total genres des deux films)
    C'est comme comparer deux listes et compter les éléments identiques.
    """

    genres_par_film = {}
    for _, row in movies.iterrows():
        if row["genres"] != "(no genres listed)":
            genres_par_film[row["movieId"]] = set(row["genres"].split("|"))

    print("Calcul des similarités entre films...")


    similarites = {}

    for movie_id, genres_film in genres_par_film.items():
        scores = []

        for autre_id, genres_autre in genres_par_film.items():
            if autre_id == movie_id:
                continue  # On ne compare pas un film avec lui-même

            genres_communs = genres_film & genres_autre  # intersection

            genres_total   = genres_film | genres_autre  # union

            if len(genres_total) > 0:
                score = len(genres_communs) / len(genres_total)
            else:
                score = 0

            scores.append((autre_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        similarites[movie_id] = scores[:10]

    print("Similarités calculées ✓")
    return similarites

similarites = calculer_similarite_genres()

#  ÉTAPE 3 — FONCTIONS UTILITAIRES

def chercher_films(query, limite=10):
    """Cherche des films dont le titre contient le mot 'query'."""
    mask = movies["title"].str.contains(query, case=False, na=False)
    resultats = movies[mask].head(limite)
    return resultats.to_dict("records")


def infos_film(movie_id):
    """Retourne les infos d'un film : titre, genres, note moyenne."""
    row = movies[movies["movieId"] == movie_id]
    if row.empty:
        return None

    notes_du_film = ratings[ratings["movieId"] == movie_id]["rating"]
    note_moy = round(notes_du_film.mean(), 1) if len(notes_du_film) > 0 else 0

    return {
        "movieId": int(movie_id),
        "title"  : row.iloc[0]["title"],
        "genres" : row.iloc[0]["genres"].replace("|", " · "),
        "nb_votes"  : len(notes_du_film),
        "note_moy"  : note_moy,
    }


def recommander(movie_id, n=8):
    """
    Retourne les n films les plus similaires au film donné.
    Utilise les similarités de genres calculées à l'étape 2.
    """
    if movie_id not in similarites:
        return []

    resultats = []
    for autre_id, score in similarites[movie_id][:n]:
        film = movies[movies["movieId"] == autre_id]
        if film.empty:
            continue
        resultats.append({
            "title"  : film.iloc[0]["title"],
            "genres" : film.iloc[0]["genres"].replace("|", " · "),
            "score"  : round(score, 2),
            "pct"    : int(score * 100), 
        })

    return resultats


def top_films(n=6):
    """Retourne les films les mieux notés (avec au moins 100 votes)."""
    merged = ratings.merge(movies, on="movieId")
    top = (
        merged.groupby("title")["rating"]
        .agg(["mean", "count"])
        .query("count >= 100")
        .sort_values("mean", ascending=False)
        .head(n)
        .reset_index()
    )
    top["mean"] = top["mean"].round(1)
    return top.to_dict("records")

#  ÉTAPE 4 — INTERFACE WEB (Django)

PAGE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CinéReco</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f5f5fa; color: #222; }

  header {
    background: linear-gradient(135deg, #1a1a2e, #533483);
    color: white; padding: 1.4rem 2rem;
    display: flex; align-items: center; gap: 14px;
  }
  header h1 { font-size: 1.5rem; font-weight: 700; }
  header p  { font-size: 0.8rem; opacity: 0.6; margin-top: 3px; }

  .page { max-width: 860px; margin: 2rem auto; padding: 0 1rem; }

  /* Stats */
  .stats { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .stat {
    flex: 1; min-width: 140px; background: white;
    border-radius: 12px; padding: 1rem; text-align: center;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
  }
  .stat .n { font-size: 1.5rem; font-weight: 700; color: #533483; }
  .stat .l { font-size: 0.75rem; color: #999; margin-top: 3px; }

  /* Carte blanche générique */
  .card {
    background: white; border-radius: 14px; padding: 1.4rem;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07); margin-bottom: 1.5rem;
  }
  .card h2 { font-size: 1rem; color: #444; margin-bottom: 1rem; }

  /* Formulaire */
  .form-row { display: flex; gap: 10px; }
  .form-row input {
    flex: 1; padding: 0.65rem 1rem;
    border: 1.5px solid #ddd; border-radius: 8px; font-size: 0.95rem; outline: none;
  }
  .form-row input:focus { border-color: #533483; }
  .form-row button {
    padding: 0.65rem 1.4rem; background: #533483; color: white;
    border: none; border-radius: 8px; font-size: 0.95rem; cursor: pointer;
  }
  .form-row button:hover { background: #3d2568; }

  /* Liste de films */
  .film-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.65rem 0; border-bottom: 1px solid #f0f0f5;
  }
  .film-row:last-child { border: none; }
  .film-name  { font-size: 0.88rem; font-weight: 500; }
  .film-genre { font-size: 0.75rem; color: #aaa; margin-top: 2px; }

  .badge {
    font-size: 0.75rem; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; white-space: nowrap; margin-left: 10px;
  }
  .badge-purple { background: #ede8fd; color: #533483; }
  .badge-green  { background: #e6f4ea; color: #2e7d32; }
  .badge-star   { background: #fff8e1; color: #f57f17; }

  a.choisir {
    text-decoration: none; font-size: 0.8rem; color: #533483;
    border: 1px solid #c5b8f5; border-radius: 6px; padding: 3px 10px;
  }
  a.choisir:hover { background: #ede8fd; }

  /* Film sélectionné */
  .ref-film {
    background: #f0ebff; border-radius: 10px; padding: 1rem 1.2rem;
    margin-bottom: 1.2rem; display: flex; gap: 12px; align-items: center;
  }
  .ref-film .icon { font-size: 2rem; }
  .ref-film .name { font-weight: 600; font-size: 1rem; }
  .ref-film .meta { font-size: 0.8rem; color: #777; margin-top: 3px; }

  .empty { text-align: center; color: #ccc; padding: 2rem 0; }

  /* Explication algo */
  .algo-box {
    background: #f0f7ff; border-left: 3px solid #2196F3;
    border-radius: 0 10px 10px 0; padding: 0.8rem 1rem;
    font-size: 0.82rem; color: #555; margin-bottom: 1.2rem; line-height: 1.6;
  }
</style>
</head>
<body>

<header>
  <div style="font-size:2rem">🎬</div>
  <div>
    <h1>CinéReco</h1>
    <p>PFA — Deuxième Licence Data Science</p>
  </div>
</header>

<div class="page">

  <!-- Statistiques -->
  <div class="stats">
    <div class="stat"><div class="n">{{ nb_films }}</div><div class="l">Films</div></div>
    <div class="stat"><div class="n">{{ nb_users }}</div><div class="l">Utilisateurs</div></div>
    <div class="stat"><div class="n">{{ nb_ratings }}</div><div class="l">Notes totales</div></div>
    <div class="stat"><div class="n">★ {{ avg }}</div><div class="l">Note moyenne</div></div>
  </div>

  <!-- Recherche -->
  <div class="card">
    <h2>🔍 Rechercher un film</h2>
    <form method="GET" action="/">
      <div class="form-row">
        <input type="text" name="q" placeholder="Ex: Toy Story, Matrix, Titanic..." value="{{ query }}">
        <button type="submit">Rechercher</button>
      </div>
    </form>
  </div>

  <!-- Résultats de recherche -->
  {% if search_results %}
  <div class="card">
    <h2>Résultats pour "{{ query }}"</h2>
    {% for f in search_results %}
    <div class="film-row">
      <div>
        <div class="film-name">{{ f.title }}</div>
        <div class="film-genre">{{ f.genres }}</div>
      </div>
      <a class="choisir" href="/?movie_id={{ f.movieId }}">Choisir →</a>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Recommandations -->
  {% if selected %}
  <div class="ref-film">
    <div class="icon">🎥</div>
    <div>
      <div class="name">{{ selected.title }}</div>
      <div class="meta">{{ selected.genres }} &nbsp;|&nbsp; {{ selected.nb_votes }} votes &nbsp;|&nbsp; ★ {{ selected.note_moy }}</div>
    </div>
  </div>

  <div class="card">
    <h2>🎯 Films similaires recommandés</h2>

    <!-- Explication simple de l'algorithme -->
    <div class="algo-box">
      💡 <b>Comment ça marche ?</b> On compare les genres de chaque film.
      Plus deux films partagent les mêmes genres, plus leur score de similarité est élevé (proche de 100%).
      Exemple : si Toy Story est "Animation · Comédie" et qu'un autre film l'est aussi → score élevé !
    </div>

    {% for f in recos %}
    <div class="film-row">
      <div>
        <div class="film-name">{{ f.title }}</div>
        <div class="film-genre">{{ f.genres }}</div>
      </div>
      <span class="badge badge-purple">{{ f.pct }}% similaire</span>
    </div>
    {% empty %}
    <div class="empty">Aucune recommandation trouvée.</div>
    {% endfor %}
  </div>

  {% elif not search_results %}

  <!-- Top films si rien sélectionné -->
  <div class="card">
    <h2>⭐ Top films les mieux notés</h2>
    {% for f in top %}
    <div class="film-row">
      <div>
        <div class="film-name">{{ f.title }}</div>
        <div class="film-genre">{{ f.count }} votes</div>
      </div>
      <span class="badge badge-star">★ {{ f.mean }}</span>
    </div>
    {% endfor %}
  </div>

  {% endif %}

</div>
</body>
</html>
"""

# ── Vue Django ─────────────────────────────────────────────────────────────

def index(request):
    query    = request.GET.get("q", "").strip()
    movie_id = request.GET.get("movie_id", "")

    ctx = {
        "nb_films"  : f"{len(movies):,}",
        "nb_users"  : f"{ratings['userId'].nunique():,}",
        "nb_ratings": f"{len(ratings):,}",
        "avg"       : round(float(ratings["rating"].mean()), 1),
        "query"     : query,
        "search_results": [],
        "selected"  : None,
        "recos"     : [],
        "top"       : top_films(),
    }

    if query:
        ctx["search_results"] = chercher_films(query)

    if movie_id:
        try:
            mid = int(movie_id)
            ctx["selected"] = infos_film(mid)
            ctx["recos"]    = recommander(mid)
        except ValueError:
            pass

    html = Template(PAGE_HTML).render(Context(ctx))
    return HttpResponse(html)


urlpatterns = [path("", index)]

if __name__ == "__main__":
    execute_from_command_line(["manage.py", "runserver", "8000"])