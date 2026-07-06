import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Set page configuration for a wide, clean dashboard layout
st.set_page_config(page_title="IT Ticket Analytics System", layout="wide", initial_sidebar_state="expanded")

# Custom UI styling for high visual contrast, modern management aesthetics, and Tab Content Bounce Animations
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { color: #1E3A8A; font-weight: 700; }
    h3 { color: #1E40AF; font-weight: 600; margin-top: 1.5rem; }
    .stMetric { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #CBD5E1; }
    
    /* --- CSS KEYFRAME ANIMATION ENGINE FOR FLUID PLOT JERK/MOVEMENT --- */
    @keyframes plotBounceEntrance {
        0% {
            transform: scale(0.93) translateY(12px);
            opacity: 0.5;
        }
        55% {
            transform: scale(1.02) translateY(-4px); 
            opacity: 0.9;
        }
        75% {
            transform: scale(0.99) translateY(2px); 
        }
        100% {
            transform: scale(1) translateY(0); 
            opacity: 1;
        }
    }

    [data-testid="stPlotlyChart"] {
        animation: plotBounceEntrance 0.65s cubic-bezier(0.25, 1.1, 0.5, 1) both;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("📊 Automated IT Ticket Analysis Dashboard")
st.markdown("Transforming raw IT service logs into clean, actionable management insights.")
st.markdown("---")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Data Configuration")
uploaded_file = st.sidebar.file_uploader("Upload May Ticket Data (Excel)", type=["xlsx", "xls"])

# EXPLICIT HIGH-CONTRAST PALETTES PER PLOT
INBOUND_SOURCE_PALETTE = ["#EC4899", "#2563EB", "#10B981", "#F59E0B"] 
LOCATION_PALETTE = ["#06B6D4", "#F59E0B", "#10B981", "#2563EB", "#EC4899", "#111827"] 

if uploaded_file is not None:
    try:
        # Step 1: Handle sheet selection safely
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        default_index = 0
        for i, name in enumerate(sheet_names):
            if "raw" in name.lower() or "data" in name.lower():
                default_index = i
                break
                
        selected_sheet = st.sidebar.selectbox("Select Data Sheet:", options=sheet_names, index=default_index)
        
        # Step 2: Read full sheet
        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
        df.columns = df.columns.str.strip()
        
        st.sidebar.success(f"Loaded sheet: {selected_sheet}")
        
        # --- VIEW SELECTOR ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🗺️ Navigation Page")
        app_page = st.sidebar.radio("Go to Page:", options=["Dashboard Visuals", "Deep-Dive Issue Inventory"])
        
        # --- SIDEBAR COLUMN OVERRIDE INTERFACE ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Verify & Map Columns")
        
        all_cols = list(df.columns)
        
        def_team = next((c for c in all_cols if 'group' in c.lower() or 'team' in c.lower()), all_cols[0] if all_cols else None)
        def_source = next((c for c in all_cols if 'source' in c.lower() or 'channel' in c.lower() or 'mode' in c.lower()), all_cols[0] if all_cols else None)
        def_date = next((c for c in all_cols if 'date' in c.lower() or 'created' in c.lower() or 'opened' in c.lower()), all_cols[0] if all_cols else None)
        def_type = next((c for c in all_cols if 'category' in c.lower() or 'type' in c.lower() or 'classification' in c.lower()), all_cols[0] if all_cols else None)
        def_loc = next((c for c in all_cols if 'location' in c.lower() or 'site' in c.lower() or 'region' in c.lower() or 'branch' in c.lower()), all_cols[0] if all_cols else None)
        def_sla = next((c for c in all_cols if ('sla' in c.lower() or 'breach' in c.lower() or 'compliance' in c.lower() or 'violated' in c.lower() or 'target' in c.lower()) and 'group' not in c.lower() and 'team' not in c.lower()), all_cols[0] if all_cols else None)
        def_desc = next((c for c in all_cols if 'desc' in c.lower() or 'subject' in c.lower() or 'summary' in c.lower() or 'title' in c.lower()), def_type if def_type else all_cols[0])
        def_agent = next((c for c in all_cols if 'agent' in c.lower() or 'assignee' in c.lower() or 'owner' in c.lower() or 'engineer' in c.lower()), all_cols[0] if all_cols else None)

        team_col = st.sidebar.selectbox("Team / Group Column:", options=all_cols, index=all_cols.index(def_team) if def_team in all_cols else 0)
        agent_col = st.sidebar.selectbox("Agent / Assignee Column:", options=all_cols, index=all_cols.index(def_agent) if def_agent in all_cols else 0)
        source_col = st.sidebar.selectbox("Source / Channel Column:", options=all_cols, index=all_cols.index(def_source) if def_source in all_cols else 0)
        date_col = st.sidebar.selectbox("Date / Timestamp Column:", options=all_cols, index=all_cols.index(def_date) if def_date in all_cols else 0)
        type_col = st.sidebar.selectbox("Ticket Type / Category Column:", options=all_cols, index=all_cols.index(def_type) if def_type in all_cols else 0)
        location_col = st.sidebar.selectbox("Location / Site Column:", options=all_cols, index=all_cols.index(def_loc) if def_loc in all_cols else 0)
        sla_col = st.sidebar.selectbox("SLA Target Status Column:", options=all_cols, index=all_cols.index(def_sla) if def_sla in all_cols else 0)
        desc_col = st.sidebar.selectbox("Description / Subject Column:", options=all_cols, index=all_cols.index(def_desc) if def_desc in all_cols else 0)

        total_rows_loaded = len(df)

        # --- DYNAMIC 50/50 SPLIT TEAM TRACKING ENGINE ---
        active_core_teams_list = []
        other_teams_list = []

        if team_col:
            df[team_col] = df[team_col].fillna("Blank / Unassigned").astype(str).str.strip()
            
            # 1. Get exact value counts of every unique team in descending order
            team_counts = df[team_col].value_counts().reset_index()
            team_counts.columns = ['Team_Name', 'Ticket_Count']
            
            # Filter out generic blank labels from calculations if necessary
            team_counts = team_counts[~team_counts['Team_Name'].isin(["", "Blank / Unassigned"])]
            
            total_unique_teams = len(team_counts)
            
            if total_unique_teams > 0:
                # 2. Calculate the dynamic split index (halfway point, rounded up)
                split_limit = int(np.ceil(total_unique_teams / 2))
                
                # 3. Slit list down the middle numerically 
                top_half_df = team_counts.head(split_limit)
                bottom_half_df = team_counts.tail(total_unique_teams - split_limit)
                
                # Convert tuples for streamlined render looping
                active_core_teams_list = list(top_half_df.itertuples(index=False, name=None))
                other_teams_list = list(bottom_half_df.itertuples(index=False, name=None))
                
                # 4. Map back to main dataframe for downstream visualizations
                top_core_names = set(top_half_df['Team_Name'])
                df['Categorized_Team'] = df[team_col].apply(lambda x: x if x in top_core_names else "Other Teams")
            else:
                df['Categorized_Team'] = "Other Teams"
        else:
            df['Categorized_Team'] = "Column Not Selected"

        # Agent Processing Logic
        if agent_col:
            df[agent_col] = df[agent_col].fillna("Unassigned Agent").astype(str).str.strip()
            unique_agents_count = df[df[agent_col] != "Unassigned Agent"][agent_col].nunique()
        else:
            unique_agents_count = 0

        # High Intel Extractor for Incident vs Request
        if type_col:
            df['Type_Search_Base'] = df[type_col].fillna("Missing Value").astype(str).str.strip()
            is_inc = df['Type_Search_Base'].str.contains("incident|inc|issue|bug|error|fault|sdinc", case=False, na=False)
            is_req = df['Type_Search_Base'].str.contains("request|req|sr|ritm|service|sdsr", case=False, na=False)
            
            df['Ticket_Type_Group'] = "Other Categories"
            df.loc[is_inc, 'Ticket_Type_Group'] = "Incident"
            df.loc[is_req, 'Ticket_Type_Group'] = "Request"
        else:
            df['Ticket_Type_Group'] = "Column Not Selected"

        # SLA Tracking Engine
        if sla_col:
            df['Cleaned_Raw_SLA'] = df[sla_col].fillna("Missing SLA Data").astype(str).str.strip().str.lower()
            
            def advanced_sla_mapper(val):
                if val in ['missing sla data', 'nan', 'none', '', 'null']:
                    return 'Missing SLA Data'
                if val == '1' or val == 'true' or val == 'yes' or any(x in val for x in ["within", "met", "compliant", "achieved", "in sla"]):
                    return "Within SLA"
                if val == '0' or val == 'false' or val == 'no' or any(x in val for x in ["violated", "breached", "missed", "out of sla", "failed"]):
                    return "SLA Violated"
                return None
                
            df['SLA_Group'] = df['Cleaned_Raw_SLA'].apply(advanced_sla_mapper)
        else:
            df['SLA_Group'] = "Column Not Selected"

        # Time Formatting Logic
        if date_col:
            parsed_dates = pd.to_datetime(df[date_col], errors='coerce')
            df['Day'] = parsed_dates.dt.strftime('%Y-%m-%d').fillna("Missing Date")
            df['Week'] = parsed_dates.dt.strftime('%Y-W%V').fillna("Missing Date")
        else:
            df['Day'] = "No Date Column Found"
            df['Week'] = "No Date Column Found"

        # Location Processing Logic
        if location_col:
            df[location_col] = df[location_col].fillna("Blank / Unspecified").astype(str).str.strip()

        # Dynamic Issue / Subject Analytics Tagging Engine
        if desc_col:
            df['Cleaned_Desc'] = df[desc_col].fillna("").astype(str).str.lower()
            
            def tagging_engine(desc_str):
                if any(x in desc_str for x in ["vpn", "pulse", "cisco anyconnect", "forticlient"]):
                    return "VPN Issues"
                elif any(x in desc_str for x in ["battery", "storage", "disk full", "hard drive", "ssd", "space", "ram"]):
                    return "Battery / Storage Issues"
                elif any(x in desc_str for x in ["password", "reset", "unlock", "ad credentials", "login", "credential"]):
                    return "Password / Access Issues"
                elif any(x in desc_str for x in ["outlook", "email", "teams", "o365", "mailbox"]):
                    return "Email & Collaboration Issues"
                elif any(x in desc_str for x in ["printer", "print", "scanner"]):
                    return "Peripherals / Printer Issues"
                elif any(x in desc_str for x in ["sap", "oracle", "database", "erp"]):
                    return "Enterprise Software Apps"
                elif any(x in desc_str for x in ["network", "wifi", "wi-fi", "lan", "internet"]):
                    return "Network Connectivity Issues"
                return "General Hardware & OS Inquiries"

            df['Detected_Issue_Pattern'] = df['Cleaned_Desc'].apply(tagging_engine)
        else:
            df['Detected_Issue_Pattern'] = "Description Column Map Required"

        # --- ROUTING PAGES ---
        if app_page == "Dashboard Visuals":
            
            # --- TOP LEVEL KPI METRICS ---
            st.subheader("⚡ Executive Summary")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric(label="Total Logged Tickets", value=f"{total_rows_loaded:,}")
            with m_col2:
                st.metric(label="Active Core Teams (Top Half)", value=len(active_core_teams_list))
            with m_col3:
                st.metric(label="Assigned Agents", value=f"{unique_agents_count}")
            with m_col4:
                st.metric(label="Other Teams (Bottom Half)", value=len(other_teams_list))

            # --- INTERACTIVE TEAM EXPLORERS (Dynamic 50/50 Split Lists) ---
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                with st.expander("🔍 Click to view Active Core Teams (Highest handling volume half)"):
                    if len(active_core_teams_list) > 0:
                        for team, count in active_core_teams_list:
                            st.write(f"• **{team}** ({count} tickets)")
                    else:
                        st.info("No core teams detected.")

            with exp_col2:
                with st.expander("🔍 Click to view Remaining 'Other Teams' (Lower handling volume half)"):
                    if len(other_teams_list) > 0:
                        for team, count in other_teams_list:
                            st.write(f"• **{team}** ({count} tickets)")
                    else:
                        st.info("No unlisted trailing teams found.")

            # --- VISUALIZATION TABS ---
            st.markdown("---")
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "👤 Agent Performance Count",
                "🏢 Inbound Source Distribution", 
                "📍 Location Volume Performance", 
                "📋 Incident vs Request Analysis",
                "⏱️ SLA Compliance Analysis",
                "📅 Ticket Time-Series Trends"
            ])

            # TAB 1: AGENT WISE TICKET HANDLING COUNT
            with tab1:
                if agent_col:
                    st.write("### Top Ticket Handling Agents")
                    max_agents = st.slider("Select top number of agents to display:", min_value=5, max_value=30, value=15)
                    
                    agent_counts = df[agent_col].value_counts().reset_index()
                    agent_counts.columns = ['Agent Name', 'Tickets Handled']
                    
                    if not agent_counts.empty:
                        fig_agent = px.bar(
                            agent_counts.head(max_agents), 
                            x='Tickets Handled', 
                            y='Agent Name', 
                            orientation='h', 
                            text_auto=True,
                            color='Tickets Handled',
                            color_continuous_scale=px.colors.sequential.Blugrn
                        )
                        fig_agent.update_traces(textfont=dict(weight='bold'), textposition='outside')
                        fig_agent.update_layout(
                            yaxis={'categoryorder':'total ascending'}, 
                            margin=dict(l=20, r=20, t=30, b=20),
                            xaxis_title="Volume of Handled Tickets",
                            yaxis_title=None
                        )
                        st.plotly_chart(fig_agent, use_container_width=True)
                    else:
                        st.warning("No agent information found in this column.")

            # TAB 2: INBOUND SOURCE DISTRIBUTION
            with tab2:
                if source_col:
                    st.write("### Inbound Ticket Channels")
                    df[source_col] = df[source_col].fillna("Unknown Source").astype(str)
                    src_counts = df[source_col].value_counts().reset_index()
                    src_counts.columns = ['Source', 'Tickets']
                    
                    fig_src = px.pie(
                        src_counts, values='Tickets', names='Source',
                        hole=0.4, color_discrete_sequence=INBOUND_SOURCE_PALETTE
                    )
                    fig_src.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(size=14, color='white', weight='bold'))
                    fig_src.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_src, use_container_width=True)

            # TAB 3: LOCATION BASED ANALYSIS
            with tab3:
                if location_col:
                    st.write("### Site Ticket Share Proportions")
                    loc_counts = df[df[location_col] != "Blank / Unspecified"][location_col].value_counts().reset_index()
                    loc_counts.columns = ['Location', 'Tickets']
                    
                    if not loc_counts.empty:
                        fig_loc_pie = px.pie(
                            loc_counts.head(8), values='Tickets', names='Location',
                            hole=0.5, color_discrete_sequence=LOCATION_PALETTE
                        )
                        fig_loc_pie.update_traces(
                            textposition='outside', 
                            textinfo='percent+label',
                            textfont=dict(size=13, color='black', weight='bold'),
                            pull=[0.05 if i == 0 else 0 for i in range(len(loc_counts.head(8)))]
                        )
                        fig_loc_pie.update_layout(
                            margin=dict(l=40, r=40, t=40, b=40),
                            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                        )
                        st.plotly_chart(fig_loc_pie, use_container_width=True)
                    else:
                        st.warning("Location database features empty fields only.")

            # TAB 4: INCIDENT VS REQUEST ANALYSIS
            with tab4:
                if type_col:
                    st.write("### Ticket Category Distribution")
                    filtered_type_df = df[df['Ticket_Type_Group'].isin(["Incident", "Request"])]
                    
                    if not filtered_type_df.empty:
                        type_counts = filtered_type_df['Ticket_Type_Group'].value_counts().reset_index()
                        type_counts.columns = ['Classification Type', 'Ticket Count']
                        
                        fig_type = px.bar(
                            type_counts, x='Classification Type', y='Ticket Count',
                            color='Classification Type', text_auto=True,
                            color_discrete_map={
                                "Incident": "#2563EB", 
                                "Request": "#EC4899"
                            }
                        )
                        fig_type.update_traces(textfont=dict(size=14, color='black', weight='bold'), textposition='outside')
                        fig_type.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None)
                        st.plotly_chart(fig_type, use_container_width=True)
                    else:
                        st.warning("⚠️ No distinct Incidents or Requests discovered inside column row arrays.")

            # TAB 5: SLA COMPLIANCE ANALYSIS
            with tab5:
                if sla_col:
                    st.write("### SLA Target Adherence Performance Summary")
                    filtered_sla_df = df[df['SLA_Group'].isin(["Within SLA", "SLA Violated"])]
                    
                    if not filtered_sla_df.empty:
                        sla_counts = filtered_sla_df['SLA_Group'].value_counts().reset_index()
                        sla_counts.columns = ['SLA Status', 'Ticket Count']
                        
                        fig_sla = px.bar(
                            sla_counts, x='SLA Status', y='Ticket Count',
                            color='SLA Status', text_auto=True,
                            color_discrete_map={
                                "Within SLA": "#10B981", 
                                "SLA Violated": "#F59E0B"
                            }
                        )
                        fig_sla.update_traces(textfont=dict(size=14, color='black', weight='bold'), textposition='outside')
                        fig_sla.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None)
                        st.plotly_chart(fig_sla, use_container_width=True)
                    else:
                        st.warning("⚠️ Column selection misaligned. Please switch the 'SLA Target Status Column' dropdown in the sidebar override configuration panel to pick your real SLA log column field.")

            # TAB 6: TICKET TIME-SERIES TRENDS
            with tab6:
                if date_col:
                    st.write("### Ticket Intake Trends")
                    time_view = st.radio("Select View:", options=["Per Day", "Per Week"], horizontal=True)
                    
                    graph_df = df[df['Day'] != "Missing Date"]
                    
                    if graph_df.empty:
                        st.warning("⚠️ No valid structural timestamps found inside file logs.")
                    else:
                        if time_view == "Per Day":
                            trend_df = graph_df['Day'].value_counts().sort_index().reset_index()
                            trend_df.columns = ['Date', 'Tickets']
                            
                            fig_trend = px.line(
                                trend_df, x='Date', y='Tickets', markers=True, 
                                text='Tickets', title="Daily Ticket Intake Volume"
                            )
                            fig_trend.update_traces(
                                line=dict(color='#06B6D4', width=4),
                                textposition="top center",
                                textfont=dict(size=12, color="black", weight="bold")
                            )
                        else:
                            trend_df = graph_df['Week'].value_counts().sort_index().reset_index()
                            trend_df.columns = ['Week', 'Tickets']
                            
                            fig_trend = px.bar(
                                trend_df, x='Week', y='Tickets', text_auto=True, 
                                color='Week', color_discrete_sequence=LOCATION_PALETTE,
                                title="Weekly Ticket Breakdown Volume"
                            )
                            fig_trend.update_layout(showlegend=False)
                        
                        fig_trend.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))
                        st.plotly_chart(fig_trend, use_container_width=True)

        elif app_page == "Deep-Dive Issue Inventory":
            st.subheader("🔍 Deep-Dive Frequent Issue Inventory Page")
            st.markdown("Identify text patterns from subjects and notes to categorize recurring technical demands.")
            
            st.write("### Frequent Ticket Issue Categories (Total Dataset Overview)")
            total_issue_counts = df['Detected_Issue_Pattern'].value_counts().reset_index()
            total_issue_counts.columns = ['Frequent Ticket Issue Category', 'Total Reported Cases']
            
            fig_issues = px.bar(
                total_issue_counts, x='Total Reported Cases', y='Frequent Ticket Issue Category', 
                orientation='h', text_auto=True,
                color='Frequent Ticket Issue Category',
                color_discrete_sequence=LOCATION_PALETTE
            )
            fig_issues.update_traces(textfont=dict(weight='bold'))
            fig_issues.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_issues, use_container_width=True)
            
            st.markdown("---")
            
            search_query = st.text_input("📝 Live Search Filter Box (Type text here to filter the interactive logs table below):", value="")
            
            if search_query.strip():
                filtered_df = df[df[desc_col].fillna("").astype(str).str.contains(search_query.strip(), case=False, na=False)]
                st.info(f"Filtering interactive table logs down to keyword: '{search_query}' ({len(filtered_df)} matches found)")
            else:
                filtered_df = df
                
            st.write("### 📋 Filtered Complete Searchable Inventory Log")
            if not filtered_df.empty:
                display_cols = [c for c in [date_col, team_col, agent_col, type_col, location_col, sla_col, desc_col] if c is not None]
                
                st.dataframe(
                    filtered_df[['Detected_Issue_Pattern'] + display_cols], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning("No tabular matches found matching your typed query criteria.")

    except Exception as e:
        st.error(f"Dashboard unexpected rendering error: {e}")
else:
    st.info("👋 System ready. Please drop your IT support logs Excel file in the sidebar config to populate the dashboard layouts.")
