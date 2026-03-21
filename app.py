import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import altair as alt
import plotly.graph_objects as go

st.set_page_config(page_title="HALO+ 企业诊断系统", layout="wide")
st.title("🏆 HALO+ 企业诊断系统")
st.markdown("输入企业名称（支持模糊查询），查看该企业的 HALO+ 总分及各维度得分")

# 数据路径（请根据实际路径修改）
BASE_DIR = r"D:\Finance\results"
total_file = os.path.join(BASE_DIR, "HALO_total_score.csv")

@st.cache_data
def load_data():
    if not os.path.exists(total_file):
        st.error(f"总分文件不存在: {total_file}")
        return pd.DataFrame()
    # 强制将 code 列作为字符串读取
    df = pd.read_csv(total_file, dtype={'code': str})
    # 检查必备列（注意列名可能为 'HA_score', 'LO_score', 'I_score', 'E_score'）
    required = ['code', 'name', 'year', 'HA_score', 'LO_score', 'I_score', 'E_score', 'HALO_score']
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"文件缺少列: {missing}")
        return pd.DataFrame()
    # 重命名以便使用
    df.rename(columns={
        'HA_score': 'HA',
        'LO_score': 'LO',
        'I_score': 'I',
        'E_score': 'E'
    }, inplace=True)
    return df

df_all = load_data()

if df_all.empty:
    st.stop()

query = st.text_input("🔍 请输入企业名称（如“万科”、“晶合集成”）", "")

if query:
    matched = df_all[df_all['name'].str.contains(query, case=False, na=False)]
    if matched.empty:
        st.warning("未找到匹配的企业，请尝试其他关键词。")
    else:
        unique_companies = matched[['code', 'name']].drop_duplicates()
        st.subheader(f"匹配到 {len(unique_companies)} 家企业，请选择：")
        company_options = unique_companies.apply(lambda x: f"{x['code']} - {x['name']}", axis=1).tolist()
        selected = st.selectbox("选择企业", company_options)
        selected_code = selected.split(" - ")[0]
        selected_name = selected.split(" - ")[1]

        df_company = matched[matched['code'] == selected_code].sort_values('year')
        st.subheader(f"📈 {selected_name} ({selected_code}) 历年 HALO+ 总分趋势")
        
        # 复制数据并确保年份是普通字符串
        chart_data = df_company.copy()
        chart_data['year'] = chart_data['year'].astype(str)
        
        # 使用 Altair 精确定义图表
        # 'year:O' 代表把年份当做离散的类别，axis=alt.Axis(labelAngle=0) 强制文字水平不旋转
        # scale=alt.Scale(zero=False) 让 Y 轴不强制从 0 开始，能更清晰看到分数的起伏
        base_chart = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X('year:O', title='年份', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('HALO_score:Q', title='HALO+ 总分', scale=alt.Scale(zero=False)),
            tooltip=['year', 'HALO_score'] # 鼠标悬浮时显示提示框
        ).properties(height=350)

        # 渲染图表
        st.altair_chart(base_chart, use_container_width=True)

        st.subheader("📊 各维度得分详情")
        show_cols = ['year', 'HA', 'LO', 'I', 'E', 'HALO_score']
        st.dataframe(df_company[show_cols].round(2).style.format("{:.2f}"))

        # 近三年均值雷达图
        # 近三年均值雷达图
        mean_scores = df_company[['HA', 'LO', 'I', 'E']].mean().round(2)
        st.subheader(f"📌 {selected_name} 近三年各维度得分均值")
        
        categories = ['HA', 'LO', 'I', 'E']
        values = [mean_scores['HA'], mean_scores['LO'], mean_scores['I'], mean_scores['E']]
        
        # 使用 Plotly 绘制现代化的交互式雷达图
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            fillcolor='rgba(0, 110, 255, 0.2)', # 优雅的半透明蓝色填充
            line=dict(color='#006eff', width=2),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            polar=dict(
                # 把雷达图内部圆圈的底色调成纯白（带一点透明度），让里面的数字更清晰
                bgcolor='rgba(255, 255, 255, 0.8)',
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    showticklabels=True,
                    # 【关键修改】里面的分数数字：加大字号，并强制设为纯黑色
                    tickfont=dict(size=13, color='black'), 
                    tickangle=0,
                    gridcolor='lightgrey'
                ),
                angularaxis=dict(
                    linewidth=1,
                    showline=True,
                    linecolor='lightgrey',
                    # 【关键修改】外圈的字母(HA, LO...)：字号调大到16
                    tickfont=dict(size=16) 
                )
            ),
            showlegend=False,
            height=400, 
            margin=dict(t=40, b=40, l=40, r=40)
        )
        
        # 渲染到页面上
        st.plotly_chart(fig, use_container_width=True)

        # ------------- 华丽的分割线 -------------
        st.markdown("---")
        st.subheader("👑 行业排行榜：平均总分 Top X 企业")
        
        # 1. 让用户自己输入想看前几名（默认看前10名）
        top_x = st.number_input("请输入想要查看的 Top 企业数量：", min_value=1, max_value=500, value=10, step=1)
        
        # 2. 计算所有企业历年的“平均得分”
        # 使用 groupby 按企业代码和名称分组，计算各维度的平均值，并重置索引
        avg_scores = df_all.groupby(['code', 'name'])[['HA', 'LO', 'I', 'E', 'HALO_score']].mean().reset_index()
        
        # 3. 按照 HALO_score 平均分从高到低排序，并截取前 top_x 名
        top_companies = avg_scores.sort_values(by='HALO_score', ascending=False).head(top_x)
        
        # 4. 把数字保留两位小数，让表格更好看
        top_companies_display = top_companies.round(2)
        
        # 5. 在页面上展示排行榜表格
        st.dataframe(top_companies_display.style.format({
            'HA': '{:.2f}', 'LO': '{:.2f}', 'I': '{:.2f}', 'E': '{:.2f}', 'HALO_score': '{:.2f}'
        }))
        
        # 6. 生成可供下载的 CSV 文件数据
        # 注意：这里用 utf-8-sig 编码，是为了防止用 Excel 打开下载的 CSV 时中文名字变乱码！
        csv_data = top_companies_display.to_csv(index=False).encode('utf-8-sig')
        
        # 7. 添加批量下载按钮
        st.download_button(
            label=f"📥 一键下载 Top {top_x} 企业数据 (CSV)",
            data=csv_data,
            file_name=f"HALO_Top_{top_x}_企业排行榜.csv",
            mime="text/csv"
        )