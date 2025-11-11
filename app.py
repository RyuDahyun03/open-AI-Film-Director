import streamlit as st
from openai import OpenAI
import cv2  # (V2) 비디오 프레임 처리
import base64 # (V2) 이미지를 API로 보내기 위해
import tempfile # (V2) 업로드된 파일을 임시 저장
import os       # (V2) 임시 파일 관리

# -----------------------
# 페이지 기본 설정
# -----------------------
st.set_page_config(page_title="🎬 AI 비디오 감독 어시스턴스", layout="wide")
st.title("🎬 AI 비디오 감독")
st.write("원하는 작업을 탭에서 선택하세요")

# -----------------------
# (공통) 사이드바: API 키 (Secrets에서 불러오기)
# -----------------------
st.sidebar.header("🔑 (공통) API 설정")

# Streamlit Cloud에 배포된 버전인지 확인
if 'OPENAI_API_KEY' in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    st.sidebar.success("API Key가 안전하게 로드되었습니다.")
else:
    # 로컬 테스트용 (선택 사항)
    st.sidebar.warning("Streamlit Cloud Secrets에 'OPENAI_API_KEY'를 설정해주세요.")
    # 로컬에서만 임시로 키를 입력받고 싶다면, 이전 코드를 여기에 넣을 수 있습니다.
    api_key = st.sidebar.text_input(
        "(로컬 테스트용) OpenAI API Key를 입력하세요:",
        type="password",
        placeholder="sk-xxxxxxxxxxxxxxxx",
    )

# -----------------------
# (공통) V1, V2에서 사용할 프롬프트와 헬퍼 함수 정의
# -----------------------

# (V1) 버전 1에서 사용할 역할 정의
V1_ROLES = {
    "🎥 Video Director": 
    "You are a professional film director. Always analyze ideas in terms of visual storytelling — use camera movement, lighting, framing, and emotional tone to explain your thoughts. Describe concepts as if you are planning a film scene.",
    
}

# (V2) 버전 2에서 사용할 고정 시스템 프롬프트
V2_SYSTEM_PROMPT = """
You are a professional film director and shot analyzer.
Your task is to analyze a series of video frames provided by the user.
Based on these frames, generate a detailed "prompt" that could be used by an AI video generator to create this exact scene.
Your analysis must include: Subject, Action, Scene Description, Cinematography (angle, movement, lighting), and Style.
Combine all of this into a concise, powerful prompt for an AI video generator.
"""

# (V2) 버전 2에서 사용할 헬퍼 함수
def process_video(video_path, seconds_per_frame, max_frames_to_send):
    """비디오 파일에서 프레임을 추출하고 Base64로 인코딩합니다."""
    base64_frames = []
    vid_cap = cv2.VideoCapture(video_path)
    
    fps = vid_cap.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 30
    
    frame_interval = int(fps * seconds_per_frame)
    if frame_interval == 0: frame_interval = 1
            
    frame_count = 0
    
    while vid_cap.isOpened():
        ret, frame = vid_cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            _, buffer = cv2.imencode(".jpg", frame)
            base64_frames.append(base64.b64encode(buffer).decode("utf-8"))
        
        frame_count += 1
        
        if len(base64_frames) >= max_frames_to_send:
            break
            
    vid_cap.release()
    return base64_frames

# -----------------------
# (공통) 메인 페이지 - 탭 생성
# -----------------------
tab1, tab2 = st.tabs(["🎬 버전 1: 프롬프트 디벨로퍼", "🎞️ 버전 2: 영상 프롬프트 분석기"])

# [ 탭 1 ] 버전 1: 프롬프트 디벨로퍼 (비디오 감독 전용)
# -----------------------
with tab1:
    st.header("버전 1: 아이디어를 영상으로 발전시키기")
    
    # --- (수정됨) V1 역할을 '비디오 감독'으로 고정 ---
    # V1_ROLES 딕셔너리 대신, 비디오 감독 프롬프트를 직접 정의합니다.
    V1_SYSTEM_PROMPT = """
    You are a professional film director. Always analyze ideas in terms of visual storytelling — use camera movement, lighting, framing, and emotional tone to explain your thoughts. Describe concepts as if you are planning a film scene.
    """
    st.info(f"현재 역할: 🎥 Video Director\n\n{V1_SYSTEM_PROMPT}")

    # V1 텍스트 입력
    user_input_v1 = st.text_area(
        "💬 발전시키고 싶은 아이디어를 입력하세요:",
        height=100,
        placeholder="예: 비 오는 날 창밖을 보는 슬픈 남자",
        key="v1_text_area"
    )
    
    # V1 응답 생성 버튼
    if st.button("프롬프트 디벨롭하기", key="v1_button"):
        if not api_key:
            st.warning("⚠️ 사이드바에 OpenAI API 키를 입력해주세요.")
        elif not user_input_v1:
            st.warning("⚠️ 발전시킬 아이디어를 먼저 입력해주세요.")
        else:
            try:
                client = OpenAI(api_key=api_key)
                with st.spinner("AI 감독이 씬을 구상 중입니다..."):
                    response = client.chat.completions.create(
                        model="gpt-4o-mini", # V1은 mini로도 충분
                        messages=[
                            # (수정됨) 'role_description' 대신 직접 정의한 프롬프트를 사용
                            {"role": "system", "content": V1_SYSTEM_PROMPT},
                            {"role": "user", "content": user_input_v1}
                        ]
                    )
                    answer = response.choices[0].message.content
                    
                    # (수정됨) 역할 이름을 "Video Director"로 고정
                    st.success("🎬 Video Director의 제안:")
                    st.write(answer)
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# -----------------------
# [ 탭 2 ] 버전 2: 영상 프롬프트 분석기
# -----------------------
with tab2:
    st.header("버전 2: 비디오를 분석하여 프롬프트 생성하기")
    st.info(f"AI 분석가 역할:\n{V2_SYSTEM_PROMPT}")

    # V2 파일 업로더
    uploaded_file = st.file_uploader(
        "분석할 비디오 파일을 업로드하세요 (mp4, mov, avi):",
        type=["mp4", "mov", "avi"],
        key="v2_file_uploader"
    )

    # V2 분석 옵션
    st.subheader("분석 옵션")
    col1, col2 = st.columns(2)
    with col1:
        frame_sampling_rate = st.slider("프레임 샘플링 간격 (초)", 0.5, 5.0, 1.0, 0.5,
                                        help="몇 초에 한 번씩 스크린샷(프레임)을 찍어 AI에게 보낼지 결정합니다.",
                                        key="v2_slider")
    with col2:
        max_frames = st.number_input("전송할 최대 프레임 수", 5, 20, 10,
                                    help="AI에게 한 번에 보낼 최대 프레임 수입니다.",
                                    key="v2_number_input")

    # V2 응답 생성 버튼
    if st.button("비디오 분석 및 프롬프트 생성", key="v2_button"):
        if not api_key:
            st.warning("⚠️ 사이드바에 OpenAI API 키를 입력해주세요.")
        elif uploaded_file is None:
            st.warning("⚠️ 비디오 파일을 먼저 업로드해주세요.")
        else:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tfile:
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name
                
                with st.spinner(f"비디오 처리 중... (최대 {max_frames} 프레임 샘플링)"):
                    base64_frames = process_video(video_path, frame_sampling_rate, max_frames)
                    
                if not base64_frames:
                    st.error("비디오 파일을 처리할 수 없습니다.")
                else:
                    st.success(f"{len(base64_frames)}개의 프레임을 추출했습니다. AI에 분석을 요청합니다...")
                    
                    # (선택사항) 프레임 미리보기
                    # st.write("AI에 전송된 샘플 프레임:")
                    # cols = st.columns(len(base64_frames))
                    # for i, frame_data in enumerate(base64_frames):
                    #     with cols[i]:
                    #         st.image(f"data:image/jpeg;base64,{frame_data}", use_column_width=True)

                    messages = [
                        {"role": "system", "content": V2_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "이 비디오 프레임들을 순서대로 분석하고, 이 씬을 생성하기 위한 상세한 프롬프트를 작성해 주세요."},
                                *[
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
                                    } for frame in base64_frames
                                ]
                            ]
                        }
                    ]
                    
                    client = OpenAI(api_key=api_key)
                    with st.spinner("AI 감독이 영상을 분석 중입니다..."):
                        response = client.chat.completions.create(
                            model="gpt-4o", # V2는 gpt-4o 권장
                            messages=messages,
                            max_tokens=1000 
                        )
                        answer = response.choices[0].message.content
                        st.subheader("🎬 AI가 생성한 프롬프트")
                        st.write(answer)

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
            finally:
                if 'video_path' in locals() and os.path.exists(video_path):
                    os.remove(video_path)

# -----------------------
# (공통) 푸터
# -----------------------
st.markdown("---")
st.caption("Built for 'Art & Advanced Big Data' • Prof. Jahwan Koo (SKKU)")
