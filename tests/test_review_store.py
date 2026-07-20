from acceptance.review_state import ChangeSet, Review
from acceptance.review_store import ReviewStore


def test_read_missing_revision_returns_none(tmp_path):
    store = ReviewStore(tmp_path / "reviews")
    assert store.read("deadbeef") is None


def test_review_round_trips_through_the_store(tmp_path):
    store = ReviewStore(tmp_path / "reviews")
    review = Review(
        mode="local",
        reviewed_revision="head1",
        change_set=ChangeSet(base_revision="base1", head_revision="head1"),
    )

    store.write(review)

    assert store.read("head1") == review


def test_rerun_over_the_same_head_overwrites_in_place(tmp_path):
    store = ReviewStore(tmp_path / "reviews")
    store.write(Review(mode="local", reviewed_revision="head1", recommendation="first"))
    store.write(Review(mode="local", reviewed_revision="head1", recommendation="second"))

    assert store.read("head1").recommendation == "second"
    assert list((tmp_path / "reviews").glob("*.json")) == [store.path_for("head1")]


def test_stored_form_is_canonical(tmp_path):
    store = ReviewStore(tmp_path / "reviews")
    review = Review(mode="local", reviewed_revision="head1")

    path = store.write(review)

    assert path.read_text() == review.to_canonical_json() + "\n"
