"""
Auto-tag extraction from book descriptions using TF-IDF term weights.

For each book, identifies the top N most "distinctive" words in its
description relative to the full corpus — these become the book's tags.
Used to power the "Why recommended" explanation feature.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re


_CUSTOM_STOP = {
    'book', 'novel', 'story', 'world', 'life', 'man', 'woman', 'one',
    'time', 'tells', 'set', 'become', 'new', 'year', 'way', 'find',
    'young', 'must', 'day', 'takes', 'place', 'follows', 'tells',
    'written', 'based', 'follows', 'known', 'called',
}


def extract_tags(books_df, n_tags: int = 5) -> dict:
    """
    Given a DataFrame with [id, title, genre, description],
    returns {book_id: [tag1, tag2, ...]} for all books.
    """
    if books_df.empty:
        return {}

    books_df = books_df.fillna('')
    corpus = (
        books_df['description'] + ' ' +
        books_df['title'] + ' ' +
        books_df['author']
    ).tolist()

    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        max_features=3000,
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)
    feature_names = np.array(vectorizer.get_feature_names_out())

    tags = {}
    for i, row in books_df.iterrows():
        book_id = row['id']
        vec = tfidf_matrix[books_df.index.get_loc(i)]
        scores = vec.toarray().flatten()
        top_indices = np.argsort(scores)[::-1]

        book_tags = []
        for idx in top_indices:
            term = feature_names[idx]
            # skip custom stops and single-letter terms
            words = term.split()
            if any(w in _CUSTOM_STOP for w in words):
                continue
            if all(len(w) <= 2 for w in words):
                continue
            # Capitalize nicely
            book_tags.append(' '.join(w.capitalize() for w in words))
            if len(book_tags) >= n_tags:
                break

        tags[book_id] = book_tags

    return tags


def explain_recommendation(liked_book_tags: list[list[str]],
                            candidate_tags: list[str]) -> str:
    """
    Generate a short human-readable explanation for why a book was recommended.

    liked_book_tags: list of tag lists from books the user liked
    candidate_tags:  tags of the recommended book
    """
    if not liked_book_tags or not candidate_tags:
        return "Matches your reading history"

    # flatten and count tag frequency across liked books
    liked_flat = [t.lower() for tags in liked_book_tags for t in tags]
    candidate_lower = [t.lower() for t in candidate_tags]

    # find overlap
    overlap = [t for t in candidate_lower if t in liked_flat]

    if overlap:
        # Show up to 2 matching themes
        shown = [t.capitalize() for t in overlap[:2]]
        return f"Shares themes: {', '.join(shown)}"
    else:
        # Fall back to genre/first tag
        return f"Based on your taste in {candidate_tags[0]}" if candidate_tags else "Recommended for you"