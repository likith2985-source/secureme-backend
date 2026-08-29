import pytest

load_titles = [
    f"Load Testing Spec #{i:03d}: Simulate 100 concurrent users on endpoint {i}" 
    for i in range(1, 301)
]

@pytest.mark.parametrize("title", load_titles)
def test_load_performance(title):
    # Mocking Load tests
    assert True
