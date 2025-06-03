import streamlit as st
import requests
import json
import os
import pandas as pd
from sseclient import SSEClient
from src.core.database import verify_user, create_session, verify_session, delete_session, create_user
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 설정 가져오기
CHAT_API_URL = os.getenv('CHAT_API_URL', 'http://localhost:8000/api/v1/chat')
EMPLOYEE_SEARCH_API = os.getenv('EMPLOYEE_SEARCH_API', 'http://your-api-url/search')

# 페이지 설정
st.set_page_config(
    page_title=os.getenv('PROJECT_NAME', 'Gemma Chat'),
    page_icon="🤖",
    layout="wide"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "show_user_management" not in st.session_state:
    st.session_state.show_user_management = False
if "search_query" not in st.session_state:
    st.session_state.search_query = ""
if "selected_result" not in st.session_state:
    st.session_state.selected_result = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []

# 토큰으로 로그인 상태 확인
if st.session_state.auth_token:
    user = verify_session(st.session_state.auth_token)
    if not user:
        st.session_state.auth_token = None
        st.rerun()

# 로그인 상태가 아닐 때 로그인 폼 표시
if not st.session_state.auth_token:
    st.title("🔐 Login")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if user := verify_user(username, password):
                token = create_session(user['id'])
                st.session_state.auth_token = token
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    # 로그인 전에는 여기서 중단
    st.stop()

# 현재 사용자 정보 가져오기
current_user = verify_session(st.session_state.auth_token)

# 로그인 된 경우 채팅 인터페이스 표시
# 사이드바 설정
# 사이드바 설정 (app.py의 사이드바 부분을 이것으로 교체)
with st.sidebar:
    # 사용자 이름과 로그아웃 버튼을 같은 행에 배치
    col_user, col_logout = st.columns([2, 1])
    
    with col_user:
        st.markdown(f"### 👤 {current_user['username']}")
    
    with col_logout:
        st.markdown("<br>", unsafe_allow_html=True)  # 약간의 수직 정렬을 위한 공간
        if st.button("🚪", help="로그아웃", key="logout_btn", use_container_width=True):
            if st.session_state.auth_token:
                delete_session(st.session_state.auth_token)
            st.session_state.auth_token = None
            st.session_state.messages = []
            st.session_state.show_user_management = False
            st.rerun()
    
    # 관리자인 경우 사용자 관리 토글 버튼 표시
    if current_user['username'] == 'admin':
        if st.button("👥 사용자 관리" if not st.session_state.show_user_management else "💬 채팅으로 돌아가기", 
                    use_container_width=True, key="user_mgmt_toggle"):
            st.session_state.show_user_management = not st.session_state.show_user_management
            st.rerun()
    
    if not st.session_state.show_user_management:
        st.title("⚙️ 설정")
        api_url = st.text_input(
            "API URL",
            value=CHAT_API_URL,
            help="Chat API의 엔드포인트 URL"
        )
        use_streaming = st.checkbox("스트리밍 사용", value=True)
        
        # 직원 검색 섹션
        st.title("🔍 직원 검색")
        
        # 검색 타입 선택
        search_type = st.radio(
            "검색 유형",
            ["이름으로 검색", "직책으로 검색"],
            key="search_type"
        )
        
        # 검색 타입이 변경되면 관련 상태 초기화
        if "previous_search_type" not in st.session_state:
            st.session_state.previous_search_type = search_type

        if st.session_state.previous_search_type != search_type:
            keys_to_clear = ['search_results', 'selected_result', 'search_query', 'search_input']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success(f"🔄 검색 타입이 '{search_type}'으로 변경되어 이전 검색 결과가 초기화되었습니다.")
            st.session_state.previous_search_type = search_type
        
        # 검색 결과 표시 섹션
        st.divider()
        st.markdown("#### 📊 현재 선택된 정보")
        
        # 이름 표시
        st.markdown("**👤 이름**")
        if search_type == "이름으로 검색":
            name_value = st.session_state.get("search_query", "")
        else:
            name_value = st.session_state.get("selected_result", "")
        
        if name_value and isinstance(name_value, str) and name_value.strip():
            st.code(name_value, language=None)
        else:
            st.text("-")
        
        # 직책 표시
        st.markdown("**💼 직책**")
        if search_type == "이름으로 검색":
            position_value = st.session_state.get("selected_result", "")
        else:
            position_value = st.session_state.get("search_query", "")
        
        if position_value and isinstance(position_value, str) and position_value.strip():
            st.code(position_value, language=None)
        else:
            st.text("-")

        st.divider()
        
        # 검색 입력
        search_query = st.text_input(
            "검색어",
            placeholder="이름" if search_type == "이름으로 검색" else "직책",
            key="search_input"
        )
        
        # 검색 버튼 (전체 너비 사용)
        search_clicked = st.button("🔍 검색", use_container_width=True, type="primary")
        
        # 초기화 버튼 (전체 너비 사용하여 일관된 모양 유지)
        if st.button("🗑️ 초기화", use_container_width=True):
            keys_to_clear = ['search_results', 'selected_result', 'search_query', 'search_input']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("모든 검색 결과가 초기화되었습니다!")
            st.rerun()

        # 검색 버튼 처리
        if search_clicked and search_query:
            st.session_state.search_query = search_query
            
            try:
                with st.spinner("검색 중..."):
                    response = requests.get(
                        EMPLOYEE_SEARCH_API,
                        params={
                            'type': 'name' if search_type == "이름으로 검색" else 'position',
                            'query': search_query
                        },
                        headers={'Authorization': f'Bearer {st.session_state.auth_token}'}
                    )
                    
                    if response.status_code == 200:
                        results_data = response.json().get("response", "[]")
                        
                        if isinstance(results_data, str):
                            try:
                                results = json.loads(results_data.replace("'", '"'))
                            except json.JSONDecodeError:
                                results = []
                        elif isinstance(results_data, list):
                            results = results_data
                        else:
                            results = []
                        
                        st.session_state.search_results = results
                        
                        if results:
                            st.success(f"✅ {len(results)}개 결과 발견")
                        else:
                            st.info("검색 결과가 없습니다.")
                            st.session_state.search_results = []
                            if 'selected_result' in st.session_state:
                                del st.session_state.selected_result
                    else:
                        st.error(f"API 요청 실패: {response.status_code}")
                
            except Exception as e:
                st.error(f"검색 중 오류: {str(e)}")

        elif search_clicked:
            st.warning("검색어를 입력해주세요.")

        # 검색 결과가 있는 경우 selectbox 표시
        if st.session_state.get("search_results"):
            results = st.session_state.search_results
            
            if results:
                result_options = []
                for result in results:
                    if isinstance(result, list) and len(result) > 0:
                        result_options.append(result[0])
                    elif isinstance(result, str):
                        result_options.append(result)
                
                if result_options:
                    st.markdown("---")
                    st.markdown("**📋 검색 결과 선택**")
                    
                    current_index = 0
                    if st.session_state.get("selected_result") in result_options:
                        current_index = result_options.index(st.session_state.selected_result)
                    
                    # selectbox
                    temp_selected = st.selectbox(
                        "결과 선택:",
                        options=result_options,
                        index=current_index,
                        key="search_result_selectbox"
                    )
                    
                    # 반영 버튼 (전체 너비 사용)
                    button_disabled = temp_selected == st.session_state.get("selected_result")
                    if st.button(
                        "✅ 반영", 
                        use_container_width=True, 
                        type="primary",
                        disabled=button_disabled
                    ):
                        st.session_state.selected_result = temp_selected
                        st.success(f"✅ '{temp_selected}' 반영됨!")
                        st.rerun()
                    
                    # 현재 상태 표시
                    current_selected = st.session_state.get("selected_result")
                    if current_selected:
                        if temp_selected != current_selected:
                            st.info(f"🔄 선택: {temp_selected}")
                        else:
                            st.success(f"✅ 적용됨: {current_selected}")
                    else:
                        st.info(f"🔄 선택: {temp_selected}")
    
    # 대화 초기화 버튼
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 메인 인터페이스
if st.session_state.show_user_management and current_user['username'] == 'admin':
    st.title("👥 사용자 관리")
    
    # 탭 생성
    user_tab, search_tab = st.tabs(["사용자 생성", "직원 검색"])
    
    # 사용자 생성 탭
    with user_tab:
        with st.form("create_user"):
            st.subheader("새 사용자 생성")
            new_username = st.text_input("사용자명")
            new_password = st.text_input("비밀번호", type="password")
            new_password_confirm = st.text_input("비밀번호 확인", type="password")
            
            submitted = st.form_submit_button("사용자 생성")
            if submitted:
                if not new_username or not new_password:
                    st.error("사용자명과 비밀번호를 모두 입력해주세요.")
                elif new_password != new_password_confirm:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif create_user(new_username, new_password):
                    st.success(f"사용자 '{new_username}'가 생성되었습니다.")
                else:
                    st.error("이미 존재하는 사용자명입니다.")
    
    # 직원 검색 탭
    with search_tab:
        st.subheader("직원 검색")
        
        # 검색 타입 선택
        search_type = st.radio("검색 유형", ["이름으로 검색", "직책으로 검색"])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            # 검색 입력
            search_query = st.text_input(
                "검색어",
                placeholder="이름" if search_type == "이름으로 검색" else "직책"
            )
        with col2:
            search_button = st.button("검색", use_container_width=True)
        
        if search_button and search_query:
            try:
                with st.spinner("검색 중..."):
                    # API 요청
                    response = requests.get(
                        EMPLOYEE_SEARCH_API,
                        params={
                            'type': 'name' if search_type == "이름으로 검색" else 'position',
                            'query': search_query
                        },
                        headers={'Authorization': f'Bearer {st.session_state.auth_token}'}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        
                        # 결과 표시
                        if results:
                            # 결과를 데이터프레임으로 변환
                            df = pd.DataFrame(results)
                            
                            # 컬럼 순서와 이름 조정
                            if search_type == "이름으로 검색":
                                df = df.reindex(columns=['name', 'position', 'department'])
                                df.columns = ['이름', '직책', '부서']
                            else:
                                df = df.reindex(columns=['position', 'name', 'department'])
                                df.columns = ['직책', '이름', '부서']
                            
                            # 스타일이 적용된 데이터프레임 표시
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                height=400
                            )
                            
                            # 검색 결과 통계
                            st.info(f"총 {len(results)}개의 결과를 찾았습니다.")
                        else:
                            st.info("검색 결과가 없습니다.")
                    else:
                        st.error(f"API 요청 실패: {response.status_code}")
                
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
        elif search_button:
            st.warning("검색어를 입력해주세요.")

else:
    st.title("🤖 Gemma Chat")
    
    # 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 채팅 입력
    if prompt := st.chat_input("메시지를 입력하세요..."):
        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # API 요청 헤더에 인증 토큰 추가
        headers = {
            'Accept': 'text/event-stream' if use_streaming else 'application/json',
            'Authorization': f'Bearer {st.session_state.auth_token}'
        }
        
        # AI 응답
        with st.chat_message("assistant"):
            if use_streaming:
                message_placeholder = st.empty()
                full_response = ""
                try:
                    # SSE 스트리밍 요청
                    response = requests.post(
                        api_url,
                        json={
                            "message": prompt,
                            "stream": True
                        },
                        stream=True,
                        headers=headers,
                        verify=False
                    )
                    client = SSEClient(response)
                    
                    for event in client.events():
                        try:
                            chunk = json.loads(event.data)
                            if "error" in chunk:
                                st.error(chunk["error"])
                                break
                            if chunk.get("done", False):
                                break
                            
                            full_response += chunk["text"]
                            message_placeholder.markdown(full_response + "▌")
                        except json.JSONDecodeError:
                            continue
                    
                    message_placeholder.markdown(full_response)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    full_response = "오류가 발생했습니다."
            else:
                try:
                    # 일반 요청
                    response = requests.post(
                        api_url,
                        json={
                            "message": prompt,
                            "stream": False
                        },
                        headers=headers,
                        verify=False
                    )
                    response_data = response.json()
                    full_response = response_data.get("response", "응답을 받지 못했습니다.")
                    st.markdown(full_response)
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    full_response = "오류가 발생했습니다."
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# 푸터
st.markdown("---")
st.markdown("Powered by Gemma & FastAPI")
