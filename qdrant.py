from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://00672a95-2ca4-4986-a3f0-ae02d773830d.europe-west3-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.uTPXceuxj9mSIuEFdJAyTgIcHIfc4zvFsGEejnuikA4",
)

print(qdrant_client.get_collections())