"""
Integration tests for the /books endpoints.

Covers CRUD operations, authentication guards, filtering, pagination,
and edge cases like duplicate ISBNs and missing resources.
"""
import pytest


class TestListBooks:
    def test_list_books_empty(self, client):
        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    def test_list_books_with_data(self, client, sample_books):
        response = client.get("/books")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(sample_books)
        assert len(data["items"]) == len(sample_books)

    def test_list_books_pagination(self, client, sample_books):
        response = client.get("/books?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] == len(sample_books)

    def test_list_books_second_page(self, client, sample_books):
        response = client.get("/books?page=2&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    def test_list_books_filter_by_genre(self, client, sample_books):
        response = client.get("/books?genre=Programming")
        assert response.status_code == 200
        data = response.json()
        assert all("Programming" in item["genre"] for item in data["items"])

    def test_list_books_filter_by_author(self, client, sample_books):
        response = client.get("/books?author=Martin")
        assert response.status_code == 200
        data = response.json()
        assert all("Martin" in item["author"] for item in data["items"])

    def test_list_books_filter_in_stock(self, client, sample_books):
        response = client.get("/books?in_stock=true")
        assert response.status_code == 200
        data = response.json()
        assert all(item["in_stock"] is True for item in data["items"])

    def test_list_books_filter_out_of_stock(self, client, sample_books):
        response = client.get("/books?in_stock=false")
        assert response.status_code == 200
        data = response.json()
        assert all(item["in_stock"] is False for item in data["items"])

    def test_list_books_invalid_page(self, client):
        response = client.get("/books?page=0")
        assert response.status_code == 422

    def test_list_books_page_size_too_large(self, client):
        response = client.get("/books?page_size=101")
        assert response.status_code == 422


class TestGetBook:
    def test_get_book_success(self, client, sample_book):
        response = client.get(f"/books/{sample_book.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_book.id
        assert data["title"] == sample_book.title
        assert data["isbn"] == sample_book.isbn

    def test_get_book_not_found(self, client):
        response = client.get("/books/999999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Book not found"

    def test_get_book_does_not_require_auth(self, client, sample_book):
        """Public read access — no token needed."""
        response = client.get(f"/books/{sample_book.id}")
        assert response.status_code == 200


class TestCreateBook:
    VALID_PAYLOAD = {
        "title": "Test Driven Development",
        "author": "Kent Beck",
        "isbn": "9780321146533",
        "price": 39.99,
        "genre": "Programming",
        "published_year": 2002,
        "in_stock": True,
    }

    def test_create_book_success(self, client, auth_headers):
        response = client.post("/books", json=self.VALID_PAYLOAD, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == self.VALID_PAYLOAD["title"]
        assert data["isbn"] == self.VALID_PAYLOAD["isbn"]
        assert "id" in data

    def test_create_book_requires_auth(self, client):
        response = client.post("/books", json=self.VALID_PAYLOAD)
        assert response.status_code == 401

    def test_create_book_duplicate_isbn(self, client, auth_headers, sample_book):
        payload = {**self.VALID_PAYLOAD, "isbn": sample_book.isbn}
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert "ISBN already exists" in response.json()["detail"]

    def test_create_book_negative_price(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "price": -5.0, "isbn": "9780000000001"}
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_book_zero_price(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "price": 0, "isbn": "9780000000002"}
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_book_invalid_isbn(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "isbn": "not-an-isbn"}
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_book_empty_title(self, client, auth_headers):
        payload = {**self.VALID_PAYLOAD, "title": "", "isbn": "9780000000003"}
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_book_sets_owner(self, client, auth_headers, test_user):
        response = client.post("/books", json=self.VALID_PAYLOAD, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["owner_id"] == test_user.id


class TestUpdateBook:
    def test_update_book_price(self, client, auth_headers, sample_book):
        response = client.patch(
            f"/books/{sample_book.id}",
            json={"price": 19.99},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["price"] == 19.99

    def test_update_book_stock_status(self, client, auth_headers, sample_book):
        response = client.patch(
            f"/books/{sample_book.id}",
            json={"in_stock": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_stock"] is False

    def test_update_book_multiple_fields(self, client, auth_headers, sample_book):
        response = client.patch(
            f"/books/{sample_book.id}",
            json={"price": 9.99, "genre": "Classic", "in_stock": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 9.99
        assert data["genre"] == "Classic"
        assert data["in_stock"] is False

    def test_update_book_requires_auth(self, client, sample_book):
        response = client.patch(f"/books/{sample_book.id}", json={"price": 1.0})
        assert response.status_code == 401

    def test_update_book_not_found(self, client, auth_headers):
        response = client.patch("/books/999999", json={"price": 1.0}, headers=auth_headers)
        assert response.status_code == 404

    def test_update_book_invalid_price(self, client, auth_headers, sample_book):
        response = client.patch(
            f"/books/{sample_book.id}",
            json={"price": -1.0},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestDeleteBook:
    def test_delete_book_success(self, client, auth_headers, sample_book):
        response = client.delete(f"/books/{sample_book.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/books/{sample_book.id}")
        assert get_response.status_code == 404

    def test_delete_book_requires_auth(self, client, sample_book):
        response = client.delete(f"/books/{sample_book.id}")
        assert response.status_code == 401

    def test_delete_book_not_found(self, client, auth_headers):
        response = client.delete("/books/999999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_book_idempotency(self, client, auth_headers, sample_book):
        """Deleting twice should return 404 on the second attempt."""
        client.delete(f"/books/{sample_book.id}", headers=auth_headers)
        response = client.delete(f"/books/{sample_book.id}", headers=auth_headers)
        assert response.status_code == 404
