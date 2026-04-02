import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="인증서 다운로드", layout="centered")

# 경로 설정 (안전한 방식)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")

# 데이터 불러오기
df = pd.read_csv(CSV_PATH)

# URL 파라미터 받기
query_params = st.query_params
product_code = query_params.get("product")

# =========================
# 제품 선택된 경우
# =========================
if product_code:
    product_data = df[df["product_code"] == product_code]

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        st.title(product_data.iloc[0]["product_name"])
        st.write("아래 인증서를 다운로드하세요.")

        for _, row in product_data.iterrows():
            file_name = row["file"]

            # 빈값 방지
            if pd.isna(file_name):
                st.warning("파일 정보 없음")
                continue

            file_path = os.path.join(FILES_DIR, str(file_name))

            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"{row['cert_name']} 다운로드",
                        data=f,
                        file_name=file_name,
                        mime="application/pdf"
                    )
            else:
                st.warning(f"파일 없음: {file_name}")

# =========================
# 기본 페이지 (제품 선택)
# =========================
else:
    st.title("제품별 인증서 다운로드")
    st.write("제품을 선택하세요.")

    products = df[["product_code", "product_name"]].drop_duplicates()

    for _, row in products.iterrows():
        st.markdown(
            f"- [{row['product_name']}](?product={row['product_code']})"
        )
