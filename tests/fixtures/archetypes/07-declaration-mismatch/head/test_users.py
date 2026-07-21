from users import get_user


def test_existing_id_returns_the_record():
    users = {1: {"name": "Ada"}}
    assert get_user(users, 1) == {"name": "Ada"}
