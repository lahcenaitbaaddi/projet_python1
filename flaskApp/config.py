from dotenv import load_dotenv
import os

# Charge votre fichier .env personnalisé
load_dotenv(dotenv_path="fich.env")

MONGO_URI = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY")
