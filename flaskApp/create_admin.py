from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import config

client = MongoClient(config.MONGO_URI)
db = client.boutique

db.users.insert_one({
    "username": "admin",
    "password": generate_password_hash("4011@"),
    "is_admin": True
})

print("Admin créé avec succès")
