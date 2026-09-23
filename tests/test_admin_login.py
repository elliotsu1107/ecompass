def test_admin_page_redirects_anonymous_visitor_to_login(client):
    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_import_page_redirects_anonymous_visitor_to_login(client):
    response = client.get("/import", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_admin_page_renders_after_login(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "ecompass123"},
        follow_redirects=False,
    )

    response = client.get("/admin")

    assert response.status_code == 200
    assert 'data-section="stores"' in response.text


def test_admin_api_still_returns_401_for_anonymous_callers(client):
    assert client.get("/api/admin/stores").status_code == 401


def test_dashboard_links_to_admin_login(client):
    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/login"' in response.text
    assert "后台管理" in response.text


def test_login_layout_keeps_fields_and_submit_button_in_form(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert '<form method="post" action="/login">' in response.text
    assert 'class="login-field"' in response.text
    assert 'id="username"' in response.text
    assert 'id="password"' in response.text
    assert '<button type="submit">登录</button>' in response.text
    assert ".login-field{align-items:flex-start;flex-direction:column" in response.text
