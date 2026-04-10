import streamlit as st
import pandas as pd
import os
import io
import zipfile
from datetime import datetime
from typing import List, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

st.set_page_config(page_title="인증서 시스템", layout="centered")

# --- 경로 및 설정 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
STAMP_PATH = os.path.join(ASSETS_DIR, "stamp.png")

def resolve_path(*candidates):
    for path in candidates:
        if path and os.path.exists(path): return path
    return None

def setup_fonts():
    reg = resolve_path(os.path.join(ASSETS_DIR, "NanumGothic.ttf"), "/mnt/data/NanumGothic.ttf")
    bold = resolve_path(os.path.join(ASSETS_DIR, "NanumGothicBold.ttf"), "/mnt/data/NanumGothicBold.ttf")
    if not reg or not bold:
        st.error("폰트 파일을 찾을 수 없습니다.")
        st.stop()
    pdfmetrics.registerFont(TTFont("Nanum", reg))
    pdfmetrics.registerFont(TTFont("Nanum-Bold", bold))
    return "Nanum", "Nanum-Bold"

PDF_FONT, PDF_FONT_BOLD = setup_fonts()

# --- 데이터 로드 ---
if not os.path.exists(CSV_PATH):
    st.error("CSV 파일을 찾을 수 없습니다.")
    st.stop()

df = pd.read_csv(CSV_PATH)
if "cert_name" in df.columns:
    df["cert_name"] = df["cert_name"].str.strip()

# --- 공통 함수 ---
def draw_wrapped_centered_text(c, text, center_x, start_y, max_width, font_name, font_size, line_gap=14):
    c.setFont(font_name, font_size)
    words = str(text).split(" ")
    lines, current = [], ""
    for word in words:
        test = word if current == "" else f"{current} {word}"
        if stringWidth(test, font_name, font_size) <= max_width: current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    y_offset = start_y + ((len(lines) - 1) * line_gap / 2)
    for i, line in enumerate(lines):
        c.drawCentredString(center_x, y_offset - (i * line_gap), line)

def get_template_lines(product_name, t_type):
    templates = {
        "allergen": ("알레르기유발물질 확인서", ["당사는 아래 제품에 대하여 원재료 및 제조공정 검토 결과를 바탕으로", "알레르기유발물질 관리사항을 확인하였음을 증명합니다.", "", f"제품명: {product_name}"]),
        "plant": ("식물성 원재료 확인서", ["당사는 아래 제품의 원재료가 식물성 원재료 기준에 따라 검토되었음을 확인합니다.", "", f"제품명: {product_name}"]),
        "non_animal": ("비동물성 원료 확인서", ["당사는 아래 제품이 동물성 유래 원료를 사용하지 않은 기준으로 검토되었음을 확인합니다.", "", f"제품명: {product_name}"]),
        "no_pork": ("돼지고기 미사용 확인서", ["당사는 아래 제품의 제조에 돼지고기 및 돼지고기 유래 원료를 사용하지 않음을 확인합니다.", "", f"제품명: {product_name}"]),
    }
    return templates.get(t_type, ("확인서", [f"제품명: {product_name}", "상기 제품에 대한 확인서를 발행합니다."]))

# --- PDF 생성 함수 (일반 템플릿) ---
def generate_template_pdf(product_name, t_type):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    title, lines = get_template_lines(product_name, t_type)
    if os.path.exists(LOGO_PATH): c.drawImage(ImageReader(LOGO_PATH), 50, h-90, 140, 40, mask='auto')
    c.setFont(PDF_FONT_BOLD, 18); c.drawCentredString(w/2, h-120, title)
    y = h-180
    c.setFont(PDF_FONT, 11)
    for l in lines:
        if l == "": y -= 10
        else: c.drawString(70, y, l); y -= 24
    y -= 50; c.drawString(70, y, "삼양사"); c.drawString(70, y-22, "품질책임자: __________________")
    if os.path.exists(STAMP_PATH): c.drawImage(ImageReader(STAMP_PATH), 220, y-45, 80, 80, mask='auto')
    c.showPage(); c.save(); buffer.seek(0)
    return buffer

# --- PDF 생성 함수 (원산지 증명서 - 요청대로 수정된 버전) ---
def generate_origin_certificate_pdf(product_name, main_ing, origin, receiver="수신자제위"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    today = datetime.today().strftime("%Y-%m-%d")

    # 테두리
    c.setLineWidth(0.8); c.rect(15, 15, w-30, h-30)

    # 1. 상단 회사명 영역 (상하좌우 정중앙)
    header_top, header_line = h-15, h-70
    if os.path.exists(LOGO_PATH):
        c.drawImage(ImageReader(LOGO_PATH), 30, h-55, 110, 24, mask='auto')
    c.setFont(PDF_FONT_BOLD, 22)
    c.drawCentredString(w/2, (header_top + header_line)/2 - 8, "주식회사 삼 양 사")
    c.line(15, header_line, w-15, header_line)

    # 2. 주소 영역 (상하좌우 정중앙)
    addr_line = h-95
    c.setFont(PDF_FONT, 9.5)
    c.drawCentredString(w/2, (header_line + addr_line)/2 - 3, "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277")
    c.line(15, addr_line, w-15, addr_line)

    # 3. 정보 박스
    info_top = addr_line - 15
    info_h = 115
    info_bot = info_top - info_h
    c.rect(15, info_bot, w-30, info_h)

    row_y = info_top - 25
    gap = 26
    c.setFont(PDF_FONT_BOLD, 11); c.drawString(35, row_y, "발신일자 :"); c.setFont(PDF_FONT, 11); c.drawString(115, row_y, today)
    row_y -= gap
    c.setFont(PDF_FONT_BOLD, 11); c.drawString(35, row_y, "수    신 :"); c.setFont(PDF_FONT, 11); c.drawString(115, row_y, receiver)
    row_y -= gap
    c.setFont(PDF_FONT_BOLD, 11); c.drawString(35, row_y, "참    조 :")
    row_y -= gap
    # 제목 선 겹침 방지: 글자 쓰고 선은 사각형 외곽선으로 대체됨
    c.setFont(PDF_FONT_BOLD, 11); c.drawString(35, row_y, "제    목 :"); c.setFont(PDF_FONT, 11); c.drawString(115, row_y, "원산지 증명")

    # 4. 본문
    body_y = info_bot - 35
    c.setFont(PDF_FONT, 11)
    c.drawString(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어")
    c.drawString(63, body_y - 16, "주신 각별한 애호에 감사 드립니다.") # 간격 좁힘
    c.drawString(45, body_y - 55, "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.")

    # 5. 테이블 (상하좌우 정중앙)
    t_top = body_y - 85
    t_h = 85
    t_bot = t_top - t_h
    x0, x1, x2, x3 = 25, 170, 340, w-25
    c.rect(x0, t_bot, x3-x0, t_h)
    c.line(x1, t_bot, x1, t_top); c.line(x2, t_bot, x2, t_top)
    h_h = 28
    c.line(x0, t_top-h_h, x3, t_top-h_h)
    
    c.setFont(PDF_FONT_BOLD, 11)
    c.drawCentredString((x0+x1)/2, t_top-18, "제품명")
    c.drawCentredString((x1+x2)/2, t_top-18, "주원료")
    c.drawCentredString((x2+x3)/2, t_top-18, "원료원산지")

    mid_y = t_bot + (t_h - h_h)/2 - 4
    c.setFont(PDF_FONT, 12); c.drawCentredString((x0+x1)/2, mid_y, product_name)
    c.setFont(PDF_FONT, 11); c.drawCentredString((x1+x2)/2, mid_y, str(main_ing))
    draw_wrapped_centered_text(c, origin, (x2+x3)/2, mid_y+2, (x3-x2)-15, PDF_FONT, 10)

    # 6. 하단부
    c.setFont(PDF_FONT, 11)
    c.drawString(45, t_bot - 35, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.")
    c.drawRightString(w-45, 120, "1부.끝.")

    f_y = 95
    c.drawCentredString(w/2, f_y, "인천광역시 서구 백범로 726")
    c.setFont(PDF_FONT_BOLD, 13); c.drawCentredString(w/2, f_y-22, "주식회사 삼양사")
    c.setFont(PDF_FONT, 11); c.drawCentredString(w/2, f_y-44, "식품안전팀장")
    if os.path.exists(STAMP_PATH): c.drawImage(ImageReader(STAMP_PATH), w/2+75, f_y-65, 70, 70, mask='auto')

    c.line(15, 35, w-15, 35)
    c.setFont(PDF_FONT, 8.5)
    c.drawString(35, 22, "서식3-J113Rev.0"); c.drawCentredString(w/2, 22, "㈜삼양사 인천1공장"); c.drawRightString(w-35, 22, "A4(210mm X 297mm)")
    
    c.showPage(); c.save(); buffer.seek(0)
    return buffer

def build_zip(docs):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as f:
        for name, data in docs: f.writestr(name, data)
    buf.seek(0)
    return buf

# --- UI 메인 로직 ---
p_code = st.query_params.get("product")

if p_code:
    p_data = df[df["product_code"] == p_code].copy()
    if len(p_data) == 0: st.error("제품을 찾을 수 없습니다.")
    else:
        # 중복 제거 및 정렬
        p_data['has_val'] = p_data['file'].notna() | p_data['template_type'].notna()
        p_data = p_data.sort_values('has_val', ascending=False).drop_duplicates('cert_name')
        
        p_name = p_data.iloc[0]["product_name"]
        st.title(f"📄 {p_name} 인증서 관리")
        
        zip_list = []
        for idx, row in p_data.reset_index(drop=True).iterrows():
            c_name = row["cert_name"]
            d_type = str(row["type"]).lower().strip()
            
            col1, col2, col3 = st.columns([0.5, 3.5, 1.2])
            f_bytes, f_name = None, ""

            # 케이스 1: 등록된 파일 다운로드
            if d_type == "file":
                fname = str(row.get("file", ""))
                fpath = os.path.join(FILES_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f: f_bytes = f.read()
                    f_name = fname
                else: 
                    with col2: st.caption(f"⚠️ {c_name} (파일 없음)")
                    continue

            # 케이스 2: 템플릿 생성
            elif d_type == "template":
                t_type = str(row.get("template_type", "")).lower()
                if t_type == "origin":
                    pdf = generate_origin_certificate_pdf(p_name, row.get("main_ingredient","-"), row.get("origin_country","-"))
                else:
                    pdf = generate_template_pdf(p_name, t_type)
                f_bytes = pdf.getvalue()
                f_name = f"{p_name}_{c_name}.pdf"

            if f_bytes:
                with col1: chk = st.checkbox("", key=f"chk_{idx}")
                with col2: st.write(c_name)
                with col3: st.download_button("다운로드", f_bytes, f_name, "application/pdf", key=f"dl_{idx}")
                zip_list.append((f_name, f_bytes, chk))

        if zip_list:
            st.divider()
            selected = [(n, b) for n, b, c in zip_list if c]
            if selected:
                st.download_button("선택 문서 ZIP 다운로드", build_zip(selected), f"{p_name}_인증서.zip", "application/zip")
            else:
                st.info("ZIP으로 다운로드할 문서를 왼쪽 체크박스에서 선택해주세요.")
else:
    st.title("🏭 제품 선택")
    products = df[["product_code", "product_name"]].drop_duplicates()
    for _, r in products.iterrows():
        st.markdown(f"- [{r['product_name']}](?product={r['product_code']})")
