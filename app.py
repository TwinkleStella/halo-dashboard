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

# 直接读取同一文件夹下的数据文件
total_file = "HALO_total_score.csv"

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
    # 【自动清洗补丁】：强制把主表的 code 变成 6 位数文本
    df['code'] = df['code'].astype(str).str.zfill(6)
    return df

df_all = load_data()

if df_all.empty:
    st.stop()
    
# ================== 🌟 新增：精准匹配申万行业并计算排名 ==================
@st.cache_data
def load_and_calculate_ranks(df_main):
    # 1. 计算所有企业历年 HALO+ 总分的平均值，作为排名的基准
    avg_scores = df_main.groupby(['code', 'name'])[['HA', 'LO', 'I', 'E', 'HALO_score']].mean().reset_index()
    
    # 2. 读取你专门清洗好的行业分类文件
    industry_file = "申万行业分类_cleaned.csv"
    if os.path.exists(industry_file):
        # 强制把 code 读为字符串
        df_industry = pd.read_csv(industry_file, dtype={'code': str})
        
        # 【关键修复】把类似 "1" 的代码补齐为 "000001"，防止和主表匹配不上！
        df_industry['code'] = df_industry['code'].str.zfill(6)
        
        # 因为有连续几年的数据，同一个企业我们只取一行行业标签即可
        df_ind_unique = df_industry[['code', 'industry']].drop_duplicates(subset=['code'])
        
        # 将行业信息完美合并进平均分表里
        avg_scores = pd.merge(avg_scores, df_ind_unique, on='code', how='left')
        avg_scores['industry'] = avg_scores['industry'].fillna('未分类')
    else:
        avg_scores['industry'] = '未分类'

    # 3. 计算全市场总排名（加入 fillna(0) 防止空值报错）
    avg_scores['global_rank'] = avg_scores['HALO_score'].rank(method='min', ascending=False).fillna(0).astype(int)
    
    # 4. 计算各行业内部的排名（加入 fillna(0) 防止空值报错）
    avg_scores['industry_rank'] = avg_scores.groupby('industry')['HALO_score'].rank(method='min', ascending=False).fillna(0).astype(int)
    
    # 5. 统计各类别的总企业数
    total_companies = len(avg_scores)
    industry_counts = avg_scores['industry'].value_counts().to_dict()
    
    return avg_scores, total_companies, industry_counts

# 运行计算引擎
df_ranks, total_companies, industry_counts = load_and_calculate_ranks(df_all)

# ================== 核心交互界面：三合一分流标签页 ==================

# 创建三个顶级标签页
tab1, tab2, tab3 = st.tabs(["🔍 单家企业诊断", "📂 批量客户筛查", "🏆 行业 Top 排行榜"])

# ----------------- 路径一：单家企业诊断（你原本的功能） -----------------
with tab1:
    st.markdown("#### 输入企业名称（支持模糊查询），查看该企业的 HALO+ 总分及各维度得分")
    query = st.text_input("🔍 请输入企业名称（如“万科”、“晶合集成”）", "", key="single_search")

    if query:
        matched = df_all[df_all['name'].str.contains(query, case=False, na=False)]
        if matched.empty:
            st.warning("未找到匹配的企业，请尝试其他关键词。")
        else:
            unique_companies = matched[['code', 'name']].drop_duplicates()
            company_options = unique_companies.apply(lambda x: f"{x['code']} - {x['name']}", axis=1).tolist()
            selected = st.selectbox("选择企业", company_options)
            selected_code = selected.split(" - ")[0]
            selected_name = selected.split(" - ")[1]

            df_company = matched[matched['code'] == selected_code].sort_values('year')
            
            # --- 🌟 新增：展示企业排名仪表盘 ---
            company_rank_info = df_ranks[df_ranks['code'] == selected_code]
            if not company_rank_info.empty:
                r_info = company_rank_info.iloc[0]
                ind_name = r_info['industry']
                ind_total = industry_counts.get(ind_name, 1) # 该行业的总企业数
                
                # 画三个并排的漂亮指标卡片
                st.markdown("### 🏅 综合排名与行业地位 (基于历年均值)")
                col_m1, col_m2, col_m3 = st.columns(3)
                
                col_m1.metric(label="📌 平均综合得分", value=f"{r_info['HALO_score']:.2f} 分")
                
                col_m2.metric(
                    label="🏆 全市场总排名", 
                    value=f"第 {r_info['global_rank']} 名", 
                    delta=f"打败了 {(1 - r_info['global_rank']/total_companies)*100:.1f}% 的企业",
                    delta_color="normal"
                )
                
                if ind_name == '未分类':
                    col_m3.metric(label="🏢 行业内排名", value="暂无分类数据", delta="缺少匹配信息", delta_color="off")
                else:
                    col_m3.metric(
                        label=f"🏢 申万行业({ind_name}) 排名", 
                        value=f"第 {r_info['industry_rank']} 名", 
                        delta=f"该细分行业共 {ind_total} 家企业", 
                        delta_color="off"
                    )
                st.markdown("---")
                
            # --- 渲染折线图 ---
            st.subheader(f"📈 {selected_name} ({selected_code}) 历年 HALO+ 总分趋势")
            chart_data = df_company.copy()
            chart_data['year'] = chart_data['year'].astype(str)
            base_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X('year:O', title='年份', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('HALO_score:Q', title='HALO+ 总分', scale=alt.Scale(zero=False)),
                tooltip=['year', 'HALO_score']
            ).properties(height=350)
            st.altair_chart(base_chart, use_container_width=True)

            # --- 渲染表格与雷达图 ---
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("📊 各维度得分详情")
                show_cols = ['year', 'HA', 'LO', 'I', 'E', 'HALO_score']
                st.dataframe(df_company[show_cols].round(2).style.format("{:.2f}"), use_container_width=True)
            
            with col2:
                mean_scores = df_company[['HA', 'LO', 'I', 'E']].mean().round(2)
                st.subheader("📌 近三年各维度均值")
                categories = ['HA', 'LO', 'I', 'E']
                values = [mean_scores['HA'], mean_scores['LO'], mean_scores['I'], mean_scores['E']]
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=values, theta=categories, fill='toself',
                    fillcolor='rgba(0, 110, 255, 0.2)', line=dict(color='#006eff', width=2), marker=dict(size=8)
                ))
                fig.update_layout(
                    polar=dict(
                        bgcolor='rgba(255, 255, 255, 0.8)',
                        radialaxis=dict(visible=True, range=[0, 100], showticklabels=True, tickfont=dict(size=13, color='black'), tickangle=0, gridcolor='lightgrey'),
                        angularaxis=dict(linewidth=1, showline=True, linecolor='lightgrey', tickfont=dict(size=16))
                    ),
                    showlegend=False, height=350, margin=dict(t=30, b=30, l=40, r=40)
                )
                st.plotly_chart(fig, use_container_width=True)


# ----------------- 路径二：批量客户名单筛查（新增功能） -----------------
with tab2:
    st.markdown("#### 批量检测您的客户名单中是否包含高得分企业")
    
    # 左侧输入，右侧设置阈值
    col_input, col_setting = st.columns([2, 1])
    
    with col_input:
        client_input = st.text_area(
            "📋 请在此粘贴客户名单（每行一个企业名称）：", 
            height=200, 
            placeholder="示例格式：\n万科\n宁德时代\n晶合集成\n（直接从 Excel 复制一列粘贴即可）"
        )
    
    with col_setting:
        st.info("💡 评分标准设置")
        # 让用户自己定义多少分算“高分”
        score_threshold = st.slider("最低合格分数（HALO+ 总分）：", min_value=0.0, max_value=100.0, value=60.0, step=1.0)
        st.markdown(f"**当前筛选条件**：平均分 $\ge {score_threshold}$")
        
        # 将按钮放在右侧下面
        start_batch = st.button("🚀 立即开始批量筛查", use_container_width=True)

    if start_batch:
        if not client_input.strip():
            st.warning("⚠️ 请先在左侧输入框中粘贴您的客户名单！")
        else:
            # 1. 清洗输入的数据，去掉空行和多余空格
            client_list = [name.strip() for name in client_input.split('\n') if name.strip()]
            
            # 2. 计算所有企业库的历史平均分（作为底表）
            avg_scores_db = df_all.groupby(['code', 'name'])[['HA', 'LO', 'I', 'E', 'HALO_score']].mean().reset_index()
            
            # 3. 进行名单匹配 (使用包含关系，只要库里的名字包含客户名字就匹配上)
            import re
            # 用正则的 | 把所有客户名字连起来，变成 "万科|宁德时代|..."
            pattern = '|'.join([re.escape(c) for c in client_list]) 
            matched_batch = avg_scores_db[avg_scores_db['name'].str.contains(pattern, case=False, na=False)]
            
            if matched_batch.empty:
                 st.error("没有在系统库中匹配到您提供的任何客户。")

            else:
                # 4. 筛选出超过用户设定阈值的企业
                high_scorers = matched_batch[matched_batch['HALO_score'] >= score_threshold].sort_values(by='HALO_score', ascending=False)
                
                st.success(f"✅ 筛查完毕！在提交的 {len(client_list)} 家客户中，匹配到 {len(matched_batch)} 家系统企业。其中 **{len(high_scorers)} 家** 达到高分标准（$\ge {score_threshold}$）！")
                
                # 5. 展示结果与下载按钮
                high_scorers_display = high_scorers.round(2)
                st.dataframe(high_scorers_display.style.format({'HA': '{:.2f}', 'LO': '{:.2f}', 'I': '{:.2f}', 'E': '{:.2f}', 'HALO_score': '{:.2f}'}), use_container_width=True)
                
                csv_batch = high_scorers_display.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 导出高分匹配结果 (CSV)", data=csv_batch, file_name=f"高分客户名单筛查结果_{score_threshold}分以上.csv", mime="text/csv")


# ----------------- 路径三：HALO+ 高分企业优选池（多维严选模型） -----------------
with tab3:
    st.markdown("#### 🏆 HALO+ 高分企业智能优选池")
    st.markdown("基于多维严选模型，为您自动过滤掉存在单项短板或近期业绩下滑的标的，筛选出真正的优质企业。")
    
    # 将严选准则做成可交互的控制面板（默认值设为你截图里的标准）
    with st.expander("⚙️ 展开查看或动态调整筛选阈值", expanded=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("**1. 综合优异 (HALO总分)**")
            halo_avg_min = st.number_input("总分近三年均值 >", value=60.0, step=1.0)
            halo_2023_min = st.number_input("总分2023年单年 >", value=60.0, step=1.0)
        with col_p2:
            st.markdown("**2. 无明显短板 (四个子项)**")
            sub_avg_min = st.number_input("各子项近三年均值 >", value=50.0, step=1.0)
            sub_2023_min = st.number_input("各子项2023年单年 >", value=50.0, step=1.0)
        with col_p3:
            st.markdown("**3. E项相对突出**")
            e_avg_min = st.number_input("E项近三年均值 >", value=60.0, step=1.0)
            e_2023_min = st.number_input("E项2023年单年 >", value=60.0, step=1.0)

    # --- 数据处理与量化筛选引擎 ---
    # 1. 计算近三年均值
    df_avg = df_all.groupby(['code', 'name'])[['HA', 'LO', 'I', 'E', 'HALO_score']].mean().reset_index()
    
    # 2. 提取 2023 年单年数据 (安全提取，防止 year 列格式差异)
    df_2023 = df_all[df_all['year'].astype(str).str.contains('2023')][['code', 'HA', 'LO', 'I', 'E', 'HALO_score']]
    # 为了合并时列名不冲突，给 2023 年的数据加上后缀
    df_2023.columns = ['code', 'HA_23', 'LO_23', 'I_23', 'E_23', 'HALO_23']
    
    # 3. 将均值和 2023 年数据合并到一张大表上
    df_pool = pd.merge(df_avg, df_2023, on='code', how='inner')
    
    # 4. 执行严选逻辑：根据上方面板设定的阈值进行布尔筛选
    cond1 = (df_pool['HALO_score'] > halo_avg_min) & (df_pool['HALO_23'] > halo_2023_min)
    cond2 = (df_pool['HA'] > sub_avg_min) & (df_pool['LO'] > sub_avg_min) & (df_pool['I'] > sub_avg_min) & (df_pool['E'] > sub_avg_min) & \
            (df_pool['HA_23'] > sub_2023_min) & (df_pool['LO_23'] > sub_2023_min) & (df_pool['I_23'] > sub_2023_min) & (df_pool['E_23'] > sub_2023_min)
    cond3 = (df_pool['E'] > e_avg_min) & (df_pool['E_23'] > e_2023_min)
    
    # 获取最终过关的企业名单，并按总分均值排序
    final_pool = df_pool[cond1 & cond2 & cond3].sort_values(by='HALO_score', ascending=False)
    
    # --- 结果展示与下载 ---
    if final_pool.empty:
        st.warning("⚠️ 在当前严格的筛选标准下，全市场暂无符合条件的企业。您可以尝试在上方放宽条件。")
    else:
        st.success(f"🎉 严选完成！经过层层过滤，全市场共筛选出 **{len(final_pool)}** 家完美的【HALO+ 高分优质企业】。")
        
        # 整理展示用的表格，提取核心关键指标并汉化列名
        display_df = final_pool[['code', 'name', 'HALO_score', 'HALO_23', 'E', 'E_23', 'HA', 'LO', 'I']].copy()
        display_df.columns = ['企业代码', '企业名称', 'HALO总分(均值)', 'HALO总分(23年)', 'E项(均值)', 'E项(23年)', 'HA(均值)', 'LO(均值)', 'I(均值)']
        display_df = display_df.round(2)
        
        # 渲染出漂亮的高亮表格
        st.dataframe(display_df, use_container_width=True)
        
        # 批量下载按钮
        csv_pool = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label=f"📥 一键下载优选池企业名单 ({len(final_pool)}家)",
            data=csv_pool,
            file_name="HALO系统_严选高分企业池.csv",
            mime="text/csv"
        )
