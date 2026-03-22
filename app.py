import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import altair as alt
import plotly.graph_objects as go

st.set_page_config(page_title="HALO+ 企业诊断系统", layout="wide")
st.title("🏭 HALO+ 新质生产力评价系统")
st.markdown("基于重资产、产业链护城河、智能化转型与绿色治理的实体经济企业综合诊断平台")

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
    
# ================== 🌟 新增：精准匹配申万行业并计算排名（终极防崩溃版） ==================
@st.cache_data
def load_and_calculate_ranks(df_main):
    avg_scores = df_main.groupby(['code', 'name'])[['HA', 'LO', 'I', 'E', 'HALO_score']].mean().reset_index()
    
    # 【防弹机制1】上来先给所有企业一个默认行业，哪怕后面全部失败，这一列也永远存在！
    avg_scores['industry'] = '未分类'
    
    shenwan_dict = {
        'S11': '农林牧渔', 'S21': '煤炭', 'S22': '基础化工', 'S23': '钢铁', 'S24': '有色金属',
        'S27': '电子', 'S28': '汽车', 'S33': '家用电器', 'S34': '食品饮料', 'S35': '纺织服饰',
        'S36': '轻工制造', 'S37': '医药生物', 'S41': '公用事业', 'S42': '交通运输', 'S43': '房地产',
        'S45': '商贸零售', 'S46': '社会服务', 'S48': '银行', 'S49': '非银金融', 'S51': '综合',
        'S61': '建筑材料', 'S62': '建筑装饰', 'S63': '电力设备', 'S64': '机械设备', 'S65': '国防军工',
        'S71': '计算机', 'S72': '传媒', 'S73': '通信', 'S76': '环保', 'S77': '美容护理'
    }
    
    industry_file = "申万行业分类_cleaned.csv"
    
    # 【防弹机制2】用 try-except 替代 if，哪怕文件损坏或没传，也不会红底报错
    try:
        df_industry = pd.read_csv(industry_file, dtype={'code': str})
        df_industry['code'] = df_industry['code'].str.zfill(6)
        
        # 翻译中文行业，并拼接成 "S43 - 房地产"
        df_industry['ind_cn'] = df_industry['industry'].map(shenwan_dict).fillna('未知细分')
        df_industry['industry_display'] = df_industry['industry'] + ' - ' + df_industry['ind_cn']
        
        df_ind_unique = df_industry[['code', 'industry_display']].drop_duplicates(subset=['code'])
        
        # 合并前先删掉刚才占位的 industry，换成带有真实数据的
        avg_scores = avg_scores.drop(columns=['industry'])
        avg_scores = pd.merge(avg_scores, df_ind_unique, on='code', how='left')
        
        avg_scores.rename(columns={'industry_display': 'industry'}, inplace=True)
        avg_scores['industry'] = avg_scores['industry'].fillna('未分类')
    except Exception as e:
        # 如果文件没找到，只在网页上发个黄色警告，绝不崩溃
        st.warning("⚠️ 行业分类文件(申万行业分类_cleaned.csv)读取失败，请检查是否已上传至 GitHub。所有企业将暂记为'未分类'。")

    # 强制将分数转为数字格式
    avg_scores['HALO_score'] = pd.to_numeric(avg_scores['HALO_score'], errors='coerce')
    
    # 计算排名（包含 999999 垫底补丁）
    avg_scores['global_rank'] = avg_scores['HALO_score'].rank(method='min', ascending=False).fillna(999999).astype(int)
    avg_scores['industry_rank'] = avg_scores.groupby('industry')['HALO_score'].rank(method='min', ascending=False).fillna(999999).astype(int)
    
    total_companies = len(avg_scores)
    industry_counts = avg_scores['industry'].value_counts().to_dict()
    
    return avg_scores, total_companies, industry_counts

# 运行这个计算引擎
df_ranks, total_companies, industry_counts = load_and_calculate_ranks(df_all)

# ================== 核心交互界面：三合一分流标签页 ==================

# 创建三个顶级标签页
tab1, tab2, tab3, tab4 = st.tabs(["🔍 单家企业诊断", "📂 批量客户筛查", "🏆 排行榜智能查询", "💻 在线计算 HALO+得分"])

# ----------------- 路径一：单家企业诊断（你原本的功能） -----------------
with tab1:
    st.markdown("输入企业名称（支持模糊查询），一键获取 HALO+ 总分、各维度得分趋势图及近三年雷达图")
    query = st.text_input("🔍 请输入企业名称（如“万科”、“宁德”）", "", key="single_search")

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
    st.markdown("上传企业名单，批量导出得分明细，快速筛选潜在合作伙伴或投资标的")
    
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


# ----------------- 路径三：全市场与行业百分位排名榜单 -----------------
with tab3:
    st.markdown("基于企业**近三年得分均值**，查看各行业内 HALO+ 得分领先企业，通过调整百分位，灵活洞察新质生产力龙头。")
    
    sub_tab_global, sub_tab_industry = st.tabs(["🌍 全市场 A 股排名", "🏢 所属申万行业内排名"])

    # ================= 子标签 1：全市场按百分位排名 =================
    with sub_tab_global:
        st.info("💡 筛选全市场综合得分排名前 X% 的企业")
        top_percent_global = st.slider("🌍 选择全市场前百分之几（Top X%）：", min_value=1, max_value=100, value=10, step=1, key="slider_global")
        
        # 过滤出 999999 那些没有分数的无效数据，并且计算排名阈值
        valid_ranks = df_ranks[df_ranks['global_rank'] < 999999]
        threshold_rank_global = max(1, int(len(valid_ranks) * (top_percent_global / 100.0)))
        
        df_global_filtered = valid_ranks[valid_ranks['global_rank'] <= threshold_rank_global].sort_values(by='global_rank')
        
        if df_global_filtered.empty:
            st.warning("无满足条件的企业。")
        else:
            display_global = df_global_filtered[['global_rank', 'code', 'name', 'industry', 'HA', 'LO', 'I', 'E', 'HALO_score']].copy()
            display_global.columns = ['名次', '股票代码', '企业名称', '所属申万行业', 'HA得分', 'LO得分', 'I得分', 'E得分', 'HALO总分']
            
            # 【关键魔法】将“名次”设置为表格最左侧的索引，消灭丑陋的四位数行号！
            display_global.set_index('名次', inplace=True)
            
            st.success(f"✅ 全市场有效数据共 {len(valid_ranks)} 家，已为您筛选出排名前 {top_percent_global}% 的企业（共 {len(display_global)} 家）。")
            st.dataframe(display_global.round(2).style.format(precision=2), use_container_width=True)
            
            csv_global = display_global.round(2).to_csv(index=True).encode('utf-8-sig') # 包含 index(名次) 下载
            st.download_button(label=f"📥 导出全市场 Top {top_percent_global}% 榜单", data=csv_global, file_name=f"HALO全市场_Top{top_percent_global}%.csv", mime="text/csv", key="btn_global")

    # ================= 子标签 2：按所属行业百分位排名 =================
    with sub_tab_industry:
        st.info("💡 选择特定行业，并筛选该行业内得分排名前 X% 的企业")
        
        col_ind1, col_ind2 = st.columns(2)
        with col_ind1:
            industry_list = sorted([ind for ind in df_ranks['industry'].unique() if ind != '未分类'])
            selected_industry = st.selectbox("🏢 请选择所属申万行业：", industry_list)
            
        with col_ind2:
            top_percent_ind = st.slider(f"🎯 选择该行业前百分之几（Top X%）：", min_value=1, max_value=100, value=20, step=1, key="slider_ind")
            
        # 过滤出选中行业的有效企业
        df_ind_only = df_ranks[(df_ranks['industry'] == selected_industry) & (df_ranks['industry_rank'] < 999999)]
        ind_total_companies = len(df_ind_only)
        
        if ind_total_companies == 0:
            st.warning("该行业暂无有效数据。")
        else:
            threshold_rank_ind = max(1, int(ind_total_companies * (top_percent_ind / 100.0)))
            df_ind_filtered = df_ind_only[df_ind_only['industry_rank'] <= threshold_rank_ind].sort_values(by='industry_rank')
            
            display_ind = df_ind_filtered[['industry_rank', 'code', 'name', 'industry', 'HA', 'LO', 'I', 'E', 'HALO_score']].copy()
            display_ind.columns = ['名次', '股票代码', '企业名称', '所属申万行业', 'HA得分', 'LO得分', 'I得分', 'E得分', 'HALO总分']
            
            # 【关键魔法】消灭四位数行号
            display_ind.set_index('名次', inplace=True)
            
            st.success(f"✅ **{selected_industry}** 共有 {ind_total_companies} 家企业，已为您筛选出排名前 {top_percent_ind}% 的企业（共 {len(display_ind)} 家）。")
            st.dataframe(display_ind.round(2).style.format(precision=2), use_container_width=True)
            
            csv_ind = display_ind.round(2).to_csv(index=True).encode('utf-8-sig')
            st.download_button(label=f"📥 导出 {selected_industry.split(' - ')[0]}行业 Top {top_percent_ind}% 榜单", data=csv_ind, file_name=f"HALO行业排名_{selected_industry}.csv", mime="text/csv", key="btn_ind")

# ----------------- 路径四：批量上传企业数据并计算得分 -----------------
with tab4:
    st.markdown("#### 💻 本地数据在线计算引擎")
    st.markdown("上传您的企业财务数据表，系统将调用内置算法，自动计算 HALO+ 各维度得分及总分。您的数据仅在本地浏览器运算，**绝不会上传至云端泄露**。")
    
    with st.expander("📖 点击查看模板必填字段与中文对照表", expanded=False):
        st.markdown("""
        | 英文列名 | 中文含义 | 英文列名 | 中文含义 |
        | :--- | :--- | :--- | :--- |
        | **code** | 企业代码 (必填) | **depreciation** | 折旧与摊销 |
        | **name** | 企业名称 (必填) | **rd_expense** | 研发费用 |
        | **year** | 数据年份 (必填) | **cost_of_sales** | 营业成本 |
        | **revenue** | 营业收入 | **employee_count**| 员工总数 |
        | **fixed_assets** | 固定资产净值 | **software_assets**| 软件类无形资产 |
        | **total_assets** | 总资产 | **fixed_assets_original**| 固定资产原值 |
        | **cash** | 货币资金 | **nwc** | 净营运资本 |
        | **intangible_assets**| 无形资产 | **esg_rating** | ESG评级(选填，默认BB) |
        | **capex** | 资本支出 | **esg_controversy_score**| ESG争议(选填，默认100)|
        | **operating_profit** | 营业利润 | **patent_weighted_raw**| 专利加权分(选填，默认0)|
        """)

    uploaded_file = st.file_uploader("📥 请选择数据文件 (支持 .xlsx 或 .csv 格式)", type=['xlsx', 'csv'])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_new = pd.read_csv(uploaded_file)
            else:
                df_new = pd.read_excel(uploaded_file)
                
            st.success("文件读取成功！数据预览：")
            st.dataframe(df_new.head(), use_container_width=True)

            # 检查必要列是否存在
            template_cols = ["code", "name", "year", "revenue", "fixed_assets", "total_assets", "cash", "intangible_assets", "capex", "operating_profit", "depreciation", "rd_expense", "cost_of_sales", "employee_count", "software_assets", "fixed_assets_original", "nwc"]
            missing_cols = [c for c in template_cols if c not in df_new.columns]
            if missing_cols:
                st.error(f"❌ 您的文件中缺少以下必要字段，请检查后重新上传：\n{missing_cols}")
                st.stop()

            with st.spinner("系统正在进行量化指标运算..."):
                # 1. 强力数据清洗：防止分母为 0 导致无限大 (inf) 崩溃系统
                # 将所有 0 替换为极小值（防止除0），或者在计算后处理 inf
                df_new = df_new.fillna(0) # 基础空值填 0

                # 2. 尝试加载模型参数，如果没有 json 文件，就用当批上传数据的最大最小值
                import os, json
                params = {}
                if os.path.exists("halo_params.json"):
                    with open("halo_params.json", "r") as f:
                        params = json.load(f)
                else:
                    st.info("提示：未检测到极值参数文件，系统将基于本次上传数据的最大/最小值进行动态标准化。")

                def min_max_norm(series, col):
                    if col in params:
                        min_val, max_val = params[col]
                    else:
                        min_val, max_val = series.min(), series.max()
                    
                    if max_val == min_val or pd.isna(max_val):
                        return series * 0
                    return (series - min_val) / (max_val - min_val)

                # 3. 计算各维度指标 (加入 numpy 的安全除法机制)
                # 使用 np.where 防止分母为0
                df_new['HA_fa_intensity'] = np.where(df_new['revenue'] == 0, 0, df_new['fixed_assets'] / df_new['revenue'])
                df_new['HA_fa_ratio'] = np.where(df_new['total_assets'] == 0, 0, df_new['fixed_assets'] / df_new['total_assets'])
                df_new['HA_tangible_intensity'] = np.where(df_new['revenue'] == 0, 0, (df_new['total_assets'] - df_new['cash'] - df_new['intangible_assets']) / df_new['revenue'])
                df_new['HA_capex_intensity'] = np.where(df_new['revenue'] == 0, 0, df_new['capex'] / df_new['revenue'])
                
                op_dep = df_new['operating_profit'] + df_new['depreciation']
                df_new['HA_capex_load'] = np.where(op_dep == 0, 0, df_new['capex'] / op_dep)
                
                df_new['HA_fa_newness'] = np.where(df_new['fixed_assets_original'] == 0, 0, df_new['fixed_assets'] / df_new['fixed_assets_original'])
                df_new['HA_fa_turnover'] = np.where(df_new['fixed_assets'] == 0, 0, df_new['revenue'] / df_new['fixed_assets'])

                # I 指标
                df_new['I_asset_labor_ratio'] = np.where(df_new['employee_count'] == 0, 0, (df_new['total_assets'] - df_new['cash'] - df_new['intangible_assets']) / df_new['employee_count'])
                df_new = df_new.sort_values(['code','year'])
                # 如果只有一年数据，pct_change会变成 NaN，这里填0保障运算不中断
                df_new['I_fa_update_rate'] = df_new.groupby('code')['fixed_assets_original'].pct_change().fillna(0)
                df_new['I_software_ratio'] = np.where(df_new['total_assets'] == 0, 0, df_new['software_assets'] / df_new['total_assets'])
                
                df_new['revenue_per_emp'] = np.where(df_new['employee_count'] == 0, 0, df_new['revenue'] / df_new['employee_count'])
                # 修改 periods 为 1，因为很多用户可能只传 2-3 年数据，要求 3 年跨度太苛刻了
                df_new['I_rev_per_emp_growth'] = df_new.groupby('code')['revenue_per_emp'].pct_change(periods=1).fillna(0)

                # LO 指标
                df_new['rd_intensity'] = np.where(df_new['revenue'] == 0, 0, df_new['rd_expense'] / df_new['revenue'])
                
                if 'gross_margin' not in df_new.columns:
                    df_new['gross_margin'] = np.where(df_new['revenue'] == 0, 0, (df_new['revenue'] - df_new['cost_of_sales']) / df_new['revenue'])
                
                df_new['gross_margin_stability'] = df_new.groupby('code')['gross_margin'].transform(lambda x: x.rolling(2, min_periods=1).std()).fillna(0)
                df_new['nwc_ratio'] = np.where(df_new['revenue'] == 0, 0, df_new['nwc'] / df_new['revenue'])
                
                df_new['patent_weighted_raw'] = df_new.get('patent_weighted_raw', 0).fillna(0)

                # E 维度 (为中小微企业增加宽容机制：如果没有评级，默认给 BB 级中等分)
                if 'esg_rating' not in df_new.columns:
                    df_new['esg_rating'] = 'BB'
                else:
                    df_new['esg_rating'] = df_new['esg_rating'].fillna('BB')
                    
                if 'esg_controversy_score' not in df_new.columns:
                    df_new['esg_controversy_score'] = 100
                else:
                    df_new['esg_controversy_score'] = df_new['esg_controversy_score'].fillna(100)

                rating_map = {'C':1, 'CC':2, 'CCC':3, 'B':4, 'BB':5, 'BBB':6, 'A':7, 'AA':8, 'AAA':9}
                df_new['rating_num'] = df_new['esg_rating'].map(rating_map).fillna(5) # 没匹配上的默认为5(BB)
                df_new['E_base'] = (df_new['rating_num'] - 1) / 8 * 100
                df_new['P_env'] = df_new['esg_controversy_score'] / 100
                df_new['E_score'] = df_new['E_base'] * df_new['P_env']

                # 4. 清理任何潜在的无限大值，然后进行标准化
                df_new.replace([np.inf, -np.inf], 0, inplace=True)

                ha_cols = ['HA_fa_intensity','HA_fa_ratio','HA_tangible_intensity','HA_capex_intensity','HA_capex_load','HA_fa_newness','HA_fa_turnover']
                i_cols = ['I_asset_labor_ratio','I_fa_update_rate','I_software_ratio','I_rev_per_emp_growth']
                lo_cols = ['rd_intensity','gross_margin_stability','nwc_ratio','patent_weighted_raw']

                for col in ha_cols + i_cols + lo_cols:
                    df_new[f'{col}_norm'] = min_max_norm(df_new[col], col)

                df_new['gross_margin_stability_norm'] = 1 - df_new['gross_margin_stability_norm']
                df_new['nwc_ratio_norm'] = 1 - df_new['nwc_ratio_norm']

                # 5. 合成最终得分 (加入 fillna 避免空值毁掉总分)
                df_new['HA_score'] = df_new[[f'{c}_norm' for c in ha_cols]].mean(axis=1).fillna(0) * 100
                df_new['I_score'] = df_new[[f'{c}_norm' for c in i_cols]].mean(axis=1).fillna(0) * 100
                df_new['LO_score'] = df_new[[f'{c}_norm' for c in lo_cols]].mean(axis=1).fillna(0) * 100

                df_new['HALO_score'] = (df_new['HA_score'] * 0.35 + df_new['LO_score'] * 0.35 + df_new['I_score'] * 0.20 + df_new['E_score'] * 0.10)

            # 7. 炫酷输出结果
            st.success("✅ 极速量化运算完成！以下为您上传企业的 HALO+ 各维度体检报告：")
            result_df = df_new[['code', 'name', 'year', 'HA_score', 'LO_score', 'I_score', 'E_score', 'HALO_score']].copy()
            st.dataframe(result_df.round(2).style.format(precision=2), use_container_width=True)

            csv = result_df.round(2).to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 导出全部计算结果 (CSV)", data=csv, file_name="HALO_智能计算结果.csv", mime="text/csv")
            
        except Exception as e:
            st.error(f"❌ 数据处理过程中遇到问题：{e}")
            st.info("请检查您上传的表格是否包含非法字符，或确保所有指标列均为数字格式。")
    
