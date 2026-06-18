"""
AI Book Recommendation Engine
Uses two strategies:
  1. Content-Based Filtering  → TF-IDF on title+genre+description (Scikit-learn)
  2. Collaborative Filtering  → SVD matrix factorization on user ratings (Scikit-learn)
  3. Hybrid                   → weighted combination of both scores
  4. Bayesian scoring         → smoothed rating + popularity (ml/scorer.py)
"""

import time
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import MinMaxScaler
import pickle
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'saved_models')
os.makedirs(MODEL_PATH, exist_ok=True)

# ── Recommendation cache ──────────────────────────────────────────────────────
_rec_cache: dict = {}
CACHE_TTL = 300  # 5 minutes


def _cache_get(user_id):
    entry = _rec_cache.get(user_id)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(user_id, results):
    _rec_cache[user_id] = (time.time(), results)


def _cache_invalidate(user_id=None):
    if user_id is None:
        _rec_cache.clear()
    else:
        _rec_cache.pop(user_id, None)


# ─────────────────────────────────────────────────────────────────────────────

class ContentBasedRecommender:
    """Recommends books similar to ones a user likes using TF-IDF."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=5000
        )
        self.tfidf_matrix = None
        self.book_ids = []
        self._id_to_idx = {}

    def fit(self, books_df):
        books_df = books_df.fillna('')
        books_df['content'] = (
            books_df['title'] + ' ' +
            books_df['author'] + ' ' +
            books_df['genre'] + ' ' +
            books_df['genre'] + ' ' +
            books_df['description']
        )
        self.book_ids = books_df['id'].tolist()
        self._id_to_idx = {bid: i for i, bid in enumerate(self.book_ids)}
        self.tfidf_matrix = self.vectorizer.fit_transform(books_df['content'])
        return self

    def recommend(self, book_id, n=10, exclude_ids=None):
        if book_id not in self._id_to_idx:
            return []
        exclude_ids = set(exclude_ids or [])
        idx = self._id_to_idx[book_id]
        scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        scores[idx] = 0
        ranked = np.argsort(scores)[::-1]
        results = []
        for i in ranked:
            bid = self.book_ids[i]
            if bid not in exclude_ids and len(results) < n:
                results.append((bid, float(scores[i])))
        return results

    def score_candidates(self, source_book_ids: list, candidate_ids: list) -> dict:
        """
        Return {candidate_book_id: avg_content_score} for a set of candidates,
        based on similarity to a list of source books (e.g. user's liked books).
        Used for building explanation-aware hybrid scoring.
        """
        scores = {cid: 0.0 for cid in candidate_ids}
        candidate_set = set(candidate_ids)
        for src_id in source_book_ids:
            if src_id not in self._id_to_idx:
                continue
            idx = self._id_to_idx[src_id]
            row_scores = cosine_similarity(
                self.tfidf_matrix[idx], self.tfidf_matrix
            ).flatten()
            for cid in candidate_set:
                if cid in self._id_to_idx:
                    scores[cid] += row_scores[self._id_to_idx[cid]]
        # normalize by number of source books
        n = max(len(source_book_ids), 1)
        return {k: v / n for k, v in scores.items()}

    def save(self):
        with open(os.path.join(MODEL_PATH, 'content_model.pkl'), 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls):
        path = os.path.join(MODEL_PATH, 'content_model.pkl')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None


class CollaborativeRecommender:
    """Matrix Factorization via TruncatedSVD on user-book rating matrix."""

    def __init__(self, n_components=20):
        self.n_components = n_components
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.scaler = MinMaxScaler()
        self.user_factors = None
        self.book_factors = None
        self.user_ids = []
        self.book_ids = []
        self._user_to_idx = {}
        self._book_to_idx = {}

    def fit(self, ratings_df):
        if ratings_df.empty or len(ratings_df) < 5:
            return self

        pivot = ratings_df.pivot_table(
            index='user_id', columns='book_id', values='score', fill_value=0
        )
        self.user_ids = pivot.index.tolist()
        self.book_ids = pivot.columns.tolist()
        self._user_to_idx = {uid: i for i, uid in enumerate(self.user_ids)}
        self._book_to_idx = {bid: i for i, bid in enumerate(self.book_ids)}

        matrix = pivot.values
        n_components = min(self.n_components, min(matrix.shape) - 1)
        if n_components < 1:
            return self

        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.user_factors = self.svd.fit_transform(matrix)
        self.book_factors = self.svd.components_.T
        return self

    def recommend_for_user(self, user_id, n=10, exclude_ids=None):
        if self.user_factors is None or user_id not in self._user_to_idx:
            return []
        exclude_ids = set(exclude_ids or [])
        u_idx = self._user_to_idx[user_id]
        scores = self.user_factors[u_idx] @ self.book_factors.T
        ranked = np.argsort(scores)[::-1]
        results = []
        for i in ranked:
            bid = self.book_ids[i]
            if bid not in exclude_ids and len(results) < n:
                results.append((bid, float(scores[i])))
        return results

    def get_user_collab_scores(self, user_id: int, candidate_ids: list) -> dict:
        """Return {book_id: collab_score} for a specific set of candidates."""
        if self.user_factors is None or user_id not in self._user_to_idx:
            return {cid: 0.0 for cid in candidate_ids}
        u_idx = self._user_to_idx[user_id]
        raw = self.user_factors[u_idx] @ self.book_factors.T
        result = {}
        for cid in candidate_ids:
            if cid in self._book_to_idx:
                result[cid] = float(raw[self._book_to_idx[cid]])
            else:
                result[cid] = 0.0
        return result

    def save(self):
        with open(os.path.join(MODEL_PATH, 'collab_model.pkl'), 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls):
        path = os.path.join(MODEL_PATH, 'collab_model.pkl')
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None


class HybridRecommender:
    """Combines content-based, collaborative filtering, and Bayesian scoring."""

    def __init__(self, content_weight=0.4, collab_weight=0.6):
        self.content_weight = content_weight
        self.collab_weight = collab_weight
        self.content_model = ContentBasedRecommender()
        self.collab_model = CollaborativeRecommender()
        self._trained = False
        self._books_df = None   # kept in memory for scorer + tags

    def train(self, books_df, ratings_df):
        print("[AI] Training Content-Based model...")
        self.content_model.fit(books_df)

        print("[AI] Training Collaborative Filtering model...")
        self.collab_model.fit(ratings_df)

        self._books_df = books_df.copy()
        self._trained = True
        self.content_model.save()
        self.collab_model.save()
        _cache_invalidate()
        print("[AI] Models trained and saved.")

    def recommend(self, user_id, liked_book_ids, rated_book_ids, n=12):
        """
        Hybrid recommendations with Bayesian re-ranking.
        Returns [(book_id, score, reason_str), ...]
        """
        cached = _cache_get(user_id)
        if cached is not None:
            return cached

        from ml.scorer import compute_book_scores
        from ml.embeddings import extract_tags, explain_recommendation

        exclude = set(rated_book_ids)
        scores = {}

        # --- Collaborative scores ---
        collab_recs = self.collab_model.recommend_for_user(user_id, n=80, exclude_ids=exclude)
        if collab_recs:
            max_s = max(s for _, s in collab_recs) or 1
            for bid, s in collab_recs:
                scores[bid] = scores.get(bid, 0) + self.collab_weight * (s / max_s)

        # --- Content-based scores ---
        for liked_id in liked_book_ids[:5]:
            content_recs = self.content_model.recommend(liked_id, n=40, exclude_ids=exclude)
            if content_recs:
                max_s = max(s for _, s in content_recs) or 1
                for bid, s in content_recs:
                    scores[bid] = scores.get(bid, 0) + self.content_weight * (s / max_s)

        if not scores:
            return []

        # --- Bayesian re-ranking ---
        if self._books_df is not None:
            candidate_ids = list(scores.keys())
            candidate_books = self._books_df[
                self._books_df['id'].isin(candidate_ids)
            ].to_dict('records')

            # pass ML scores into the Bayesian scorer
            collab_lookup = dict(self.collab_model.get_user_collab_scores(user_id, candidate_ids))
            content_lookup = self.content_model.score_candidates(liked_book_ids, candidate_ids)

            scored = compute_book_scores(
                candidate_books,
                content_weight=self.content_weight,
                collab_weight=self.collab_weight,
                content_scores=content_lookup,
                collab_scores=collab_lookup,
            )
            sorted_ids = [b['id'] for b in scored[:n]]
        else:
            sorted_books = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            sorted_ids = [bid for bid, _ in sorted_books[:n]]

        # --- Build explanation tags ---
        reasons = {}
        if self._books_df is not None:
            try:
                all_tags = extract_tags(self._books_df)
                liked_tags = [all_tags.get(bid, []) for bid in liked_book_ids[:5]]
                for bid in sorted_ids:
                    candidate_tags = all_tags.get(bid, [])
                    reasons[bid] = explain_recommendation(liked_tags, candidate_tags)
            except Exception:
                pass

        result = [
            (bid, round(scores.get(bid, 0), 4), reasons.get(bid, "Recommended for you"))
            for bid in sorted_ids
        ]
        _cache_set(user_id, result)
        return result

    def recommend_similar(self, book_id, n=8, exclude_ids=None):
        return self.content_model.recommend(book_id, n=n, exclude_ids=exclude_ids)

    def recommend_popular_by_genre(self, genre, books_df, n=8):
        filtered = books_df[books_df['genre'].str.lower() == genre.lower()]
        if filtered.empty:
            filtered = books_df
        top = filtered.nlargest(n, 'avg_rating')
        return top['id'].tolist()

    def get_user_genre_profile(self, rated_books_with_scores: list) -> dict:
        """
        Returns {genre: avg_score} for a user's rated books.
        rated_books_with_scores: [(book_dict, score), ...]
        Used by the profile page to show taste breakdown.
        """
        from collections import defaultdict
        genre_scores = defaultdict(list)
        for book, score in rated_books_with_scores:
            genre = book.get('genre', 'Unknown')
            genre_scores[genre].append(score)
        return {
            genre: round(sum(scores) / len(scores), 2)
            for genre, scores in genre_scores.items()
        }

    @property
    def is_trained(self):
        return self._trained


# Singleton
_recommender = None


def get_recommender():
    global _recommender
    if _recommender is None:
        _recommender = HybridRecommender()
        content = ContentBasedRecommender.load()
        collab = CollaborativeRecommender.load()
        if content:
            _recommender.content_model = content
        if collab:
            _recommender.collab_model = collab
        if content and collab:
            _recommender._trained = True
    return _recommender