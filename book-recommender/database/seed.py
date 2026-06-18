"""
Seed the database with books and sample ratings.
Run once: python database/seed.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import Book, User, Rating
import random

BOOKS = [
    # --- Fiction ---
    {"title": "The Name of the Wind", "author": "Patrick Rothfuss", "genre": "Fantasy",
     "description": "A young man grows to become the most notorious wizard his world has ever seen.",
     "published_year": 2007, "pages": 662, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739161-L.jpg"},
    {"title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi",
     "description": "Epic sci-fi saga set on the desert planet Arrakis, home of the spice melange.",
     "published_year": 1965, "pages": 688, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8475472-L.jpg"},
    {"title": "1984", "author": "George Orwell", "genre": "Dystopia",
     "description": "A totalitarian society where Big Brother watches your every move.",
     "published_year": 1949, "pages": 328, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575708-L.jpg"},
    {"title": "The Hitchhiker's Guide to the Galaxy", "author": "Douglas Adams", "genre": "Sci-Fi",
     "description": "A comedic adventure through space after Earth is demolished for a hyperspace bypass.",
     "published_year": 1979, "pages": 193, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406786-L.jpg"},
    {"title": "Neuromancer", "author": "William Gibson", "genre": "Sci-Fi",
     "description": "The seminal cyberpunk novel about a washed-up hacker hired for one last job.",
     "published_year": 1984, "pages": 271, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406798-L.jpg"},
    {"title": "The Way of Kings", "author": "Brandon Sanderson", "genre": "Fantasy",
     "description": "Epic fantasy on a world of stone and storms, where ancient secrets reshape a war.",
     "published_year": 2010, "pages": 1007, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739162-L.jpg"},
    {"title": "Brave New World", "author": "Aldous Huxley", "genre": "Dystopia",
     "description": "A future where humans are engineered and conditioned for happiness at the cost of freedom.",
     "published_year": 1932, "pages": 311, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575709-L.jpg"},
    {"title": "The Hobbit", "author": "J.R.R. Tolkien", "genre": "Fantasy",
     "description": "Bilbo Baggins goes on an unexpected journey with dwarves and a wizard.",
     "published_year": 1937, "pages": 310, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406799-L.jpg"},
    {"title": "Foundation", "author": "Isaac Asimov", "genre": "Sci-Fi",
     "description": "A mathematician predicts the collapse of the Galactic Empire and plans to preserve knowledge.",
     "published_year": 1951, "pages": 255, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739163-L.jpg"},
    {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "genre": "Sci-Fi",
     "description": "An envoy travels to a planet of genderless humans in this groundbreaking sci-fi classic.",
     "published_year": 1969, "pages": 286, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406800-L.jpg"},
    # --- Mystery ---
    {"title": "The Girl with the Dragon Tattoo", "author": "Stieg Larsson", "genre": "Mystery",
     "description": "A journalist and a hacker investigate a 40-year-old disappearance in a powerful Swedish family.",
     "published_year": 2005, "pages": 465, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739164-L.jpg"},
    {"title": "Gone Girl", "author": "Gillian Flynn", "genre": "Mystery",
     "description": "On their anniversary, Amy Dunne disappears and her husband becomes the prime suspect.",
     "published_year": 2012, "pages": 422, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575710-L.jpg"},
    {"title": "And Then There Were None", "author": "Agatha Christie", "genre": "Mystery",
     "description": "Ten strangers are invited to an island and begin to be murdered one by one.",
     "published_year": 1939, "pages": 272, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406801-L.jpg"},
    {"title": "The Da Vinci Code", "author": "Dan Brown", "genre": "Mystery",
     "description": "A symbologist unravels a conspiracy hidden in Leonardo da Vinci's artwork.",
     "published_year": 2003, "pages": 454, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739165-L.jpg"},
    # --- Non-Fiction ---
    {"title": "Sapiens", "author": "Yuval Noah Harari", "genre": "Non-Fiction",
     "description": "A brief history of humankind from the Stone Age to the 21st century.",
     "published_year": 2011, "pages": 443, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575711-L.jpg"},
    {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "genre": "Non-Fiction",
     "description": "Explores the two systems that drive the way we think and make choices.",
     "published_year": 2011, "pages": 499, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739166-L.jpg"},
    {"title": "The Lean Startup", "author": "Eric Ries", "genre": "Business",
     "description": "How entrepreneurs use continuous innovation to create successful businesses.",
     "published_year": 2011, "pages": 336, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406802-L.jpg"},
    {"title": "Atomic Habits", "author": "James Clear", "genre": "Self-Help",
     "description": "An easy and proven way to build good habits and break bad ones.",
     "published_year": 2018, "pages": 320, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739167-L.jpg"},
    # --- Romance ---
    {"title": "Pride and Prejudice", "author": "Jane Austen", "genre": "Romance",
     "description": "The romantic clash between Elizabeth Bennet and the wealthy, arrogant Mr. Darcy.",
     "published_year": 1813, "pages": 432, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575712-L.jpg"},
    {"title": "The Notebook", "author": "Nicholas Sparks", "genre": "Romance",
     "description": "A love story spanning decades between a poor country boy and a rich city girl.",
     "published_year": 1996, "pages": 214, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406803-L.jpg"},
    # --- Horror ---
    {"title": "It", "author": "Stephen King", "genre": "Horror",
     "description": "A group of children face a terrifying entity that preys on their fears in Derry, Maine.",
     "published_year": 1986, "pages": 1138, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739168-L.jpg"},
    {"title": "Dracula", "author": "Bram Stoker", "genre": "Horror",
     "description": "The classic epistolary novel of Count Dracula's attempt to move from Transylvania to England.",
     "published_year": 1897, "pages": 418, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8575713-L.jpg"},
    # --- Historical ---
    {"title": "The Pillars of the Earth", "author": "Ken Follett", "genre": "Historical",
     "description": "The building of a cathedral in 12th-century England and the lives it shapes.",
     "published_year": 1989, "pages": 973, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8406804-L.jpg"},
    {"title": "All the Light We Cannot See", "author": "Anthony Doerr", "genre": "Historical",
     "description": "Parallel stories of a blind French girl and a German boy during World War II.",
     "published_year": 2014, "pages": 531, "language": "English",
     "cover_url": "https://covers.openlibrary.org/b/id/8739169-L.jpg"},
]


def seed():
    app = create_app()
    with app.app_context():
        # Create tables
        db.create_all()

        # Clear existing data
        Rating.query.delete()
        Book.query.delete()
        User.query.delete()
        db.session.commit()

        # Insert books
        books = []
        for b in BOOKS:
            book = Book(**b)
            book.avg_rating = round(random.uniform(3.5, 5.0), 1)
            book.rating_count = random.randint(50, 5000)
            db.session.add(book)
            books.append(book)
        db.session.commit()
        print(f"[Seed] Inserted {len(books)} books.")

        # Create demo users
        users = []
        demo_users = [
            ("alice", "alice@example.com", "password123"),
            ("bob", "bob@example.com", "password123"),
            ("charlie", "charlie@example.com", "password123"),
            ("diana", "diana@example.com", "password123"),
            ("eve", "eve@example.com", "password123"),
        ]
        for username, email, pwd in demo_users:
            u = User(username=username, email=email)
            u.set_password(pwd)
            db.session.add(u)
            users.append(u)
        db.session.commit()
        print(f"[Seed] Inserted {len(users)} demo users.")

        # Generate synthetic ratings
        genres_liked = {
            "alice": ["Fantasy", "Sci-Fi"],
            "bob": ["Mystery", "Horror"],
            "charlie": ["Non-Fiction", "Business", "Self-Help"],
            "diana": ["Romance", "Historical"],
            "eve": ["Sci-Fi", "Dystopia"],
        }
        rating_count = 0
        for user in users:
            liked = genres_liked.get(user.username, [])
            for book in books:
                if random.random() < 0.4:   # 40% chance of rating
                    if book.genre in liked:
                        score = round(random.uniform(3.8, 5.0), 1)
                    else:
                        score = round(random.uniform(1.5, 4.0), 1)
                    r = Rating(user_id=user.id, book_id=book.id, score=score)
                    db.session.add(r)
                    rating_count += 1
        db.session.commit()
        print(f"[Seed] Inserted {rating_count} ratings.")

        # Train AI models
        from ml.recommender import get_recommender
        import pandas as pd
        books_data = [b.to_dict() for b in books]
        books_df = pd.DataFrame(books_data)
        ratings_data = [{"user_id": r.user_id, "book_id": r.book_id, "score": r.score}
                        for r in Rating.query.all()]
        ratings_df = pd.DataFrame(ratings_data)
        rec = get_recommender()
        rec.train(books_df, ratings_df)
        print("[Seed] AI models trained successfully!")
        print("\n[Seed] Done! Demo login: alice / password123")


if __name__ == '__main__':
    seed()
