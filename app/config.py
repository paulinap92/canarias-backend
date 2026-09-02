import os

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = (
    "postgresql+psycopg://canarias:canarias_dev@localhost:5432/canarias"
)

AEMET_API_KEY = os.getenv("AEMET_API_KEY")