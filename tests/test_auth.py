"""
OJ System - Step 3: 用户与权限管理测试
"""
import json
import pytest


class TestAuthRegister:
    """注册相关测试"""

    def test_register_success(self, client):
        """注册成功 → 201，默认角色 student"""
        resp = client.post("/api/auth/register", json={
            "username": "new_student",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["role"] == "student"
        assert data["data"]["username"] == "new_student"
        assert "password" not in str(data)
        assert "password_hash" not in str(data)

    def test_register_duplicate_username(self, client):
        """重复用户名 → 409"""
        client.post("/api/auth/register", json={"username": "dup", "password": "password123"})
        resp = client.post("/api/auth/register", json={"username": "dup", "password": "password456"})
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        """密码过短 → 422"""
        resp = client.post("/api/auth/register", json={"username": "test", "password": "123"})
        assert resp.status_code == 422

    def test_register_short_username(self, client):
        """用户名过短 → 422"""
        resp = client.post("/api/auth/register", json={"username": "ab", "password": "password123"})
        assert resp.status_code == 422

    def test_register_long_username(self, client):
        """用户名过长 → 422"""
        resp = client.post("/api/auth/register", json={
            "username": "a" * 33,
            "password": "password123",
        })
        assert resp.status_code == 422


class TestAuthLogin:
    """登录相关测试"""

    def test_login_success(self, client):
        """登录成功 → 200，Session 已设置"""
        client.post("/api/auth/register", json={"username": "login_test", "password": "password123"})
        resp = client.post("/api/auth/login", json={"username": "login_test", "password": "password123"})
        assert resp.status_code == 200
        # 验证 Session 已设置（后续请求应返回 200）
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["data"]["username"] == "login_test"

    def test_login_wrong_password(self, client):
        """密码错误 → 401"""
        client.post("/api/auth/register", json={"username": "test2", "password": "correct"})
        resp = client.post("/api/auth/login", json={"username": "test2", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户名 → 401（不暴露用户是否存在）"""
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})
        assert resp.status_code == 401

    def test_login_wrong_username(self, client):
        """错误用户名 → 401（与密码错误信息完全一致）"""
        client.post("/api/auth/register", json={"username": "real", "password": "correct"})
        r1 = client.post("/api/auth/login", json={"username": "real", "password": "wrong"}).json()
        r2 = client.post("/api/auth/login", json={"username": "fake", "password": "correct"}).json()
        # 两种错误返回相同的错误信息
        assert r1["message"] == r2["message"]


class TestAuthLogout:
    """登出相关测试"""

    def test_logout(self, client):
        """登出后 Session 失效 → /auth/me 返回 401"""
        client.post("/api/auth/register", json={"username": "logout_test", "password": "password123"})
        client.post("/api/auth/login", json={"username": "logout_test", "password": "password123"})
        # 登录后可以访问
        assert client.get("/api/auth/me").status_code == 200
        # 登出
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        # 登出后无法访问
        assert client.get("/api/auth/me").status_code == 401


class TestAuthMe:
    """当前用户信息测试"""

    def test_me_unauthenticated(self, client):
        """未登录 → 401"""
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_returns_no_password(self, client):
        """不返回密码或密码哈希"""
        client.post("/api/auth/register", json={"username": "me_test", "password": "password123"})
        client.post("/api/auth/login", json={"username": "me_test", "password": "password123"})
        resp = client.get("/api/auth/me")
        data = resp.json()["data"]
        assert "password" not in data
        assert "password_hash" not in data


class TestDisabledUser:
    """禁用用户相关测试"""

    def test_disabled_user_cannot_login(self, admin_client, client):
        """禁用用户登录 → 403"""
        # 注册新用户
        client.post("/api/auth/register", json={"username": "to_disable", "password": "password123"})
        # 管理员禁用该用户
        users = admin_client.get("/api/users").json()
        uid = None
        for u in users["data"]["items"]:
            if u["username"] == "to_disable":
                uid = u["id"]
                break
        admin_client.put(f"/api/users/{uid}", json={"is_active": False})
        # 该用户尝试登录
        resp = client.post("/api/auth/login", json={"username": "to_disable", "password": "password123"})
        assert resp.status_code == 403


class TestUserManagement:
    """用户管理测试（管理员）"""

    def test_admin_list_users(self, admin_client):
        """管理员查看分页用户列表"""
        resp = admin_client.get("/api/users?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1

    def test_admin_get_user(self, admin_client):
        """管理员查看单个用户"""
        users = admin_client.get("/api/users").json()
        uid = users["data"]["items"][0]["id"]
        resp = admin_client.get(f"/api/users/{uid}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == uid

    def test_admin_update_role(self, admin_client, client):
        """管理员修改用户角色"""
        client.post("/api/auth/register", json={"username": "to_promote", "password": "password123"})
        users = admin_client.get("/api/users").json()
        uid = None
        for u in users["data"]["items"]:
            if u["username"] == "to_promote":
                uid = u["id"]
                break
        resp = admin_client.put(f"/api/users/{uid}", json={"role": "teacher"})
        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "teacher"

    def test_admin_cannot_modify_self(self, admin_client):
        """管理员不能修改自己的账号（角色/启用状态） → 400"""
        users = admin_client.get("/api/users").json()
        admin_uid = None
        for u in users["data"]["items"]:
            if u["role"] == "admin":
                admin_uid = u["id"]
                break
        resp = admin_client.put(f"/api/users/{admin_uid}", json={"is_active": False})
        assert resp.status_code == 400

        resp2 = admin_client.put(f"/api/users/{admin_uid}", json={"role": "teacher"})
        assert resp2.status_code == 400

    def test_nonexistent_user(self, admin_client):
        """查询不存在的用户 → 404"""
        resp = admin_client.get("/api/users/nonexistent-id")
        assert resp.status_code == 404

    def test_invalid_role_update(self, admin_client):
        """修改为无效角色 → 422"""
        users = admin_client.get("/api/users").json()
        uid = users["data"]["items"][0]["id"]
        resp = admin_client.put(f"/api/users/{uid}", json={"role": "superadmin"})
        assert resp.status_code == 422


class TestPermissionControl:
    """权限控制测试"""

    def test_student_cannot_manage_users(self, student_client):
        """学生无权访问用户管理 → 403"""
        assert student_client.get("/api/users").status_code == 403
        assert student_client.get("/api/users/some-id").status_code == 403
        assert student_client.put("/api/users/some-id", json={"role": "admin"}).status_code == 403

    def test_teacher_cannot_manage_users(self, teacher_client):
        """教师无权访问用户管理 → 403"""
        assert teacher_client.get("/api/users").status_code == 403
        assert teacher_client.get("/api/users/some-id").status_code == 403

    def test_unauthenticated_cannot_access(self, client):
        """未登录无法访问受保护接口"""
        assert client.get("/api/auth/me").status_code == 401
        assert client.get("/api/users").status_code == 401
