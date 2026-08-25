"""Streamlit 페이지가 공유하는 backend 연결 리소스."""

import streamlit as st

from web.backend import MySQLDB


@st.cache_resource
def get_db() -> MySQLDB:
    """프로젝트 환경변수로 만든 MySQL 연결을 세션 간 재사용한다."""
    return MySQLDB.from_env()
