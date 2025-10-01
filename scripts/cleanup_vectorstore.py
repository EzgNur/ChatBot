import os
from typing import List

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document


def keep_doc(doc: Document, allowed_prefix: str) -> bool:
    url = (doc.metadata or {}).get("url") or ""
    url = url.strip()
    if not url:
        return False
    return url.startswith(allowed_prefix)


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(__file__))
    vs_path = os.path.join(project_root, "data", "vectorstore")
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    print(f"📂 Vectorstore: {vs_path}")
    embeddings = HuggingFaceEmbeddings(model_name=model_name)

    try:
        vs = FAISS.load_local(vs_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"❌ Yükleme hatası: {e}")
        return

    # Eski tüm dokümanları oku
    all_docs: List[Document] = []
    store = getattr(vs, "docstore", None)
    if store and hasattr(store, "_dict"):
        all_docs = list(store._dict.values())
    else:
        # Fallback: küçük bir örnekle yetin (tam doğruluk sağlamaz)
        all_docs = [d for d, _ in vs.similarity_search_with_score(".", k=10000)]

    total = len(all_docs)
    print(f"🔍 Toplam doküman: {total}")

    allowed_prefix = os.environ.get("CLEAN_ALLOWED_PREFIX", "https://alternativkraft.com/")
    kept = [d for d in all_docs if keep_doc(d, allowed_prefix)]
    removed = total - len(kept)
    print(f"🧹 Kalan: {len(kept)}  | Silinen: {removed}  | Kriter: url startswith {allowed_prefix}")

    if not kept:
        print("⚠️ Tüm dokümanlar eleniyor; işlemi iptal ettim.")
        return

    # Yeni FAISS'i baştan oluştur ve kaydet
    new_vs = FAISS.from_documents(kept, embeddings)
    new_vs.save_local(vs_path)
    print("✅ Vectorstore temizlendi ve kaydedildi.")


if __name__ == "__main__":
    main()


