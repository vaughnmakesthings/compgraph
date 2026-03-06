from compgraph.db.models import Posting, PostingEnrichment


def test_posting_enrichment_has_embedding_column():
    columns = PostingEnrichment.__table__.columns
    assert "embedding" in columns
    col = columns["embedding"]
    assert col.nullable is True


def test_posting_has_latitude_column():
    columns = Posting.__table__.columns
    assert "latitude" in columns
    col = columns["latitude"]
    assert col.nullable is True


def test_posting_has_longitude_column():
    columns = Posting.__table__.columns
    assert "longitude" in columns
    col = columns["longitude"]
    assert col.nullable is True


def test_posting_has_h3_index_column():
    columns = Posting.__table__.columns
    assert "h3_index" in columns
    col = columns["h3_index"]
    assert col.nullable is True


def test_posting_h3_index_has_max_length():
    col = Posting.__table__.columns["h3_index"]
    assert col.type.length == 15


def test_posting_enrichment_embedding_dimension():
    col = PostingEnrichment.__table__.columns["embedding"]
    assert col.type.dim == 384
