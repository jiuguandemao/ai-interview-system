import os
import time

import requests
import streamlit as st


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
st.set_page_config(page_title="AI-Interview", layout="wide")
st.title("AI-Interview 智能模拟面试")


def headers() -> dict[str, str]:
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def show_error(response: requests.Response) -> None:
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    st.error(f"请求失败（{response.status_code}）：{detail}")


def wait_job(job_id: str, timeout: int = 180) -> dict:
    progress = st.progress(0, text="任务已提交")
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{API_BASE}/jobs/{job_id}", headers=headers(), timeout=15)
        if not response.ok:
            show_error(response)
            return {}
        job = response.json()
        progress.progress(job["progress"], text=f"{job['status']} - {job['progress']}%")
        if job["status"] == "success":
            return job
        if job["status"] == "failed":
            st.error(job.get("error_message") or "后台任务失败")
            return job
        time.sleep(1)
    st.warning("等待超时，任务仍可能在后台运行，请稍后刷新")
    return {}


with st.sidebar:
    st.header("账号")
    mode = st.segmented_control("操作", ["登录", "注册"], default="登录")
    username = st.text_input("用户名或邮箱")
    password = st.text_input("密码", type="password")
    if mode == "注册":
        email = st.text_input("邮箱")
        if st.button("创建账号", use_container_width=True):
            response = requests.post(
                f"{API_BASE}/auth/register",
                json={"username": username, "email": email, "password": password},
                timeout=15,
            )
            st.success("注册成功，请切换到登录") if response.ok else show_error(response)
    elif st.button("登录", use_container_width=True):
        response = requests.post(
            f"{API_BASE}/auth/token",
            data={"username": username, "password": password},
            timeout=15,
        )
        if response.ok:
            st.session_state.token = response.json()["access_token"]
            st.success("已登录")
        else:
            show_error(response)


if not st.session_state.get("token"):
    st.info("先在左侧注册并登录，然后上传简历和岗位 JD。")
    st.stop()

upload_tab, interview_tab, report_tab = st.tabs(["准备材料", "模拟面试", "结果报告"])

with upload_tab:
    left, right = st.columns(2)
    with left:
        st.subheader("上传简历")
        resume_file = st.file_uploader("PDF、DOCX、TXT 或 Markdown", type=["pdf", "docx", "txt", "md"])
        if st.button("解析简历", disabled=resume_file is None):
            response = requests.post(
                f"{API_BASE}/resumes",
                headers=headers(),
                files={"file": (resume_file.name, resume_file.getvalue())},
                timeout=30,
            )
            if response.ok:
                result = response.json()
                st.session_state.resume_id = str(result["resume_id"])
                wait_job(str(result["job_id"]))
            else:
                show_error(response)
    with right:
        st.subheader("录入岗位 JD")
        jd_title = st.text_input("岗位名称", value="AI 应用开发工程师")
        jd_text = st.text_area("岗位职责与要求", height=220)
        jd_file = st.file_uploader("也可以上传 JD 文件", type=["pdf", "docx", "txt", "md"])
        if st.button("解析 JD", disabled=not jd_text.strip() and jd_file is None):
            files = {"file": (jd_file.name, jd_file.getvalue())} if jd_file else None
            response = requests.post(
                f"{API_BASE}/job-descriptions",
                headers=headers(),
                data={"title": jd_title, "text": jd_text},
                files=files,
                timeout=30,
            )
            if response.ok:
                result = response.json()
                st.session_state.jd_id = str(result["jd_id"])
                wait_job(str(result["job_id"]))
            else:
                show_error(response)

with interview_tab:
    st.subheader("开始和回答")
    resume_id = st.text_input("简历 ID", value=st.session_state.get("resume_id", ""))
    jd_id = st.text_input("JD ID", value=st.session_state.get("jd_id", ""))
    max_questions = st.number_input("问答轮数", min_value=1, max_value=20, value=5)
    if st.button("创建模拟面试"):
        response = requests.post(
            f"{API_BASE}/interviews",
            headers=headers(),
            json={"resume_id": resume_id, "jd_id": jd_id, "max_questions": max_questions},
            timeout=30,
        )
        if response.ok:
            result = response.json()
            st.session_state.session_id = str(result["session_id"])
            wait_job(str(result["job_id"]))
        else:
            show_error(response)

    session_id = st.text_input("面试会话 ID", value=st.session_state.get("session_id", ""))
    if session_id and st.button("刷新当前问题"):
        response = requests.get(f"{API_BASE}/interviews/{session_id}", headers=headers(), timeout=15)
        if response.ok:
            st.session_state.current_question = response.json().get("current_question")
            st.json(response.json())
        else:
            show_error(response)
    st.info(st.session_state.get("current_question") or "创建面试后刷新当前问题")
    answer = st.text_area("你的回答", height=180)
    if st.button("提交回答", disabled=not session_id or not answer.strip()):
        response = requests.post(
            f"{API_BASE}/interviews/{session_id}/answers",
            headers=headers(),
            json={"answer": answer},
            timeout=30,
        )
        if response.ok:
            result = wait_job(str(response.json()["job_id"]))
            st.json(result.get("result_json", result))
        else:
            show_error(response)

with report_tab:
    report_session_id = st.text_input("报告对应的会话 ID", value=st.session_state.get("session_id", ""))
    if st.button("查看报告", disabled=not report_session_id):
        response = requests.get(
            f"{API_BASE}/interviews/{report_session_id}/report", headers=headers(), timeout=15
        )
        st.json(response.json()) if response.ok else show_error(response)
