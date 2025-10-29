"""
Staff Scheduling Optimization Model
This module implements a Mixed Integer Linear Programming (MILP) model
to optimize engineering staff assignment to jobs across the country.

Objectives:
- Minimize total cost (travel + labor)
- Maximize staff satisfaction
- Maximize skill match quality

Constraints:
- Each job assigned to exactly one staff member
- Staff workload limits
- Minimum skill match thresholds
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pulp import *
import warnings
import os
warnings.filterwarnings('ignore')

base_dir = os.path.dirname(os.path.abspath(__file__))

# Set visualization style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


class StaffSchedulingOptimizer:
    """
    A comprehensive scheduling optimizer for engineering staff assignment.
    """

    def __init__(self, data_path):
        """Initialize the optimizer with dataset path."""
        self.data_path = data_path
        self.df = None
        self.staff_ids = None
        self.job_ids = None
        self.model = None
        self.assignments = None
        self.results = None

    def load_and_clean_data(self):
        """Load and clean the dataset."""
        print("STEP 1: DATA LOADING & CLEANING")

        # Load data
        self.df = pd.read_csv(self.data_path)
        print(f"\n✓ Loaded dataset: {self.df.shape[0]} rows × {self.df.shape[1]} columns")

        # Check for missing values
        missing = self.df.isnull().sum()
        if missing.sum() > 0:
            print(f"\n⚠ Missing values found:")
            print(missing[missing > 0])
            self.df = self.df.dropna()
            print(f"✓ Dropped rows with missing values. New shape: {self.df.shape}")
        else:
            print("\n✓ No missing values found")

        # Check for duplicates
        duplicates = self.df.duplicated().sum()
        if duplicates > 0:
            print(f"\n⚠ Found {duplicates} duplicate rows")
            self.df = self.df.drop_duplicates()
            print(f"✓ Removed duplicates. New shape: {self.df.shape}")
        else:
            print("\n✓ No duplicate rows found")

        # Validate data types and ranges
        print("\n✓ Data validation:")
        print(f"  - Satisfaction scores: [{self.df['Satisfaction Score'].min():.2f}, {self.df['Satisfaction Score'].max():.2f}]")
        print(f"  - Skill match: [{self.df['Skill_Match'].min():.2f}, {self.df['Skill_Match'].max():.2f}]")
        print(f"  - Job priority: [{self.df['Job_Priority'].min()}, {self.df['Job_Priority'].max()}]")

        # Extract unique staff and jobs
        self.staff_ids = sorted(self.df['Staff ID'].unique())
        self.job_ids = sorted(self.df['Job_ID'].unique())

        print(f"\n✓ Dataset contains {len(self.staff_ids)} staff members and {len(self.job_ids)} jobs")

        return self.df

    def exploratory_analysis(self):
        """Perform exploratory data analysis."""
        print("STEP 2: EXPLORATORY DATA ANALYSIS")
        # Summary statistics
        print("\n📊 Summary Statistics:")
        print(self.df[['Travel_Cost', 'Labour_Cost', 'Total_Cost',
                       'Satisfaction Score', 'Skill_Match', 'Distance_km']].describe())

        # Staff analysis
        staff_summary = self.df.groupby('Staff ID').agg({
            'Years of Experience': 'first',
            'Satisfaction Score': 'first',
            'Absenteeism (Days)': 'first',
            'Cost_per_Hour': 'first'
        }).describe()

        print("\n👥 Staff Profile Summary:")
        print(staff_summary.T)

        # Job analysis
        job_summary = self.df.groupby('Job_ID').agg({
            'Job_Location': 'first',
            'Job_Priority': 'first',
            'Job_Hours': 'first',
            'Skill_Match': 'mean',
            'Total_Cost': 'mean'
        })

        print("\n💼 Job Summary (first 10 jobs):")
        print(job_summary.head(10))

        # Location analysis
        location_stats = self.df.groupby('Job_Location').agg({
            'Job_ID': 'nunique',
            'Distance_km': 'mean',
            'Travel_Cost': 'mean'
        }).sort_values('Job_ID', ascending=False)

        print("\n📍 Jobs by Location:")
        print(location_stats)

        return {
            'staff_summary': staff_summary,
            'job_summary': job_summary,
            'location_stats': location_stats
        }

    def create_visualizations(self):
        """Create exploratory visualizations."""
        print("\n📈 Generating visualizations...")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Staff Scheduling Dataset - Exploratory Analysis', fontsize=16, fontweight='bold')

        # 1. Cost distribution
        axes[0, 0].hist(self.df['Total_Cost'], bins=50, color='steelblue', edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('Total Cost ($)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Distribution of Total Assignment Costs')
        axes[0, 0].axvline(self.df['Total_Cost'].mean(), color='red', linestyle='--', label=f'Mean: ${self.df["Total_Cost"].mean():.2f}')
        axes[0, 0].legend()

        # 2. Satisfaction vs Skill Match
        scatter = axes[0, 1].scatter(self.df['Skill_Match'], self.df['Satisfaction Score'],
                                     c=self.df['Total_Cost'], cmap='RdYlGn_r', alpha=0.5, s=20)
        axes[0, 1].set_xlabel('Skill Match')
        axes[0, 1].set_ylabel('Satisfaction Score')
        axes[0, 1].set_title('Skill Match vs Satisfaction (colored by cost)')
        plt.colorbar(scatter, ax=axes[0, 1], label='Total Cost')

        # 3. Distance vs Travel Cost
        axes[0, 2].scatter(self.df['Distance_km'], self.df['Travel_Cost'], alpha=0.3, s=10)
        axes[0, 2].set_xlabel('Distance (km)')
        axes[0, 2].set_ylabel('Travel Cost ($)')
        axes[0, 2].set_title('Distance vs Travel Cost')

        # 4. Jobs by location
        location_counts = self.df.groupby('Job_Location')['Job_ID'].nunique().sort_values(ascending=False).head(10)
        axes[1, 0].barh(location_counts.index, location_counts.values, color='teal')
        axes[1, 0].set_xlabel('Number of Jobs')
        axes[1, 0].set_title('Top 10 Locations by Job Count')
        axes[1, 0].invert_yaxis()

        # 5. Priority distribution
        priority_counts = self.df.groupby('Job_Priority')['Job_ID'].nunique()
        axes[1, 1].bar(priority_counts.index, priority_counts.values, color='coral', edgecolor='black')
        axes[1, 1].set_xlabel('Job Priority')
        axes[1, 1].set_ylabel('Number of Jobs')
        axes[1, 1].set_title('Job Distribution by Priority')
        axes[1, 1].set_xticks(range(1, 6))

        # 6. Experience vs Cost per Hour
        staff_data = self.df.groupby('Staff ID')[['Years of Experience', 'Cost_per_Hour']].first()
        axes[1, 2].scatter(staff_data['Years of Experience'], staff_data['Cost_per_Hour'],
                          alpha=0.6, color='purple', s=50)
        axes[1, 2].set_xlabel('Years of Experience')
        axes[1, 2].set_ylabel('Cost per Hour ($)')
        axes[1, 2].set_title('Staff Experience vs Hourly Cost')

        plt.tight_layout()
        plt.savefig(os.path.join(base_dir, 'eda_visualizations.png'), dpi=300, bbox_inches='tight')
        print("✓ Saved visualizations to 'eda_visualizations.png'")
        plt.close()

    def build_optimization_model(self,
                                  cost_weight=0.6,
                                  satisfaction_weight=0.2,
                                  skill_weight=0.2,
                                  min_skill_match=0.5,
                                  max_jobs_per_staff=None):
        """
        Build the MILP optimization model.

        Parameters:
        -----------
        cost_weight : float
            Weight for cost minimization (0-1)
        satisfaction_weight : float
            Weight for satisfaction maximization (0-1)
        skill_weight : float
            Weight for skill match maximization (0-1)
        min_skill_match : float
            Minimum acceptable skill match (0-1)
        max_jobs_per_staff : int
            Maximum jobs per staff member (None = no limit)
        """
        print("STEP 3: BUILDING OPTIMIZATION MODEL")

        print("\n🎯 Optimization Objective:")
        print(f"  Multi-objective function with weights:")
        print(f"  - Cost minimization: {cost_weight:.1%}")
        print(f"  - Satisfaction maximization: {satisfaction_weight:.1%}")
        print(f"  - Skill match maximization: {skill_weight:.1%}")

        print("\n📋 Constraints:")
        print(f"  - Each job assigned to exactly ONE staff member")
        print(f"  - Minimum skill match: {min_skill_match:.0%}")
        if max_jobs_per_staff:
            print(f"  - Maximum jobs per staff: {max_jobs_per_staff}")
        else:
            print(f"  - No workload limit per staff")

        # Initialize the model
        self.model = LpProblem("Staff_Scheduling_Optimization", LpMinimize)

        # Normalize the data for multi-objective optimization
        max_cost = self.df['Total_Cost'].max()
        max_satisfaction = self.df['Satisfaction Score'].max()

        # Decision variables: x[i,j] = 1 if staff i is assigned to job j, 0 otherwise
        self.assignments = LpVariable.dicts("assign",
                                           ((s, j) for s in self.staff_ids for j in self.job_ids),
                                           cat='Binary')

        # Filter valid assignments (pre-filtering based on skill match)
        valid_assignments = self.df[self.df['Skill_Match'] >= min_skill_match].copy()
        valid_pairs = set(zip(valid_assignments['Staff ID'], valid_assignments['Job_ID']))

        print(f"\n✓ Valid assignment possibilities: {len(valid_pairs):,} out of {len(self.staff_ids) * len(self.job_ids):,}")

        # Objective function: Minimize cost while maximizing satisfaction and skill match
        # We convert maximization to minimization by using negative values
        objective = lpSum([
            self.assignments[s, j] * (
                cost_weight * (self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Total_Cost'].values[0] / max_cost)
                - satisfaction_weight * (self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Satisfaction Score'].values[0] / max_satisfaction)
                - skill_weight * self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)]['Skill_Match'].values[0]
            )
            for (s, j) in valid_pairs
        ])

        self.model += objective, "Multi_Objective_Function"

        # Constraint 1: Each job must be assigned to exactly one staff member
        for j in self.job_ids:
            valid_staff_for_job = [s for (s, job) in valid_pairs if job == j]
            if valid_staff_for_job:
                self.model += lpSum([self.assignments[s, j] for s in valid_staff_for_job]) == 1, f"Job_{j}_Assignment"

        # Constraint 2: Maximum jobs per staff member (if specified)
        if max_jobs_per_staff:
            for s in self.staff_ids:
                valid_jobs_for_staff = [j for (staff, j) in valid_pairs if staff == s]
                if valid_jobs_for_staff:
                    self.model += lpSum([self.assignments[s, j] for j in valid_jobs_for_staff]) <= max_jobs_per_staff, f"Staff_{s}_Workload"

        # Constraint 3: Invalid assignments (skill match too low) must be zero
        for s in self.staff_ids:
            for j in self.job_ids:
                if (s, j) not in valid_pairs:
                    self.model += self.assignments[s, j] == 0, f"Invalid_{s}_{j}"

        print(f"✓ Model built successfully")
        print(f"  - Variables: {len(self.assignments):,}")
        print(f"  - Constraints: {len(self.model.constraints):,}")

    def solve_optimization(self):
        """Solve the optimization problem."""
        print("STEP 4: SOLVING OPTIMIZATION PROBLEM")

        print("\n🔄 Running MILP solver (this may take a moment)...")

        # Solve the problem
        solver = PULP_CBC_CMD(msg=1, timeLimit=300)  # 5 minute time limit
        self.model.solve(solver)

        # Check solution status
        status = LpStatus[self.model.status]
        print(f"\n✓ Solver Status: {status}")

        if status != 'Optimal':
            print("⚠ Warning: Solution may not be optimal")

        # Extract results
        self.results = []
        for s in self.staff_ids:
            for j in self.job_ids:
                if value(self.assignments[s, j]) == 1:
                    # Get the assignment details
                    assignment_data = self.df[(self.df['Staff ID'] == s) & (self.df['Job_ID'] == j)].iloc[0]
                    self.results.append(assignment_data)

        self.results_df = pd.DataFrame(self.results)

        print(f"\n✓ Successfully assigned {len(self.results_df)} jobs")

        return self.results_df

    def analyze_solution(self):
        """Analyze and report on the optimization solution."""
        print("STEP 5: SOLUTION ANALYSIS & PERFORMANCE METRICS")

        # Overall metrics
        total_cost = self.results_df['Total_Cost'].sum()
        total_travel_cost = self.results_df['Travel_Cost'].sum()
        total_labour_cost = self.results_df['Labour_Cost'].sum()
        avg_satisfaction = self.results_df['Satisfaction Score'].mean()
        avg_skill_match = self.results_df['Skill_Match'].mean()
        avg_distance = self.results_df['Distance_km'].mean()

        print("\n💰 COST METRICS:")
        print(f"  Total Cost:        ${total_cost:,.2f}")
        print(f"  Travel Cost:       ${total_travel_cost:,.2f} ({total_travel_cost/total_cost:.1%})")
        print(f"  Labour Cost:       ${total_labour_cost:,.2f} ({total_labour_cost/total_cost:.1%})")
        print(f"  Average per Job:   ${total_cost/len(self.results_df):,.2f}")

        print("\n😊 QUALITY METRICS:")
        print(f"  Avg Satisfaction:  {avg_satisfaction:.2f} / 5.00")
        print(f"  Avg Skill Match:   {avg_skill_match:.1%}")
        print(f"  Avg Distance:      {avg_distance:.1f} km")

        # Priority coverage
        priority_coverage = self.results_df.groupby('Job_Priority').size()
        print("\n⭐ PRIORITY COVERAGE:")
        for priority in sorted(priority_coverage.index, reverse=True):
            print(f"  Priority {priority}: {priority_coverage[priority]} jobs")

        # Workload distribution
        workload = self.results_df.groupby('Staff ID').size()
        print(f"\n👥 WORKLOAD DISTRIBUTION:")
        print(f"  Staff utilized:    {len(workload)} / {len(self.staff_ids)}")
        print(f"  Jobs per staff:    {workload.mean():.2f} (avg), {workload.max()} (max), {workload.min()} (min)")
        print(f"  Std deviation:     {workload.std():.2f}")

        # Location distribution
        location_dist = self.results_df.groupby('Job_Location').size().sort_values(ascending=False)
        print(f"\n📍 TOP LOCATIONS:")
        for i, (loc, count) in enumerate(location_dist.head(5).items(), 1):
            print(f"  {i}. {loc}: {count} jobs")

        # Comparison with baseline (random assignment)
        print("BASELINE COMPARISON (Random Assignment)")

        # Create a random valid assignment baseline
        baseline_assignments = []
        for job in self.job_ids:
            valid_staff = self.df[(self.df['Job_ID'] == job) & (self.df['Skill_Match'] >= 0.5)]['Staff ID'].tolist()
            if valid_staff:
                random_staff = np.random.choice(valid_staff)
                assignment = self.df[(self.df['Staff ID'] == random_staff) & (self.df['Job_ID'] == job)].iloc[0]
                baseline_assignments.append(assignment)

        baseline_df = pd.DataFrame(baseline_assignments)

        baseline_cost = baseline_df['Total_Cost'].sum()
        baseline_satisfaction = baseline_df['Satisfaction Score'].mean()
        baseline_skill = baseline_df['Skill_Match'].mean()

        print(f"\n📊 Optimization vs Baseline:")
        print(f"  Cost Reduction:         {((baseline_cost - total_cost) / baseline_cost):.1%} (${baseline_cost - total_cost:,.2f} saved)")
        print(f"  Satisfaction Gain:      {((avg_satisfaction - baseline_satisfaction) / baseline_satisfaction):.1%}")
        print(f"  Skill Match Improvement: {((avg_skill_match - baseline_skill) / baseline_skill):.1%}")

        return {
            'total_cost': total_cost,
            'avg_satisfaction': avg_satisfaction,
            'avg_skill_match': avg_skill_match,
            'workload_distribution': workload,
            'cost_improvement': (baseline_cost - total_cost) / baseline_cost
        }

    def generate_schedule_output(self):
        """Generate the final optimized schedule."""
        print("OPTIMIZED SCHEDULE (First 20 assignments)")

        output_df = self.results_df[[
            'Staff ID', 'Job_ID', 'Job_Location', 'Job_Priority',
            'Skill_Match', 'Satisfaction Score', 'Distance_km',
            'Job_Hours', 'Total_Cost'
        ]].copy()

        output_df = output_df.sort_values(['Job_Priority', 'Total_Cost'], ascending=[False, True])

        print("\n")
        print(output_df.head(20).to_string(index=False))

        # Save to CSV
        output_df.to_csv(os.path.join(base_dir, 'optimized_schedule.csv'), index=False)
        print("\n✓ Full schedule saved to 'optimized_schedule.csv'")

        return output_df

    def create_results_visualizations(self):
        """Create visualizations of the optimization results."""
        print("\n📈 Generating results visualizations...")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('Optimized Scheduling Results', fontsize=16, fontweight='bold')

        # 1. Cost breakdown
        cost_data = pd.DataFrame({
            'Component': ['Travel Cost', 'Labour Cost'],
            'Amount': [self.results_df['Travel_Cost'].sum(), self.results_df['Labour_Cost'].sum()]
        })
        axes[0, 0].pie(cost_data['Amount'], labels=cost_data['Component'], autopct='%1.1f%%',
                       colors=['#ff9999', '#66b3ff'], startangle=90)
        axes[0, 0].set_title(f'Total Cost Breakdown\n${self.results_df["Total_Cost"].sum():,.0f}')

        # 2. Workload distribution
        workload = self.results_df.groupby('Staff ID').size()
        axes[0, 1].hist(workload, bins=20, color='steelblue', edgecolor='black', alpha=0.7)
        axes[0, 1].set_xlabel('Jobs per Staff Member')
        axes[0, 1].set_ylabel('Number of Staff')
        axes[0, 1].set_title('Workload Distribution')
        axes[0, 1].axvline(workload.mean(), color='red', linestyle='--', label=f'Mean: {workload.mean():.1f}')
        axes[0, 1].legend()

        # 3. Skill match distribution
        axes[0, 2].hist(self.results_df['Skill_Match'], bins=20, color='green', edgecolor='black', alpha=0.7)
        axes[0, 2].set_xlabel('Skill Match Score')
        axes[0, 2].set_ylabel('Number of Assignments')
        axes[0, 2].set_title('Skill Match Distribution')
        axes[0, 2].axvline(self.results_df['Skill_Match'].mean(), color='red', linestyle='--',
                          label=f'Mean: {self.results_df["Skill_Match"].mean():.2f}')
        axes[0, 2].legend()

        # 4. Priority fulfillment
        priority_counts = self.results_df.groupby('Job_Priority').size()
        axes[1, 0].bar(priority_counts.index, priority_counts.values,
                       color=['#d62728', '#ff7f0e', '#ffdd00', '#2ca02c', '#1f77b4'],
                       edgecolor='black')
        axes[1, 0].set_xlabel('Job Priority')
        axes[1, 0].set_ylabel('Number of Jobs')
        axes[1, 0].set_title('Jobs Assigned by Priority')
        axes[1, 0].set_xticks(range(1, 6))

        # 5. Location distribution
        location_counts = self.results_df.groupby('Job_Location').size().sort_values(ascending=False).head(10)
        axes[1, 1].barh(range(len(location_counts)), location_counts.values, color='teal')
        axes[1, 1].set_yticks(range(len(location_counts)))
        axes[1, 1].set_yticklabels(location_counts.index)
        axes[1, 1].set_xlabel('Number of Jobs')
        axes[1, 1].set_title('Top 10 Locations')
        axes[1, 1].invert_yaxis()

        # 6. Satisfaction vs Skill Match (optimized)
        scatter = axes[1, 2].scatter(self.results_df['Skill_Match'],
                                     self.results_df['Satisfaction Score'],
                                     c=self.results_df['Total_Cost'],
                                     cmap='RdYlGn_r', alpha=0.6, s=50, edgecolor='black')
        axes[1, 2].set_xlabel('Skill Match')
        axes[1, 2].set_ylabel('Satisfaction Score')
        axes[1, 2].set_title('Optimized Assignments Quality')
        plt.colorbar(scatter, ax=axes[1, 2], label='Total Cost')

        plt.tight_layout()
        plt.savefig(os.path.join(base_dir, 'optimization_results.png'), dpi=300, bbox_inches='tight')
        print("✓ Saved results visualizations to 'optimization_results.png'")
        plt.close()


def main():
    """Main execution function."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "STAFF SCHEDULING OPTIMIZATION SYSTEM" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    # Initialize optimizer
    optimizer = StaffSchedulingOptimizer(
        data_path=os.path.join(base_dir, 'extended_staff_scheduling_dataset.csv')
    )

    # Step 1: Load and clean data
    optimizer.load_and_clean_data()

    # Step 2: Exploratory analysis
    optimizer.exploratory_analysis()

    # Step 3: Create EDA visualizations
    optimizer.create_visualizations()

    # Step 4: Build optimization model
    optimizer.build_optimization_model(
        cost_weight=0.6,           # 60% weight on cost minimization
        satisfaction_weight=0.2,   # 20% weight on staff satisfaction
        skill_weight=0.2,          # 20% weight on skill match
        min_skill_match=0.5,       # At least 50% skill match required
        max_jobs_per_staff=5       # Maximum 5 jobs per staff member
    )

    # Step 5: Solve optimization
    optimizer.solve_optimization()

    # Step 6: Analyze solution
    metrics = optimizer.analyze_solution()

    # Step 7: Generate output
    optimizer.generate_schedule_output()

    # Step 8: Create visualizations
    optimizer.create_results_visualizations()

    print("✓ OPTIMIZATION COMPLETE")
    print("\nGenerated files:")
    print("  1. eda_visualizations.png - Exploratory data analysis charts")
    print("  2. optimization_results.png - Optimization results visualizations")
    print("  3. optimized_schedule.csv - Complete optimized schedule")
    print("\n")


if __name__ == "__main__":
    main()
