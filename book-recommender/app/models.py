from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash
from sqlalchemy import func


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ FIX 2 — added missing column
    preferred_genres = db.Column(db.String(500), default='')

    ratings = db.relationship('Rating', backref='user', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    reading_list = db.relationship('ReadingList', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ✅ FIX 2 — added missing method
    def get_preferred_genres(self):
        if not self.preferred_genres:
            return []
        return [g.strip() for g in self.preferred_genres.split(',') if g.strip()]

    def __repr__(self):
        return f'<User {self.username}>'


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    genre = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    published_year = db.Column(db.Integer)
    avg_rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    language = db.Column(db.String(30), default='English')
    pages = db.Column(db.Integer)
    isbn = db.Column(db.String(20), unique=True)

    # ✅ FIX 3 — added missing column
    tags = db.Column(db.String(500), default='')

    ratings = db.relationship('Rating', backref='book', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='book', lazy='dynamic')
    reading_list_entries = db.relationship('ReadingList', backref='book', lazy='dynamic')

    def update_avg_rating(self):
        result = db.session.query(
            func.avg(Rating.score),
            func.count(Rating.id)
        ).filter(Rating.book_id == self.id).one()
        self.avg_rating = round(float(result[0] or 0), 2)
        self.rating_count = result[1]
        db.session.commit()

    # ✅ FIX 3 — added missing method
    def get_tags(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'genre': self.genre,
            'description': self.description,
            'cover_url': self.cover_url,
            'published_year': self.published_year,
            'avg_rating': round(self.avg_rating, 1),
            'rating_count': self.rating_count,
            'language': self.language,
            'pages': self.pages,
        }

    def __repr__(self):
        return f'<Book {self.title}>'


class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # 1.0 to 5.0
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_rating'),
        db.Index('ix_rating_user_id', 'user_id'),
        db.Index('ix_rating_book_id', 'book_id'),
    )

    def __repr__(self):
        return f'<Rating user={self.user_id} book={self.book_id} score={self.score}>'


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_fav'),
        db.Index('ix_favorite_user_id', 'user_id'),
        db.Index('ix_favorite_book_id', 'book_id'),
    )


# ✅ FIX 1 — ReadingList model was completely missing
class ReadingList(db.Model):
    __tablename__ = 'reading_list'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default='want_to_read'
    )  # 'want_to_read' | 'reading' | 'finished'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book_rl'),
        db.Index('ix_rl_user_id', 'user_id'),
        db.Index('ix_rl_book_id', 'book_id'),
    )

    def __repr__(self):
        return f'<ReadingList user={self.user_id} book={self.book_id} status={self.status}>'