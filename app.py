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
with st.sidebar:
    st.title(f"👤 {current_user['username']}")
    
    # 관리자인 경우 사용자 관리 토글 버튼 표시
    if current_user['username'] == 'admin':
        if st.button("👥 사용자 관리" if not st.session_state.show_user_management else "💬 채팅으로 돌아가기"):
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
            key="search_type"  # 세션 상태에 자동으로 저장됨
        )
        
        # 검색 결과 표시 섹션
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 이름")
            name_value = st.session_state.search_query if search_type == "이름으로 검색" else st.session_state.selected_result
            if isinstance(name_value, str) and name_value.strip():
                st.code(name_value)
            else:
                st.text("-")
            
        with col2:
            st.markdown("#### 직책")
            position_value = st.session_state.selected_result if search_type == "이름으로 검색" else st.session_state.search_query
            if isinstance(position_value, str) and position_value.strip():
                st.code(position_value)
            else:
                st.text("-")
        
        st.divider()
        search_query = st.text_input(
            "검색어",
            placeholder="이름" if search_type == "이름으로 검색" else "직책"
        )
        
        if st.button("검색", use_container_width=True) and search_query:
            # 검색어를 세션 상태에 저장
            st.session_state.search_query = search_query
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
                        # response에서 결과 가져오기
                        results_data = response.json().get("response", "[]")
                        
                        # 결과 타입에 따른 처리
                        if isinstance(results_data, str):
                            try:
                                # 문자열을 리스트로 변환
                                results = json.loads(results_data.replace("'", '"'))
                            except json.JSONDecodeError:
                                results = []
                        elif isinstance(results_data, list):
                            # 이미 리스트인 경우 그대로 사용
                            results = results_data
                        else:
                            # 다른 타입인 경우 빈 리스트로 처리
                            results = []
                        
                        # 결과 표시
                        if results:
                            # 검색 결과 통계
                            st.info(f"총 {len(results)}개의 결과를 찾았습니다.")
                            
                            # 결과를 세션 상태에 저장
                            if 'search_results' not in st.session_state:
                                st.session_state.search_results = results
                            if 'selected_result' not in st.session_state:
                                st.session_state.selected_result = None

                            # 검색 결과 표시
                            if results:
                                # 결과에서 실제 값만 추출 (리스트 내부의 문자열)
                                result_options = []
                                for result in results:
                                    if isinstance(result, list) and len(result) > 0:
                                        result_options.append(result[0])
                                    elif isinstance(result, str):
                                        result_options.append(result)
                                
                                # selectbox 표시
                                selected_index = 0
                                if result_options and st.session_state.selected_result in result_options:
                                    selected_index = result_options.index(st.session_state.selected_result)
                                
                                selected_result = st.selectbox(
                                    "검색 결과",
                                    options=result_options,
                                    index=selected_index,
                                    key="search_result_select"
                                )
                                
                                # 선택된 결과 저장
                                if selected_result is not None:
                                    st.session_state.selected_result = result_options[selected_result]
                                    # 결과 표시를 위해 즉시 리렌더링
                                    st.rerun()
                        else:
                            st.info("검색 결과가 없습니다.")
                    else:
                        st.error(f"API 요청 실패: {response.status_code}")
                
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
    
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.rerun()
    if st.button("로그아웃"):
        if st.session_state.auth_token:
            delete_session(st.session_state.auth_token)
        st.session_state.auth_token = None
        st.session_state.messages = []
        st.session_state.show_user_management = False
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
