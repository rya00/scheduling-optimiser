# Streamlit Dashboard Guide

## Overview

The **Staff Scheduling Optimization Dashboard** is an interactive web application that allows you to:

- Explore the scheduling dataset with interactive Plotly visualizations
- Adjust optimization parameters in real-time
- Run the optimization with custom settings
- Compare optimized results against baseline (random assignment)
- Download optimized schedules and reports

## Features

### 1. Interactive Data Exploration

**Four main categories of analysis:**

- **Cost Analysis**: Cost distributions, breakdowns, distance vs travel cost
- **Quality Metrics**: Skill match, satisfaction, priority distributions
- **Geographic**: Location-based analysis, distance distributions
- **Staff Analysis**: Experience, hourly costs, absenteeism patterns

All charts are interactive with:
- Zoom and pan
- Hover tooltips
- Legend filtering
- Download as PNG

### 2. Customizable Optimization Parameters

**Objective Weights** (auto-normalized to sum to 1.0):
- Cost Minimization (0-1)
- Satisfaction Maximization (0-1)
- Skill Match Maximization (0-1)

**Constraints**:
- Minimum skill match threshold
- Maximum jobs per staff member (optional)
- Solver time limit

### 3. Real-Time Optimization

- Live progress bar showing optimization status
- Solver status reporting
- Solution time tracking
- Automatic baseline comparison

### 4. Comprehensive Results Visualization

**Four results tabs:**

1. **Cost Analysis**: Breakdown, distribution, top expensive assignments
2. **Quality Metrics**: Skill match, satisfaction, priority fulfillment
3. **Workload**: Staff utilization, workload distribution
4. **Comparison**: Side-by-side baseline vs optimized metrics

### 5. Data Export

Download three types of files:
- **Optimized Schedule CSV**: Complete assignment details
- **Summary Report TXT**: Key metrics and comparisons
- **Baseline Schedule CSV**: Random assignment for comparison

## How to Use

### Launch the App

**Option 1: Using the launcher script**
```bash
cd "scheduling tool"
./run_app.sh
```

**Option 2: Direct command**
```bash
cd "scheduling tool"
streamlit run streamlit_app.py
```

**Option 3: From anywhere**
```bash
streamlit run "scheduling tool/streamlit_app.py"
```

The app will automatically open in your default browser at `http://localhost:8501`

### Step-by-Step Workflow

1. **Configure Data Source** (Sidebar)
   - Choose "Use existing dataset" or upload your own CSV
   - Verify dataset is loaded successfully

2. **Explore the Data** (Data Exploration Tab)
   - Review all four categories of visualizations
   - Identify patterns and insights
   - Use interactive features (zoom, hover, filter)

3. **Set Optimization Parameters** (Sidebar)
   - Adjust objective weights based on priorities
   - Set minimum skill match threshold
   - Configure workload limits
   - Set solver time limit

4. **Run Optimization**
   - Click "🚀 Run Optimization" button
   - Watch progress bar
   - Wait for completion (typically 10-30 seconds)

5. **Review Results** (Optimization Results Tab)
   - Examine key metrics at the top
   - Explore all four results tabs
   - Compare with baseline performance
   - Identify improvement opportunities

6. **Download Results**
   - Download optimized schedule CSV
   - Download summary report
   - Download baseline for external comparison

### Example Use Cases

#### Scenario 1: Cost-Focused Optimization

```
Weights:
- Cost: 0.8
- Satisfaction: 0.1
- Skill: 0.1

Constraints:
- Min skill match: 0.5
- Max jobs per staff: 10
```

**Best for**: Budget constraints, high-volume operations

#### Scenario 2: Quality-Focused Optimization

```
Weights:
- Cost: 0.2
- Satisfaction: 0.4
- Skill: 0.4

Constraints:
- Min skill match: 0.7
- Max jobs per staff: 3
```

**Best for**: Premium services, client satisfaction priority

#### Scenario 3: Balanced Optimization

```
Weights:
- Cost: 0.5
- Satisfaction: 0.25
- Skill: 0.25

Constraints:
- Min skill match: 0.6
- Max jobs per staff: 5
```

**Best for**: Standard operations, balanced priorities

## Interactive Features

### Chart Interactions

All Plotly charts support:

- **Zoom**: Click and drag to zoom in
- **Pan**: Hold shift and drag to pan
- **Reset**: Double-click to reset view
- **Hover**: Hover over data points for details
- **Legend**: Click legend items to show/hide
- **Download**: Use camera icon to download PNG

### Data Filtering

- **Priority Filtering**: Click priority bars to focus
- **Location Selection**: Hover on location charts for details
- **Staff Selection**: Interact with workload distributions

## Performance Tips

### For Large Datasets (>10,000 jobs)

1. **Increase time limit**: Set to 600 seconds or more
2. **Relax constraints**: Lower min skill match to 0.5
3. **Enable workload limits**: Prevent overloading solver
4. **Use cost-focused weights**: Simpler objective = faster solve

### For High-Quality Solutions

1. **Increase time limit**: Allow more exploration
2. **Balance weights**: Don't over-weight one objective
3. **Tighten constraints**: Higher skill thresholds
4. **Review results**: Iterate on parameters

## Troubleshooting

### App won't start
```bash
# Check Streamlit is installed
pip show streamlit

# Reinstall if needed
pip install --upgrade streamlit
```

### Optimization fails
- Check dataset has valid assignments meeting constraints
- Reduce min skill match threshold
- Increase time limit
- Check for data quality issues

### Slow performance
- Reduce dataset size for testing
- Use more cost-focused weights
- Enable workload limits
- Increase time limit for patience

### Charts not displaying
```bash
# Reinstall plotly
pip install --upgrade plotly
```

## Advanced Features

### Custom Dataset Format

Your CSV must include these columns:

| Column | Type | Description |
|--------|------|-------------|
| Staff ID | String | Unique staff identifier |
| Years of Experience | Integer | Experience in years |
| Absenteeism (Days) | Integer | Days absent |
| Satisfaction Score | Float | 1-5 score |
| Job_ID | String | Unique job identifier |
| Job_Location | String | Location name |
| Distance_km | Float | Distance in km |
| Travel_Cost | Float | Travel cost in $ |
| Skill_Match | Float | 0-1 match score |
| Job_Priority | Integer | 1-5 priority |
| Cost_per_Hour | Float | Hourly rate |
| Job_Hours | Integer | Hours required |
| Labour_Cost | Float | Total labor cost |
| Total_Cost | Float | Total cost |

### API Integration

The Streamlit app can be integrated with other systems:

```python
# Example: Programmatic optimization
from streamlit_app import StreamlitSchedulingOptimizer
import pandas as pd

df = pd.read_csv('your_data.csv')
optimizer = StreamlitSchedulingOptimizer(df)

results_df, solve_time, status = optimizer.build_and_solve(
    cost_weight=0.6,
    satisfaction_weight=0.2,
    skill_weight=0.2,
    min_skill_match=0.5,
    max_jobs_per_staff=5,
    time_limit=300
)

print(f"Status: {status}, Time: {solve_time:.2f}s")
results_df.to_csv('optimized_schedule.csv', index=False)
```

## Deployment

### Local Development
```bash
streamlit run streamlit_app.py
```

### Production Deployment

**Streamlit Cloud:**
1. Push code to GitHub
2. Connect to Streamlit Cloud
3. Deploy with one click

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
```

**Cloud Platforms:**
- AWS: Use ECS with ALB
- GCP: Use Cloud Run
- Azure: Use Container Instances

## Keyboard Shortcuts

While in the app:
- `R`: Rerun the app
- `Ctrl + R`: Refresh browser
- `Ctrl + K`: Open command palette
- `Ctrl + Z`: Undo (in text inputs)

## Support

For issues or questions:
- Check this guide first
- Review error messages in the app
- Check console output where Streamlit is running
- Verify data format matches requirements

## Version History

**v1.0** (2025-10-27)
- Initial release
- Full EDA with Plotly
- MILP optimization engine
- Baseline comparison
- Download capabilities
- Interactive parameter tuning

---

**Last Updated**: 2025-10-27
**Compatible with**: Streamlit 1.28+, Plotly 5.17+
