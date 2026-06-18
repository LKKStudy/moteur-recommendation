import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # FIX: raise hard error if SECRET_KEY missing — no insecure fallback in prod
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set it in your .env file before running the app."
        )

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        'mysql+pymysql://root:password@localhost/book_recommender'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'