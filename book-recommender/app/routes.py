import threading
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Book, Rating, Favorite, ReadingList
from ml.recommender import get_recommender, _cache_invalidate

main = Blueprint('main', __name__)


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────
@main.route('/')
def index():
    featured = Book.query.order_by(Book.avg_rating.desc()).limit(8).all()
    genres = db.session.query(Book.genre).distinct().all()
    genres = [g[0] for g in genres]
    return render_template('index.html', featured=featured, genres=genres)


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    genres = [g[0] for g in db.session.query(Book.genre).distinct().all()]
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        selected_genres = request.form.getlist('genres')  # NEW: genre preference

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('register.html', genres=genres)
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html', genres=genres)

        user = User(
            username=username,
            email=email,
            preferred_genres=','.join(selected_genres)
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Welcome! Rate some books to get personalized recommendations.', 'success')
        return redirect(url_for('main.books'))
    return render_template('register.html', genres=genres)


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# ─────────────────────────────────────────────
# BOOKS CATALOG
# ─────────────────────────────────────────────
@main.route('/books')
def books():
    genre = request.args.get('genre', '')
    search = request.args.get('q', '')
    sort = request.args.get('sort', 'rating')   # NEW: sort param
    page = request.args.get('page', 1, type=int)

    query = Book.query
    if genre:
        query = query.filter(Book.genre == genre)
    if search:
        query = query.filter(
            Book.title.ilike(f'%{search}%') | Book.author.ilike(f'%{search}%')
        )

    # NEW: multiple sort modes
    if sort == 'newest':
        query = query.order_by(Book.published_year.desc())
    elif sort == 'popular':
        query = query.order_by(Book.rating_count.desc())
    elif sort == 'title':
        query = query.order_by(Book.title.asc())
    else:
        query = query.order_by(Book.avg_rating.desc())

    books_page = query.paginate(page=page, per_page=12)
    genres = [g[0] for g in db.session.query(Book.genre).distinct().all()]

    user_ratings = {}
    user_favorites = set()
    user_reading_list = set()
    if current_user.is_authenticated:
        for r in Rating.query.filter_by(user_id=current_user.id).all():
            user_ratings[r.book_id] = r.score
        for f in Favorite.query.filter_by(user_id=current_user.id).all():
            user_favorites.add(f.book_id)
        for rl in ReadingList.query.filter_by(user_id=current_user.id).all():
            user_reading_list.add(rl.book_id)

    return render_template('books.html',
                           books=books_page,
                           genres=genres,
                           selected_genre=genre,
                           search=search,
                           sort=sort,
                           user_ratings=user_ratings,
                           user_favorites=user_favorites,
                           user_reading_list=user_reading_list)


@main.route('/books/<int:book_id>')
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    rec = get_recommender()
    similar_ids = [bid for bid, _ in rec.recommend_similar(book_id, n=6)]
    similar_books = Book.query.filter(Book.id.in_(similar_ids)).all() if similar_ids else []

    user_rating = None
    is_favorite = False
    in_reading_list = False
    reading_list_status = None
    if current_user.is_authenticated:
        r = Rating.query.filter_by(user_id=current_user.id, book_id=book_id).first()
        user_rating = r.score if r else None
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id, book_id=book_id).first() is not None
        rl = ReadingList.query.filter_by(
            user_id=current_user.id, book_id=book_id).first()
        in_reading_list = rl is not None
        reading_list_status = rl.status if rl else None

    reviews = Rating.query.filter_by(book_id=book_id).filter(
        Rating.review.isnot(None)).limit(10).all()

    return render_template('book_detail.html',
                           book=book,
                           similar_books=similar_books,
                           user_rating=user_rating,
                           is_favorite=is_favorite,
                           in_reading_list=in_reading_list,
                           reading_list_status=reading_list_status,
                           reviews=reviews)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
@main.route('/dashboard')
@login_required
def dashboard():
    rated_books = db.session.query(Book, Rating).join(
        Rating, Rating.book_id == Book.id
    ).filter(Rating.user_id == current_user.id).order_by(Rating.score.desc()).all()

    favorites = db.session.query(Book).join(
        Favorite, Favorite.book_id == Book.id
    ).filter(Favorite.user_id == current_user.id).all()

    reading_list_items = db.session.query(ReadingList).filter_by(
        user_id=current_user.id
    ).order_by(ReadingList.added_at.desc()).all()

    rec = get_recommender()
    rated_ids = [b.id for b, _ in rated_books]
    liked_ids = [b.id for b, r in rated_books if r.score >= 4.0]
    rec_results = rec.recommend(current_user.id, liked_ids, rated_ids, n=8)

    # rec_results is now [(book_id, score, reason), ...]
    rec_ids = [bid for bid, _, _ in rec_results]
    book_map = {b.id: b for b in Book.query.filter(Book.id.in_(rec_ids)).all()} if rec_ids else {}
    recommended = []
    for bid, score, reason in rec_results:
        b = book_map.get(bid)
        if b:
            recommended.append((b, score, reason))

    # Cold start fallback
    if not recommended:
        user_genres = current_user.get_preferred_genres()
        if user_genres:
            seen = set()
            cold_books = []
            for g in user_genres:
                top = Book.query.filter(Book.genre == g)\
                    .order_by(Book.avg_rating.desc()).limit(3).all()
                for b in top:
                    if b.id not in seen:
                        cold_books.append((b, 0.0, f"Matches your interest in {g}"))
                        seen.add(b.id)
            recommended = cold_books[:8]
        else:
            fallback = Book.query.order_by(Book.avg_rating.desc()).limit(8).all()
            recommended = [(b, 0.0, "Top rated") for b in fallback]

    # Genre profile for stats
    genre_profile = {}
    if rated_books:
        genre_profile = rec.get_user_genre_profile(
            [(b.to_dict(), r.score) for b, r in rated_books]
        )

    stats = {
        'total_rated': len(rated_books),
        'favorites': len(favorites),
        'reading_list': len(reading_list_items),
        'avg_rating': round(
            sum(r.score for _, r in rated_books) / len(rated_books), 1
        ) if rated_books else 0,
        'top_genre': max(genre_profile, key=genre_profile.get) if genre_profile else '—',
    }

    return render_template('dashboard.html',
                           rated_books=rated_books,
                           favorites=favorites,
                           reading_list=reading_list_items,
                           recommended=recommended,
                           genre_profile=genre_profile,
                           stats=stats)


# ─────────────────────────────────────────────
# NEW: FULL RECOMMENDATIONS PAGE
# ─────────────────────────────────────────────
@main.route('/recommendations')
@login_required
def recommendations():
    rated_books = db.session.query(Book, Rating).join(
        Rating, Rating.book_id == Book.id
    ).filter(Rating.user_id == current_user.id).all()

    rated_ids = [b.id for b, _ in rated_books]
    liked_ids = [b.id for b, r in rated_books if r.score >= 4.0]

    rec = get_recommender()
    rec_results = rec.recommend(current_user.id, liked_ids, rated_ids, n=20)

    rec_ids = [bid for bid, _, _ in rec_results]
    book_map = {b.id: b for b in Book.query.filter(Book.id.in_(rec_ids)).all()} if rec_ids else {}
    recommended = []
    for bid, score, reason in rec_results:
        b = book_map.get(bid)
        if b:
            recommended.append((b, round(score * 100, 1), reason))

    return render_template('recommendations.html', recommended=recommended)


# ─────────────────────────────────────────────
# NEW: USER PROFILE PAGE
# ─────────────────────────────────────────────
@main.route('/profile')
@login_required
def profile():
    rated_books = db.session.query(Book, Rating).join(
        Rating, Rating.book_id == Book.id
    ).filter(Rating.user_id == current_user.id).order_by(Rating.created_at.desc()).all()

    rec = get_recommender()
    genre_profile = {}
    if rated_books:
        genre_profile = rec.get_user_genre_profile(
            [(b.to_dict(), r.score) for b, r in rated_books]
        )

    reading_list = db.session.query(ReadingList).filter_by(
        user_id=current_user.id
    ).order_by(ReadingList.added_at.desc()).all()

    top_rated = sorted(rated_books, key=lambda x: x[1].score, reverse=True)[:5]
    stats = {
        'total_rated': len(rated_books),
        'avg_rating': round(sum(r.score for _, r in rated_books) / len(rated_books), 2) if rated_books else 0,
        'total_pages': sum(b.pages or 0 for b, _ in rated_books),
        'reading_list_count': len(reading_list),
        'top_genre': max(genre_profile, key=genre_profile.get) if genre_profile else '—',
    }

    return render_template('profile.html',
                           rated_books=rated_books,
                           genre_profile=genre_profile,
                           reading_list=reading_list,
                           top_rated=top_rated,
                           stats=stats)


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────
@main.route('/api/rate', methods=['POST'])
@login_required
def api_rate():
    data = request.get_json()
    book_id = data.get('book_id')
    score = float(data.get('score', 0))
    review = data.get('review', '')

    if not book_id or score < 1 or score > 5:
        return jsonify({'error': 'Invalid data'}), 400

    book = Book.query.get_or_404(book_id)
    existing = Rating.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        existing.score = score
        existing.review = review or existing.review
    else:
        r = Rating(user_id=current_user.id, book_id=book_id, score=score, review=review)
        db.session.add(r)
    db.session.commit()
    book.update_avg_rating()

    _cache_invalidate(current_user.id)
    _retrain_models_async()

    return jsonify({'success': True, 'avg_rating': book.avg_rating})


@main.route('/api/favorite', methods=['POST'])
@login_required
def api_favorite():
    data = request.get_json()
    book_id = data.get('book_id')
    Book.query.get_or_404(book_id)

    existing = Favorite.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'favorited': False})
    else:
        f = Favorite(user_id=current_user.id, book_id=book_id)
        db.session.add(f)
        db.session.commit()
        return jsonify({'success': True, 'favorited': True})


# NEW: Reading list API
@main.route('/api/reading-list', methods=['POST'])
@login_required
def api_reading_list():
    data = request.get_json()
    book_id = data.get('book_id')
    status = data.get('status', 'want_to_read')
    Book.query.get_or_404(book_id)

    if status not in ('want_to_read', 'reading', 'finished', 'remove'):
        return jsonify({'error': 'Invalid status'}), 400

    existing = ReadingList.query.filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()

    if status == 'remove':
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return jsonify({'success': True, 'in_list': False, 'status': None})

    if existing:
        existing.status = status
    else:
        rl = ReadingList(user_id=current_user.id, book_id=book_id, status=status)
        db.session.add(rl)
    db.session.commit()
    return jsonify({'success': True, 'in_list': True, 'status': status})


@main.route('/api/recommendations')
@login_required
def api_recommendations():
    rated = Rating.query.filter_by(user_id=current_user.id).all()
    rated_ids = [r.book_id for r in rated]
    liked_ids = [r.book_id for r in rated if r.score >= 4.0]
    rec = get_recommender()
    recs = rec.recommend(current_user.id, liked_ids, rated_ids, n=10)

    book_map = {
        b.id: b
        for b in Book.query.filter(Book.id.in_([bid for bid, _, _ in recs])).all()
    }
    books = []
    for bid, score, reason in recs:
        b = book_map.get(bid)
        if b:
            d = b.to_dict()
            d['ai_score'] = score
            d['reason'] = reason
            books.append(d)
    return jsonify({'recommendations': books})


@main.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    results = Book.query.filter(
        Book.title.ilike(f'%{q}%') | Book.author.ilike(f'%{q}%')
    ).limit(8).all()
    return jsonify([b.to_dict() for b in results])


# NEW: tag a book's auto-generated tags endpoint
@main.route('/api/books/<int:book_id>/tags')
def api_book_tags(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify({'tags': book.get_tags()})


# ─────────────────────────────────────────────
# INTERNAL
# ─────────────────────────────────────────────
def _retrain_models_async():
    def _run():
        try:
            books = Book.query.all()
            ratings = Rating.query.all()
            if len(ratings) < 3:
                return
            books_df = pd.DataFrame([b.to_dict() for b in books])
            ratings_df = pd.DataFrame([
                {"user_id": r.user_id, "book_id": r.book_id, "score": r.score}
                for r in ratings
            ])
            rec = get_recommender()
            rec.train(books_df, ratings_df)

            # NEW: update auto-generated tags in the DB after retraining
            from ml.embeddings import extract_tags
            tags_map = extract_tags(books_df)
            for book in books:
                book.tags = ','.join(tags_map.get(book.id, []))
            db.session.commit()
        except Exception as e:
            print(f"[AI] Retrain failed: {e}")

    threading.Thread(target=_run, daemon=True).start()