"""
Interactive Staff Scheduling Optimisation Dashboard
Streamlit app with Plotly visualizations for exploring data and optimisation results.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pulp import *
import time
import io
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

# Page configuration
st.set_page_config(
    page_title="Staff Scheduling Optimiser",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #§;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


class StreamlitSchedulingOptimiser:
    """Streamlit-integrated scheduling optimiser."""

    def __init__(self, df):
        self.df = df
        self.staff_ids = sorted(df['Staff ID'].unique())
        self.job_ids = sorted(df['Job_ID'].unique())
        self.model = None
        self.assignments = None
        self.results_df = None

    def build_and_solve(self, cost_weight, satisfaction_weight, skill_weight,
                       min_skill_match, max_jobs_per_staff, time_limit):
        """Build and solve the optimisation model with progress updates."""

        # Progress container
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Step 1: Build model
        status_text.text("Building optimisation model...")
        progress_bar.progress(20)

        self.model = LpProblem("Staff_Scheduling", LpMinimize)

        # Normalize data
        max_cost = self.df['Total_Cost'].max()
        max_satisfaction = self.df['Satisfaction Score'].max()

        # Decision variables
        self.assignments = LpVariable.dicts("assign",
                                           ((s, j) for s in self.staff_ids for j in self.job_ids),
                                           cat='Binary')

        # Valid assignments
        valid_assignments = self.df[self.df['Skill_Match'] >= min_skill_match].copy()
        valid_pairs = set(zip(valid_assignments['Staff ID'], valid_assignments['Job_ID']))

        progress_bar.progress(40)
        status_text.text(f"Valid assignments: {len(valid_pairs):,}")

        # Objective function
        objective = lpSum([
            self.assignments[s, j] * (
                cost_weight * (self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Total_Cost'].values[0] / max_cost)
                - satisfaction_weight * (self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Satisfaction Score'].values[0] / max_satisfaction)
                - skill_weight * self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Skill_Match'].values[0]
            )
            for (s, j) in valid_pairs
        ])

        self.model += objective

        progress_bar.progress(60)
        status_text.text("Adding constraints...")

        # Constraints
        for j in self.job_ids:
            valid_staff = [s for (s, job) in valid_pairs if job == j]
            if valid_staff:
                self.model += lpSum([self.assignments[s, j] for s in valid_staff]) == 1

        if max_jobs_per_staff:
            for s in self.staff_ids:
                valid_jobs = [j for (staff, j) in valid_pairs if staff == s]
                if valid_jobs:
                    self.model += lpSum([self.assignments[s, j] for j in valid_jobs]) <= max_jobs_per_staff

        for s in self.staff_ids:
            for j in self.job_ids:
                if (s, j) not in valid_pairs:
                    self.model += self.assignments[s, j] == 0

        progress_bar.progress(80)
        status_text.text("Solving optimisation problem...")

        # Solve
        solver = PULP_CBC_CMD(msg=0, timeLimit=time_limit)
        start_time = time.time()
        self.model.solve(solver)
        solve_time = time.time() - start_time

        progress_bar.progress(100)
        status_text.text(f"✓ Solved in {solve_time:.2f} seconds!")

        # Extract results
        results = []
        for s in self.staff_ids:
            for j in self.job_ids:
                if value(self.assignments[s, j]) == 1:
                    assignment_data = self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)].iloc[0]
                    results.append(assignment_data)

        self.results_df = pd.DataFrame(results)

        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

        return self.results_df, solve_time, LpStatus[self.model.status]


@st.cache_data
def load_data(file_path):
    """Load and cache the dataset."""
    df = pd.read_csv(file_path)
    return df


def create_eda_visualizations(df):
    """Create exploratory data analysis visualizations."""

    st.subheader("Exploratory Data Analysis")

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Cost Analysis", "Quality Metrics", "Geographic", "Staff Analysis"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Cost distribution
            fig = px.histogram(df, x='Total_Cost', nbins=50,
                             title='Distribution of Total Assignment Costs',
                             labels={'Total_Cost': 'Total Cost ($)'},
                             color_discrete_sequence=['steelblue'])
            fig.add_vline(x=df['Total_Cost'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: ${df['Total_Cost'].mean():.2f}")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Cost breakdown pie chart
            cost_breakdown = pd.DataFrame({
                'Component': ['Travel Cost', 'Labour Cost'],
                'Amount': [df['Travel_Cost'].sum(), df['Labour_Cost'].sum()]
            })
            fig = px.pie(cost_breakdown, values='Amount', names='Component',
                        title='Cost Breakdown (Total Dataset)',
                        color_discrete_sequence=['#ff9999', '#66b3ff'])
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Distance vs Travel Cost
            fig = px.scatter(df, x='Distance_km', y='Travel_Cost',
                           title='Distance vs Travel Cost',
                           labels={'Distance_km': 'Distance (km)', 'Travel_Cost': 'Travel Cost ($)'},
                           opacity=0.5, trendline="ols")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Job hours distribution
            fig = px.box(df, y='Job_Hours', title='Job Hours Distribution',
                        color_discrete_sequence=['teal'])
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Satisfaction vs Skill Match
            fig = px.scatter(df, x='Skill_Match', y='Satisfaction Score',
                           color='Total_Cost', size='Job_Hours',
                           title='Skill Match vs Satisfaction (sized by hours, colored by cost)',
                           labels={'Skill_Match': 'Skill Match', 'Satisfaction Score': 'Satisfaction Score'},
                           color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Skill match distribution
            fig = px.histogram(df, x='Skill_Match', nbins=50,
                             title='Skill Match Distribution',
                             labels={'Skill_Match': 'Skill Match Score'},
                             color_discrete_sequence=['green'])
            fig.add_vline(x=df['Skill_Match'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: {df['Skill_Match'].mean():.2f}")
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Priority distribution
            priority_counts = df.groupby('Job_Priority')['Job_ID'].nunique().reset_index()
            priority_counts.columns = ['Priority', 'Count']
            fig = px.bar(priority_counts, x='Priority', y='Count',
                        title='Job Distribution by Priority',
                        labels={'Count': 'Number of Jobs'},
                        color='Priority', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Satisfaction distribution
            fig = px.histogram(df, x='Satisfaction Score', nbins=50,
                             title='Staff Satisfaction Distribution',
                             labels={'Satisfaction Score': 'Satisfaction Score'},
                             color_discrete_sequence=['orange'])
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            # Jobs by location
            location_counts = df.groupby('Job_Location')['Job_ID'].nunique().reset_index()
            location_counts.columns = ['Location', 'Count']
            location_counts = location_counts.sort_values('Count', ascending=True).tail(15)
            fig = px.bar(location_counts, x='Count', y='Location', orientation='h',
                        title='Top 15 Locations by Job Count',
                        labels={'Count': 'Number of Jobs'},
                        color='Count', color_continuous_scale='Teal')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Average cost by location
            location_cost = df.groupby('Job_Location')['Total_Cost'].mean().reset_index()
            location_cost.columns = ['Location', 'Avg_Cost']
            location_cost = location_cost.sort_values('Avg_Cost', ascending=True).tail(15)
            fig = px.bar(location_cost, x='Avg_Cost', y='Location', orientation='h',
                        title='Top 15 Locations by Average Cost',
                        labels={'Avg_Cost': 'Average Cost ($)'},
                        color='Avg_Cost', color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)

        # Distance distribution
        fig = px.histogram(df, x='Distance_km', nbins=50,
                         title='Distance Distribution',
                         labels={'Distance_km': 'Distance (km)'},
                         color_discrete_sequence=['purple'])
        fig.add_vline(x=df['Distance_km'].mean(), line_dash="dash", line_color="red",
                     annotation_text=f"Mean: {df['Distance_km'].mean():.1f} km")
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        col1, col2 = st.columns(2)

        # Get unique staff data
        staff_data = df.groupby('Staff ID')[['Years of Experience', 'Cost_per_Hour',
                                             'Satisfaction Score', 'Absenteeism (Days)']].first().reset_index()

        with col1:
            # Experience vs Cost per Hour
            fig = px.scatter(staff_data, x='Years of Experience', y='Cost_per_Hour',
                           title='Staff Experience vs Hourly Cost',
                           labels={'Years of Experience': 'Years of Experience',
                                  'Cost_per_Hour': 'Cost per Hour ($)'},
                           color='Satisfaction Score', size='Absenteeism (Days)',
                           color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Absenteeism distribution
            fig = px.histogram(staff_data, x='Absenteeism (Days)', nbins=10,
                             title='Staff Absenteeism Distribution',
                             labels={'Absenteeism (Days)': 'Absenteeism (Days)'},
                             color_discrete_sequence=['coral'])
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Experience distribution
            fig = px.histogram(staff_data, x='Years of Experience', nbins=20,
                             title='Staff Experience Distribution',
                             labels={'Years of Experience': 'Years of Experience'},
                             color_discrete_sequence=['skyblue'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Cost per hour distribution
            fig = px.box(staff_data, y='Cost_per_Hour',
                        title='Staff Hourly Cost Distribution',
                        labels={'Cost_per_Hour': 'Cost per Hour ($)'},
                        color_discrete_sequence=['lightcoral'])
            st.plotly_chart(fig, use_container_width=True)


def create_results_visualizations(results_df, baseline_df, solve_time):
    """Create optimisation results visualizations."""

    st.subheader("Optimisation Results")

    # Calculate metrics
    total_cost = results_df['Total_Cost'].sum()
    travel_cost = results_df['Travel_Cost'].sum()
    labour_cost = results_df['Labour_Cost'].sum()
    avg_satisfaction = results_df['Satisfaction Score'].mean()
    avg_skill = results_df['Skill_Match'].mean()
    avg_distance = results_df['Distance_km'].mean()

    baseline_cost = baseline_df['Total_Cost'].sum()
    baseline_satisfaction = baseline_df['Satisfaction Score'].mean()
    baseline_skill = baseline_df['Skill_Match'].mean()

    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Cost", f"${total_cost:,.2f}",
                 f"-${baseline_cost - total_cost:,.2f}" if baseline_cost > total_cost else f"+${total_cost - baseline_cost:,.2f}",
                 delta_color="inverse")

    with col2:
        st.metric("Avg Satisfaction", f"{avg_satisfaction:.2f}",
                 f"+{avg_satisfaction - baseline_satisfaction:.2f}")

    with col3:
        st.metric("Avg Skill Match", f"{avg_skill:.1%}",
                 f"+{(avg_skill - baseline_skill)*100:.1f}%")

    with col4:
        st.metric("Solve Time", f"{solve_time:.2f}s")

    st.markdown("---")

    # Create tabs for results
    tab1, tab2, tab3, tab4 = st.tabs(["Cost Analysis", "Quality Metrics", "Workload", "Comparison"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Cost breakdown pie chart
            cost_data = pd.DataFrame({
                'Component': ['Travel Cost', 'Labour Cost'],
                'Amount': [travel_cost, labour_cost]
            })
            fig = px.pie(cost_data, values='Amount', names='Component',
                        title=f'Optimized Cost Breakdown (Total: ${total_cost:,.2f})',
                        color_discrete_sequence=['#ff9999', '#66b3ff'],
                        hole=0.4)
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Cost per job distribution
            fig = px.histogram(results_df, x='Total_Cost', nbins=30,
                             title='Optimized Cost Distribution',
                             labels={'Total_Cost': 'Total Cost per Job ($)'},
                             color_discrete_sequence=['steelblue'])
            fig.add_vline(x=results_df['Total_Cost'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: ${results_df['Total_Cost'].mean():.2f}")
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Top 10 most expensive assignments
            top_expensive = results_df.nlargest(10, 'Total_Cost')[['Staff ID', 'Job_ID', 'Job_Location', 'Total_Cost']]
            fig = px.bar(top_expensive, x='Total_Cost', y='Job_ID', orientation='h',
                        title='Top 10 Most Expensive Assignments',
                        labels={'Total_Cost': 'Total Cost ($)', 'Job_ID': 'Job ID'},
                        color='Total_Cost', color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Cost by location
            location_cost = results_df.groupby('Job_Location')['Total_Cost'].sum().reset_index()
            location_cost = location_cost.sort_values('Total_Cost', ascending=False).head(10)
            fig = px.bar(location_cost, x='Job_Location', y='Total_Cost',
                        title='Top 10 Locations by Total Cost',
                        labels={'Total_Cost': 'Total Cost ($)', 'Job_Location': 'Location'},
                        color='Total_Cost', color_continuous_scale='Oranges')
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Skill match distribution
            fig = px.histogram(results_df, x='Skill_Match', nbins=30,
                             title='Skill Match Distribution (Optimized)',
                             labels={'Skill_Match': 'Skill Match Score'},
                             color_discrete_sequence=['green'])
            fig.add_vline(x=results_df['Skill_Match'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: {results_df['Skill_Match'].mean():.2%}")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Satisfaction vs Skill Match
            fig = px.scatter(results_df, x='Skill_Match', y='Satisfaction Score',
                           color='Total_Cost', size='Job_Hours',
                           title='Optimized: Skill Match vs Satisfaction',
                           labels={'Skill_Match': 'Skill Match', 'Satisfaction Score': 'Satisfaction'},
                           color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            # Priority fulfillment
            priority_counts = results_df.groupby('Job_Priority').size().reset_index()
            priority_counts.columns = ['Priority', 'Count']
            fig = px.bar(priority_counts, x='Priority', y='Count',
                        title='Jobs Assigned by Priority',
                        labels={'Count': 'Number of Jobs'},
                        color='Priority', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Distance distribution
            fig = px.histogram(results_df, x='Distance_km', nbins=30,
                             title='Travel Distance Distribution',
                             labels={'Distance_km': 'Distance (km)'},
                             color_discrete_sequence=['purple'])
            fig.add_vline(x=results_df['Distance_km'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: {results_df['Distance_km'].mean():.1f} km")
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Workload distribution
        workload = results_df.groupby('Staff ID').size().reset_index()
        workload.columns = ['Staff ID', 'Jobs_Assigned']

        col1, col2 = st.columns(2)

        with col1:
            # Workload histogram
            fig = px.histogram(workload, x='Jobs_Assigned', nbins=20,
                             title='Workload Distribution Across Staff',
                             labels={'Jobs_Assigned': 'Jobs per Staff Member'},
                             color_discrete_sequence=['teal'])
            fig.add_vline(x=workload['Jobs_Assigned'].mean(), line_dash="dash", line_color="red",
                         annotation_text=f"Mean: {workload['Jobs_Assigned'].mean():.2f}")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Top loaded staff
            top_loaded = workload.nlargest(20, 'Jobs_Assigned')
            fig = px.bar(top_loaded, x='Jobs_Assigned', y='Staff ID', orientation='h',
                        title='Top 20 Staff by Workload',
                        labels={'Jobs_Assigned': 'Number of Jobs', 'Staff ID': 'Staff ID'},
                        color='Jobs_Assigned', color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)

        # Location distribution
        location_counts = results_df.groupby('Job_Location').size().reset_index()
        location_counts.columns = ['Location', 'Count']
        location_counts = location_counts.sort_values('Count', ascending=False).head(15)
        fig = px.bar(location_counts, x='Location', y='Count',
                    title='Top 15 Locations by Number of Assignments',
                    labels={'Count': 'Number of Assignments'},
                    color='Count', color_continuous_scale='Plasma')
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Optimisation vs Baseline (Random Assignment)")

        # Comparison metrics
        col1, col2, col3 = st.columns(3)

        cost_improvement = ((baseline_cost - total_cost) / baseline_cost) * 100
        satisfaction_improvement = ((avg_satisfaction - baseline_satisfaction) / baseline_satisfaction) * 100
        skill_improvement = ((avg_skill - baseline_skill) / baseline_skill) * 100

        with col1:
            st.metric("Cost Reduction", f"{cost_improvement:.1f}%",
                     f"${baseline_cost - total_cost:,.2f} saved")

        with col2:
            st.metric("Satisfaction Gain", f"{satisfaction_improvement:.1f}%",
                     f"+{avg_satisfaction - baseline_satisfaction:.2f} points")

        with col3:
            st.metric("Skill Match Gain", f"{skill_improvement:.1f}%",
                     f"+{(avg_skill - baseline_skill)*100:.1f} percentage points")

        # Comparison charts
        col1, col2 = st.columns(2)

        with col1:
            # Cost comparison
            comparison_data = pd.DataFrame({
                'Method': ['Baseline', 'Optimized'],
                'Total Cost': [baseline_cost, total_cost],
                'Travel Cost': [baseline_df['Travel_Cost'].sum(), travel_cost],
                'Labour Cost': [baseline_df['Labour_Cost'].sum(), labour_cost]
            })

            fig = go.Figure(data=[
                go.Bar(name='Travel Cost', x=comparison_data['Method'], y=comparison_data['Travel Cost']),
                go.Bar(name='Labour Cost', x=comparison_data['Method'], y=comparison_data['Labour Cost'])
            ])
            fig.update_layout(barmode='stack', title='Cost Comparison: Baseline vs Optimized',
                            yaxis_title='Cost ($)')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Quality metrics comparison
            quality_data = pd.DataFrame({
                'Metric': ['Satisfaction', 'Skill Match'],
                'Baseline': [baseline_satisfaction, baseline_skill * 5],  # Scale skill to 0-5
                'Optimized': [avg_satisfaction, avg_skill * 5]
            })

            fig = go.Figure(data=[
                go.Bar(name='Baseline', x=quality_data['Metric'], y=quality_data['Baseline']),
                go.Bar(name='Optimized', x=quality_data['Metric'], y=quality_data['Optimized'])
            ])
            fig.update_layout(barmode='group', title='Quality Metrics: Baseline vs Optimized',
                            yaxis_title='Score (0-5)')
            st.plotly_chart(fig, use_container_width=True)


def main():
    """Main Streamlit app."""

    # Header
    st.markdown('<div class="main-header">📊 Staff Scheduling Optimisation Dashboard</div>',
                unsafe_allow_html=True)

    st.markdown("""
    This interactive dashboard allows you to explore the scheduling dataset and run optimisation
    with custom parameters to assign engineering staff to jobs across the country.
    """)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Data loading
        st.subheader("📁 Data Source")
        data_source = st.radio("Choose data source:",
                              ["Use existing dataset", "Upload new dataset"])

        if data_source == "Upload new dataset":
            uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
            if uploaded_file:
                df = pd.read_csv(uploaded_file)
                st.success(f"Loaded {len(df)} rows")
            else:
                st.info("Please upload a CSV file")
                st.stop()
        else:
            try:
                df = load_data(os.path.join(base_dir, 'extended_staff_scheduling_dataset.csv'))
                st.success(f"Loaded {len(df):,} rows")
            except Exception as e:
                st.error(f"Error loading data: {e}")
                st.stop()

        st.markdown("---")

        # Optimisation parameters
        st.subheader("Optimisation Parameters")

        st.markdown("**Objective Weights** (must sum to 1.0)")
        cost_weight = st.slider("Cost Minimization", 0.0, 1.0, 0.6, 0.05,
                               help="Weight for minimizing total cost")
        satisfaction_weight = st.slider("Satisfaction Maximization", 0.0, 1.0, 0.2, 0.05,
                                       help="Weight for maximizing staff satisfaction")
        skill_weight = st.slider("Skill Match Maximization", 0.0, 1.0, 0.2, 0.05,
                                help="Weight for maximizing skill match")

        # Normalize weights
        total_weight = cost_weight + satisfaction_weight + skill_weight
        if total_weight > 0:
            cost_weight /= total_weight
            satisfaction_weight /= total_weight
            skill_weight /= total_weight

        st.info(f"Normalized: Cost={cost_weight:.2f}, Satisfaction={satisfaction_weight:.2f}, Skill={skill_weight:.2f}")

        st.markdown("**Constraints**")
        min_skill_match = st.slider("Minimum Skill Match", 0.0, 1.0, 0.5, 0.05,
                                   help="Minimum acceptable skill match (0-1)")

        max_jobs_enabled = st.checkbox("Limit jobs per staff", value=True)
        if max_jobs_enabled:
            max_jobs_per_staff = st.number_input("Max jobs per staff", 1, 20, 5,
                                                help="Maximum jobs assigned to one staff member")
        else:
            max_jobs_per_staff = None

        time_limit = st.number_input("Solver time limit (seconds)", 10, 600, 300,
                                    help="Maximum time for solver")

        st.markdown("---")

        # Action buttons
        run_optimisation = st.button("Run Optimisation", type="primary", use_container_width=True)

    # Main content
    # Display dataset info
    with st.expander("📋 Dataset Information", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Rows", f"{len(df):,}")
        with col2:
            st.metric("Staff Members", f"{df['Staff ID'].nunique():,}")
        with col3:
            st.metric("Jobs", f"{df['Job_ID'].nunique():,}")
        with col4:
            st.metric("Locations", f"{df['Job_Location'].nunique():,}")

        st.markdown("**Dataset Preview**")
        st.dataframe(df.head(100), use_container_width=True)

        st.markdown("**Summary Statistics**")
        st.dataframe(df.describe(), use_container_width=True)

    # Create tabs
    tab1, tab2 = st.tabs(["Data Exploration", "Optimisation Results"])

    with tab1:
        create_eda_visualizations(df)

    with tab2:
        if 'optimisation_results' not in st.session_state and not run_optimisation:
            st.info("👈 Configure parameters in the sidebar and click 'Run Optimisation' to see results")
        else:
            if run_optimisation:
                with st.spinner("Running optimisation..."):
                    # Create baseline (random valid assignment)
                    baseline_assignments = []
                    for job in df['Job_ID'].unique():
                        valid_staff = df[(df['Job_ID'] == job) & (df['Skill_Match'] >= min_skill_match)]['Staff ID'].tolist()
                        if valid_staff:
                            random_staff = np.random.choice(valid_staff)
                            assignment = df[(df['Staff ID'] == random_staff) & (df['Job_ID'] == job)].iloc[0]
                            baseline_assignments.append(assignment)

                    baseline_df = pd.DataFrame(baseline_assignments)

                    # Run optimisation
                    optimiser = StreamlitSchedulingOptimiser(df)
                    results_df, solve_time, status = optimiser.build_and_solve(
                        cost_weight, satisfaction_weight, skill_weight,
                        min_skill_match, max_jobs_per_staff, time_limit
                    )

                    # Store in session state
                    st.session_state['optimisation_results'] = results_df
                    st.session_state['baseline_results'] = baseline_df
                    st.session_state['solve_time'] = solve_time
                    st.session_state['solver_status'] = status

                    if status == 'Optimal':
                        st.success(f"Optimisation complete! Solver status: {status}")
                    else:
                        st.warning(f"⚠️ Optimisation completed with status: {status}")

            # Display results
            if 'optimisation_results' in st.session_state:
                results_df = st.session_state['optimisation_results']
                baseline_df = st.session_state['baseline_results']
                solve_time = st.session_state['solve_time']

                # Create visualizations
                create_results_visualizations(results_df, baseline_df, solve_time)

                # Download section
                st.markdown("---")
                st.subheader("📥 Download Results")

                col1, col2, col3 = st.columns(3)

                with col1:
                    # Download optimized schedule
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download Optimized Schedule (CSV)",
                        data=csv,
                        file_name="optimized_schedule.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with col2:
                    # Download summary report
                    summary = f"""
STAFF SCHEDULING OPTIMIsATION REPORT
=====================================

Optimisation Parameters:
- Cost Weight: {cost_weight:.2f}
- Satisfaction Weight: {satisfaction_weight:.2f}
- Skill Weight: {skill_weight:.2f}
- Min Skill Match: {min_skill_match:.2f}
- Max Jobs per Staff: {max_jobs_per_staff if max_jobs_per_staff else 'No limit'}
- Solver Time Limit: {time_limit}s

Results:
- Solver Status: {st.session_state['solver_status']}
- Solve Time: {solve_time:.2f}s
- Jobs Assigned: {len(results_df):,}
- Total Cost: ${results_df['Total_Cost'].sum():,.2f}
- Travel Cost: ${results_df['Travel_Cost'].sum():,.2f}
- Labour Cost: ${results_df['Labour_Cost'].sum():,.2f}
- Avg Satisfaction: {results_df['Satisfaction Score'].mean():.2f}
- Avg Skill Match: {results_df['Skill_Match'].mean():.2%}
- Avg Distance: {results_df['Distance_km'].mean():.1f} km

Baseline Comparison:
- Cost Reduction: {((baseline_df['Total_Cost'].sum() - results_df['Total_Cost'].sum()) / baseline_df['Total_Cost'].sum()) * 100:.2f}%
- Satisfaction Gain: {((results_df['Satisfaction Score'].mean() - baseline_df['Satisfaction Score'].mean()) / baseline_df['Satisfaction Score'].mean()) * 100:.2f}%
- Skill Match Gain: {((results_df['Skill_Match'].mean() - baseline_df['Skill_Match'].mean()) / baseline_df['Skill_Match'].mean()) * 100:.2f}%
"""
                    st.download_button(
                        label="📊 Download Summary Report (TXT)",
                        data=summary,
                        file_name="optimisation_report.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                with col3:
                    # Download baseline for comparison
                    csv_baseline = baseline_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download Baseline Schedule (CSV)",
                        data=csv_baseline,
                        file_name="baseline_schedule.csv",
                        mime="text/csv",
                        use_container_width=True
                    )


if __name__ == "__main__":
    main()
