import chromadb
from app.db.database import settings

client = chromadb.PersistentClient(path=str(settings.LOCAL_STORAGE_PATH) + "/chroma")
collection = client.get_collection(settings.CHROMA_COLLECTION)

query1 = "whats birthdate of gandhi"
results1 = collection.query(query_texts=[query1], n_results=1)

query2 = "What are the rules for customs clearance?"
results2 = collection.query(query_texts=[query2], n_results=1)

print("Gandhi Distance:", results1.get("distances"))
print("Customs Distance:", results2.get("distances"))
