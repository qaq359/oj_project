"""
OJ System - Streamlit 前端
启动命令: streamlit run frontend/app.py
"""
import streamlit as st
import requests
import time
import json

API_BASE = "http://127.0.0.1:8000/api"


# ──────────────────── API 封装 ────────────────────

def api_request(method: str, path: str, json_data=None) -> dict:
    """发送 API 请求，自动携带 Session Cookie"""
    if "session" not in st.session_state:
        st.session_state["session"] = requests.Session()

    url = f"{API_BASE}{path}"
    try:
        if method == "GET":
            resp = st.session_state["session"].get(url, params=json_data)
        elif method == "POST":
            resp = st.session_state["session"].post(url, json=json_data)
        elif method == "PUT":
            resp = st.session_state["session"].put(url, json=json_data)
        elif method == "DELETE":
            resp = st.session_state["session"].delete(url)
        else:
            return {"code": -1, "message": "Unknown method"}

        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return {"code": resp.status_code, "message": resp.text}
    except requests.exceptions.ConnectionError:
        return {"code": -1, "message": "无法连接到后端服务器，请确保后端已启动"}
    except Exception as e:
        return {"code": -1, "message": str(e)}


# ──────────────────── 页面配置 ────────────────────

st.set_page_config(page_title="OJ 在线评测系统", page_icon="⚖️", layout="wide")

st.title("⚖️ OJ 在线评测系统")

# 初始化 session state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "session" not in st.session_state:
    st.session_state["session"] = requests.Session()


# ──────────────────── 认证页面 ────────────────────

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            st.subheader("用户登录")
            login_username = st.text_input("用户名", key="login_user")
            login_password = st.text_input("密码", type="password", key="login_pass")
            if st.button("登录", type="primary"):
                resp = api_request("POST", "/auth/login", {
                    "username": login_username,
                    "password": login_password,
                })
                if resp.get("code") == 200:
                    user = resp["data"]
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = user
                    st.success(f"✅ 欢迎回来，{user['username']}！")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {resp.get('message', '登录失败')}")

        with tab2:
            st.subheader("注册新账号")
            reg_username = st.text_input("用户名", key="reg_user")
            reg_password = st.text_input("密码", type="password", key="reg_pass")
            if st.button("注册"):
                resp = api_request("POST", "/auth/register", {
                    "username": reg_username,
                    "password": reg_password,
                })
                if resp.get("code") == 201:
                    st.success("✅ 注册成功！请在左侧登录")
                else:
                    st.error(f"❌ {resp.get('message', '注册失败')}")


# ──────────────────── 学生 & 教师共用页面 ────────────────────

def show_problem_list():
    """题目列表"""
    st.subheader("📚 题目列表")
    resp = api_request("GET", "/problems")
    if resp.get("code") != 200:
        st.error(resp.get("message", "加载失败"))
        return

    items = resp.get("data", {}).get("items", [])
    if not items:
        st.info("暂无题目")
        return

    for p in items:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{p['id']} — {p['title']}**")
            with c2:
                diff_color = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                st.caption(f"{diff_color.get(p['difficulty'], '')} {p['difficulty']}")
            with c3:
                if st.button("查看详情", key=f"detail_{p['id']}"):
                    st.session_state["view_problem"] = p["id"]
                    st.session_state["page"] = "problem_detail"
                    st.rerun()


def show_problem_detail():
    """题目详情 + 代码提交"""
    problem_id = st.session_state.get("view_problem", "")
    resp = api_request("GET", f"/problems/{problem_id}")

    if st.button("← 返回题目列表"):
        st.session_state["page"] = "problems"
        st.rerun()

    if resp.get("code") != 200:
        st.error("题目加载失败")
        return

    p = resp["data"]
    st.subheader(f"📝 {p['id']} — {p['title']}")

    # 题目信息
    with st.expander("题目描述", expanded=True):
        st.markdown(p.get("description", ""))
    with st.expander("输入说明"):
        st.markdown(p.get("input_description", ""))
    with st.expander("输出说明"):
        st.markdown(p.get("output_description", ""))

    if p.get("samples"):
        st.subheader("📋 样例")
        for i, s in enumerate(p["samples"]):
            c1, c2 = st.columns(2)
            with c1:
                st.code(s["input"], language=None)
                st.caption("输入")
            with c2:
                st.code(s["output"], language=None)
                st.caption("输出")

    if p.get("constraints"):
        st.info(f"约束: {p['constraints']}")
    st.caption(f"⏱ {p.get('time_limit', 1)}s | 💾 {p.get('memory_limit', 128)}MB")

    # 代码提交区域
    st.subheader("⌨️ 提交代码")
    code = st.text_area(
        "Python 代码",
        height=200,
        placeholder="在这里输入你的 Python 代码...",
        key="code_input",
    )
    if st.button("提交评测", type="primary", disabled=not code.strip()):
        # 将字面 \n \t 转为真正换行/制表符（方便粘贴含转义字符的代码）
        code = code.replace("\\n", "\n").replace("\\t", "\t")
        resp = api_request("POST", "/submissions", {
            "problem_id": problem_id,
            "language": "python",
            "source_code": code,
        })
        if resp.get("code") == 202:
            sid = resp["data"]["submission_id"]
            st.success(f"✅ 提交成功！提交编号: {sid}")
            st.session_state["last_submission"] = sid
        else:
            st.error(f"❌ {resp.get('message', '提交失败')}")


def show_submission_result():
    """查看最近一次提交的结果"""
    sid = st.session_state.get("last_submission", "")
    if not sid:
        st.info("还没有提交过代码")
        return

    st.subheader(f"📊 提交结果 — {sid}")
    if st.button("🔄 刷新状态"):
        st.rerun()

    resp = api_request("GET", f"/submissions/{sid}")
    if resp.get("code") != 200:
        st.error("加载失败")
        return

    sub = resp["data"]
    status_colors = {
        "pending": "🟡", "running": "🔵", "finished": "🟢", "failed": "🔴"
    }
    result_colors = {
        "AC": "🟢", "WA": "🔴", "RE": "🟠", "TLE": "⏰", "SE": "💥"
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("状态", f"{status_colors.get(sub['status'], '')} {sub['status']}")
    with c2:
        st.metric("结果", f"{result_colors.get(sub.get('result', ''), '')} {sub.get('result', 'N/A')}")
    with c3:
        st.metric("得分", f"{sub.get('score', 0)} / 100")

    if sub["status"] in ("finished", "failed"):
        # 显示测试点详情
        logs_resp = api_request("GET", f"/submissions/{sid}/logs")
        if logs_resp.get("code") == 200:
            cases = logs_resp["data"].get("cases", [])
            if cases:
                st.subheader("📋 测试点详情")
                for c in cases:
                    icon = result_colors.get(c["result"], "")
                    hidden = "🔒 隐藏" if c.get("is_hidden") else ""
                    st.text(f"{icon} {c['case_id']}: {c['result']} | 耗时 {c['time_used']}s | {hidden}")
                    if c.get("message"):
                        st.caption(f"  {c['message']}")


def show_history():
    """提交历史"""
    st.subheader("📜 提交历史")
    resp = api_request("GET", "/submissions", {"page_size": 20})
    if resp.get("code") != 200:
        st.error("加载失败")
        return

    items = resp["data"].get("items", [])
    if not items:
        st.info("暂无提交记录")
        return

    for s in items:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
            with c1:
                st.markdown(f"**{s['problem_id']}**")
            with c2:
                st.caption(s.get("created_at", ""))
            with c3:
                r = s.get("result") or "—"
                st.markdown(("🟢" if r == "AC" else "🔴" if r else "⚪") + f" {r}")
            with c4:
                if st.button("详情", key=f"hist_{s['id']}"):
                    st.session_state["last_submission"] = s["id"]
                    st.session_state["page"] = "submission_result"
                    st.rerun()


# ──────────────────── 教师管理页面 ────────────────────

def show_teacher_problem_management():
    """教师题目管理（方案A）"""
    st.subheader("🛠️ 题目管理")

    tab1, tab2 = st.tabs(["题目列表", "创建题目"])

    with tab1:
        resp = api_request("GET", "/problems")
        if resp.get("code") == 200:
            items = resp["data"].get("items", [])
            for p in items:
                with st.expander(f"{p['id']} — {p['title']}", expanded=False):
                    resp_d = api_request("GET", f"/problems/{p['id']}")
                    if resp_d.get("code") == 200:
                        d = resp_d["data"]
                        st.json({
                            "id": d["id"], "title": d["title"],
                            "difficulty": d["difficulty"],
                            "time_limit": d["time_limit"],
                            "memory_limit": d["memory_limit"],
                            "tags": d.get("tags", []),
                            "test_cases": d.get("test_cases", []),
                        })
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🗑️ 删除", key=f"del_{p['id']}"):
                            r = api_request("DELETE", f"/problems/{p['id']}")
                            if r.get("code") == 200:
                                st.success("已删除")
                                st.rerun()
                            else:
                                st.error(r.get("message"))
                    with c2:
                        if st.button("✏️ 编辑", key=f"edit_{p['id']}"):
                            st.session_state["edit_problem"] = p["id"]
                            st.rerun()

        # 编辑界面
        edit_id = st.session_state.get("edit_problem")
        if edit_id:
            st.subheader(f"编辑题目: {edit_id}")
            with st.form("edit_form"):
                new_title = st.text_input("新标题")
                new_diff = st.selectbox("难度", ["easy", "medium", "hard"])
                new_time = st.number_input("时间限制(秒)", value=1.0, min_value=0.1)
                new_mem = st.number_input("内存限制(MB)", value=128, min_value=1)
                if st.form_submit_button("保存修改"):
                    r = api_request("PUT", f"/problems/{edit_id}", {
                        "title": new_title,
                        "difficulty": new_diff,
                        "time_limit": new_time,
                        "memory_limit": new_mem,
                    })
                    if r.get("code") == 200:
                        st.success("修改成功")
                        st.session_state["edit_problem"] = None
                        st.rerun()
                    else:
                        st.error(r.get("message"))

    with tab2:
        st.markdown("创建新题目（JSON 格式，包含完整 test_cases）")
        problem_json = st.text_area("题目 JSON", height=400, key="create_json",
            placeholder='{"id":"P1001","title":"A+B","description":"...","input_description":"...","output_description":"...","samples":[{"input":"1 2\\n","output":"3\\n"}],"time_limit":1.0,"memory_limit":128,"difficulty":"easy","tags":[],"test_cases":[{"case_id":"c1","input":"1 2\\n","output":"3\\n","score":100,"is_hidden":false}]}')
        if st.button("创建题目", type="primary"):
            try:
                data = json.loads(problem_json)
                r = api_request("POST", "/problems", data)
                if r.get("code") == 201:
                    st.success(f"✅ 题目 {data['id']} 创建成功！")
                else:
                    st.error(f"❌ {r.get('message')}")
            except json.JSONDecodeError:
                st.error("❌ JSON 格式错误")


def show_all_submissions():
    """教师查看所有提交"""
    st.subheader("📊 所有提交")
    resp = api_request("GET", "/submissions", {"page_size": 50})
    if resp.get("code") != 200:
        st.error("加载失败")
        return
    items = resp["data"].get("items", [])
    for s in items:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"**{s['id'][:8]}...**")
            with c2: st.caption(f"用户: {s['user_id'][:8]}...")
            with c3: st.caption(f"题: {s['problem_id']}")
            with c4: st.markdown(("🟢" if s.get("result") == "AC" else "🔴") + f" {s.get('result','?')}")


def show_admin_user_management():
    """管理员：用户列表、切换角色、启用/禁用"""
    st.subheader("👥 用户管理")
    resp = api_request("GET", "/users", {"page_size": 50})
    if resp.get("code") != 200:
        st.error(f"❌ {resp.get('message', '加载失败')}")
        return

    current_user_id = st.session_state["user"]["id"]

    for u in resp["data"].get("items", []):
        is_self = u["id"] == current_user_id
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                icon = "✅" if u["is_active"] else "🚫"
                self_tag = " 👈 当前用户" if is_self else ""
                st.markdown(f"{icon} **{u['username']}**{self_tag} `{u['id'][:8]}...`")
            with c2:
                role_tag = " (管理员)" if u["role"] == "admin" else ""
                st.caption(f"角色: {u['role']}{role_tag}")

            if is_self:
                with c3: st.caption("—")
                with c4: st.caption("—")
            else:
                with c3:
                    if st.button("🔄 切换角色", key=f"role_{u['id']}"):
                        new_role = "teacher" if u["role"] == "student" else "student"
                        r = api_request("PUT", f"/users/{u['id']}", {"role": new_role})
                        if r.get("code") == 200: st.success(f"✅ {u['username']} → {new_role}"); st.rerun()
                        else: st.error(r.get("message"))
                with c4:
                    if u["is_active"]:
                        if st.button("🚫 禁用", key=f"dis_{u['id']}"):
                            r = api_request("PUT", f"/users/{u['id']}", {"is_active": False})
                            if r.get("code") == 200: st.rerun()
                            else: st.error(r.get("message"))
                    else:
                        if st.button("✅ 启用", key=f"ena_{u['id']}"):
                            r = api_request("PUT", f"/users/{u['id']}", {"is_active": True})
                            if r.get("code") == 200: st.rerun()
                            else: st.error(r.get("message"))


def show_admin_backup_management():
    """管理员：备份创建、查看、恢复"""
    st.subheader("💾 数据备份与恢复")
    tab1, tab2 = st.tabs(["创建备份", "备份列表"])

    with tab1:
        if st.button("📦 创建备份", type="primary"):
            r = api_request("POST", "/admin/backups")
            if r.get("code") == 201: st.success(f"✅ 备份: {r['data']['backup_id']}")
            else: st.error(r.get("message"))

    with tab2:
        resp = api_request("GET", "/admin/backups")
        if resp.get("code") != 200: st.error("加载失败"); return
        for b in resp.get("data", []):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{b['backup_id']}**")
                    st.caption(f"时间: {b.get('created_at','')}")
                with c2:
                    if st.button("🔄 恢复", key=f"r_{b['backup_id']}"):
                        r = api_request("POST", f"/admin/backups/{b['backup_id']}/restore")
                        st.success("✅ 已恢复" if r.get("code") == 200 else f"❌ {r.get('message')}")


# ──────────────────── 主入口 ────────────────────

def main():
    # 未登录 → 显示登录/注册页
    if not st.session_state["logged_in"]:
        show_login_page()
        return

    # 已登录 → 侧边栏导航
    user = st.session_state["user"]
    role = user.get("role", "student")

    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.caption(f"角色: {role}")

        if st.button("📚 题目列表"):
            st.session_state["page"] = "problems"
        if st.button("📜 提交历史"):
            st.session_state["page"] = "history"
        if st.button("📊 最近结果"):
            st.session_state["page"] = "submission_result"

        if role in ("teacher", "admin"):
            st.divider()
            st.markdown("### 🛠️ 教师工具")
            if st.button("题目管理"):
                st.session_state["page"] = "teacher_manage"
            if st.button("📊 所有提交"):
                st.session_state["page"] = "all_submissions"

        if role == "admin":
            st.divider()
            st.markdown("### 👑 管理员工具")
            if st.button("👥 用户管理"):
                st.session_state["page"] = "user_manage"
            if st.button("💾 备份恢复"):
                st.session_state["page"] = "backup_manage"

        st.divider()
        if st.button("🚪 登出"):
            api_request("POST", "/auth/logout")
            st.session_state["logged_in"] = False
            st.session_state["user"] = None
            st.session_state["page"] = "login"
            st.session_state["session"] = requests.Session()
            st.rerun()

    # 页面路由
    page = st.session_state.get("page", "problems")

    if page == "problems":
        show_problem_list()
    elif page == "problem_detail":
        show_problem_detail()
    elif page == "submission_result":
        show_submission_result()
    elif page == "history":
        show_history()
    elif page == "teacher_manage":
        show_teacher_problem_management()
    elif page == "all_submissions":
        show_all_submissions()
    elif page == "user_manage":
        show_admin_user_management()
    elif page == "backup_manage":
        show_admin_backup_management()


if __name__ == "__main__":
    main()
