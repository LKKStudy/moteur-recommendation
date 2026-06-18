"""
Bayesian Average Rating scorer + Popularity decay.

Bayesian average shrinks a book's raw avg toward the global mean
when it has few ratings, preventing a 1-rating 5.0 book from
ranking above a 1000-rating 4.7 book.

  score = (C * m + n * R) / (C + n)
    R = book's avg rating
    n = book's rating count
    m = global mean rating
    C = confidence constant (min ratings before score is trusted)
"""

import math


def bayesian_avg(avg_rating: float, rating_count: int,
                 global_mean: float, confidence: int = 25) -> float:
    """Return Bayesian-smoothed rating score."""
    return (confidence * global_mean + rating_count * avg_rating) / (confidence + rating_count)


def popularity_score(rating_count: int, max_count: int) -> float:
    """Log-normalized popularity in [0, 1]. Prevents mega-popular books from dominating."""
    if max_count <= 0:
        return 0.0
    return math.log1p(rating_count) / math.log1p(max_count)


def compute_book_scores(books: list[dict],
                        content_weight: float = 0.0,
                        collab_weight: float = 0.0,
                        content_scores: dict = None,
                        collab_scores: dict = None) -> list[dict]:
    """
    Combine Bayesian rating, popularity, and ML scores into one final score.

    books: list of book dicts (must have id, avg_rating, rating_count)
    content_scores: {book_id: float} from content-based model
    collab_scores:  {book_id: float} from collaborative model

    Returns books list sorted by final_score descending,
    each dict augmented with: bayesian_score, popularity, final_score
    """
    if not books:
        return []

    content_scores = content_scores or {}
    collab_scores = collab_scores or {}

    global_mean = sum(b['avg_rating'] for b in books) / len(books)
    max_count = max(b['rating_count'] for b in books) or 1

    results = []
    for b in books:
        bid = b['id']
        b_score = bayesian_avg(b['avg_rating'], b['rating_count'], global_mean)
        p_score = popularity_score(b['rating_count'], max_count)

        # normalize bayesian to [0,1] using known range [1,5]
        b_norm = (b_score - 1) / 4

        # ML scores already in [0,1]
        c_score = content_scores.get(bid, 0.0)
        cf_score = collab_scores.get(bid, 0.0)

        # Weighted combination
        final = (
            0.35 * b_norm +
            0.15 * p_score +
            content_weight * c_score +
            collab_weight * cf_score
        )

        results.append({
            **b,
            'bayesian_score': round(b_score, 3),
            'popularity_score': round(p_score, 3),
            'final_score': round(final, 4),
        })

    results.sort(key=lambda x: x['final_score'], reverse=True)
    return results