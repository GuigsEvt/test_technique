from app.core.utils import make_chunks


def test_make_chunks_overlap_and_metadata():
    text = "A" * 2500
    chunks = make_chunks(text, doc_id="doc::1", filename="file.txt", source_type=".txt", max_chars=1000, overlap=200)
    assert len(chunks) == 3

    _, first, _ = chunks[0]
    _, second, meta_second = chunks[1]
    assert second.startswith("A" * 200)  # overlap zone
    assert meta_second["chunk_index"] == 1
    assert meta_second["doc_id"] == "doc::1"
