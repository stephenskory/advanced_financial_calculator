import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html
from plotly.subplots import make_subplots

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# Global state for storing scenarios
stored_scenarios = {}

# Mortgage calculator functions
def calculate_mortgage_payment(principal, annual_rate, term_years):
    """Calculate the monthly mortgage payment."""
    # Add safety checks and defaults for None values
    if principal is None:
        principal = 0
    if annual_rate is None:
        annual_rate = 0
    if term_years is None:
        term_years = 30

    # Convert to float to ensure correct calculations
    principal = float(principal)
    annual_rate = float(annual_rate)
    term_years = float(term_years)

    # Avoid division by zero
    if term_years == 0:
        term_years = 1

    rate = annual_rate / 12  # Monthly interest rate
    n_payments = term_years * 12  # Total number of payments

    if rate == 0:
        return principal / n_payments

    # Standard mortgage payment formula
    numerator = principal * (rate * (1 + rate) ** n_payments)
    denominator = ((1 + rate) ** n_payments - 1)
    return numerator / denominator

def calculate_affordability(monthly_income, monthly_expenses, monthly_payment, 
                              rental_income=0, securities_monthly_income=0):
    """Calculate mortgage affordability metrics based on income ratios."""
    # Add safety checks and defaults for None values
    if monthly_income is None:
        monthly_income = 0
    if monthly_expenses is None:
        monthly_expenses = 0
    if monthly_payment is None:
        monthly_payment = 0
    if rental_income is None:
        rental_income = 0
    if securities_monthly_income is None:
        securities_monthly_income = 0
        
    # Convert to float to ensure correct calculations
    monthly_income = float(monthly_income)
    monthly_expenses = float(monthly_expenses)
    monthly_payment = float(monthly_payment)
    rental_income = float(rental_income)
    securities_monthly_income = float(securities_monthly_income)
    
    # Calculate total income including all sources
    total_monthly_income = monthly_income + rental_income + securities_monthly_income
    
    # Front-end ratio (mortgage payment to total income)
    front_end_ratio = (monthly_payment / total_monthly_income) * 100 if total_monthly_income > 0 else float('inf')
    
    # Back-end ratio (all debt payments including mortgage to total income)
    # Assuming monthly_expenses includes other debt payments
    back_end_ratio = ((monthly_payment + monthly_expenses) / total_monthly_income) * 100 if total_monthly_income > 0 else float('inf')
    
    # Typically, front-end ratio should be < 28% and back-end < 36%
    is_front_end_affordable = front_end_ratio <= 28
    is_back_end_affordable = back_end_ratio <= 36
    
    return {
        'total_monthly_income': total_monthly_income,
        'front_end_ratio': front_end_ratio,
        'back_end_ratio': back_end_ratio,
        'is_front_end_affordable': is_front_end_affordable,
        'is_back_end_affordable': is_back_end_affordable,
        'is_affordable': is_front_end_affordable and is_back_end_affordable
    }

def generate_amortization_schedule(
    principal, annual_rate, term_years, extra_payment=0,
):
    """Generate an amortization schedule for the mortgage."""
    # Safety checks and defaults for None values
    if principal is None:
        principal = 0
    if annual_rate is None:
        annual_rate = 0
    if term_years is None:
        term_years = 30
    if extra_payment is None:
        extra_payment = 0

    # Convert to float to ensure correct calculations
    principal = float(principal)
    annual_rate = float(annual_rate)
    term_years = float(term_years)
    extra_payment = float(extra_payment)

    # Avoid division by zero
    if term_years == 0:
        term_years = 1

    monthly_rate = annual_rate / 12
    n_payments = term_years * 12
    monthly_payment = calculate_mortgage_payment(
        principal, annual_rate, term_years,
    )

    schedule = []
    remaining_balance = principal
    total_interest = 0

    for month in range(1, int(n_payments) + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = min(
            monthly_payment - interest_payment + extra_payment,
            remaining_balance,
        )
        total_payment = principal_payment + interest_payment

        total_interest += interest_payment
        remaining_balance -= principal_payment

        if remaining_balance < 0.01:  # Account for floating-point errors
            remaining_balance = 0

        schedule.append({
            "Month": month,
            "Payment": total_payment,
            "Principal": principal_payment,
            "Interest": interest_payment,
            "Remaining Balance": remaining_balance,
            "Total Interest Paid": total_interest,
        })

        if remaining_balance == 0:
            break

    return pd.DataFrame(schedule)

def create_comparison_data(
    principal, annual_rate, term_years,
    monthly_income, monthly_expenses,
    existing_house_value=0, existing_house_sell_month=-1,
    existing_house_rent_income=0, existing_house_sale_to_securities=False,
    existing_house_appreciation_rate=0.03,  # Default 3% annual appreciation for existing house
    securities_value=0, securities_growth_rate=0, securities_sell_month=0,
    securities_monthly_sell=0,  # Amount of securities to sell per month
    savings_initial=0, savings_interest_rate=0, # Savings account
    home_appreciation_rate=0.03,  # Default 3% annual appreciation for new house
    inflation_rate=0.0,  # Annual inflation rate (default 0%)
    apply_inflation_to_income=False,  # Whether to adjust income for inflation
    apply_inflation_to_expenses=False,  # Whether to adjust expenses for inflation
    apply_inflation_to_rent=False,  # Whether to adjust rental income for inflation
):
    """Create comparison data for different mortgage funding strategies."""
    # Safety checks and defaults for None values
    if principal is None:
        principal = 0
    if annual_rate is None:
        annual_rate = 0
    if term_years is None:
        term_years = 30
    if monthly_income is None:
        monthly_income = 0
    if monthly_expenses is None:
        monthly_expenses = 0
    if existing_house_value is None:
        existing_house_value = 0
    if existing_house_sell_month is None:
        existing_house_sell_month = -1
    if existing_house_rent_income is None:
        existing_house_rent_income = 0
    if securities_value is None:
        securities_value = 0
    if securities_growth_rate is None:
        securities_growth_rate = 0
    if securities_sell_month is None:
        securities_sell_month = 0
    if securities_monthly_sell is None:
        securities_monthly_sell = 0
    if savings_initial is None:
        savings_initial = 0
    if savings_interest_rate is None:
        savings_interest_rate = 0
    if home_appreciation_rate is None:
        home_appreciation_rate = 0.03
    if existing_house_appreciation_rate is None:
        existing_house_appreciation_rate = 0.03
    if inflation_rate is None:
        inflation_rate = 0.0
    if apply_inflation_to_income is None:
        apply_inflation_to_income = False
    if apply_inflation_to_expenses is None:
        apply_inflation_to_expenses = False
    if apply_inflation_to_rent is None:
        apply_inflation_to_rent = False

    # Convert numeric values to float
    principal = float(principal)
    annual_rate = float(annual_rate)
    term_years = float(term_years)
    monthly_income = float(monthly_income)
    monthly_expenses = float(monthly_expenses)
    existing_house_value = float(existing_house_value)
    existing_house_rent_income = float(existing_house_rent_income)
    existing_house_appreciation_rate = float(existing_house_appreciation_rate)
    securities_value = float(securities_value)
    securities_growth_rate = float(securities_growth_rate)
    securities_monthly_sell = float(securities_monthly_sell)
    savings_initial = float(savings_initial)
    savings_interest_rate = float(savings_interest_rate)
    home_appreciation_rate = float(home_appreciation_rate)
    inflation_rate = float(inflation_rate)

    # Convert boolean values
    apply_inflation_to_income = bool(apply_inflation_to_income)
    apply_inflation_to_expenses = bool(apply_inflation_to_expenses)
    apply_inflation_to_rent = bool(apply_inflation_to_rent)

    # Avoid division by zero
    if term_years == 0:
        term_years = 1
    monthly_payment = calculate_mortgage_payment(principal, annual_rate, term_years)
    n_payments = term_years * 12
    months = list(range(int(n_payments) + 1))

    # Base property value over time (appreciation)
    monthly_appreciation_rate = home_appreciation_rate / 12
    property_values = [principal * (1 + monthly_appreciation_rate) ** m for m in months]

    # Existing house value over time (with its own appreciation rate)
    monthly_existing_house_appreciation_rate = existing_house_appreciation_rate / 12
    existing_house_values = [existing_house_value * (1 + monthly_existing_house_appreciation_rate) ** m for m in months]

    # Create arrays of the right length to begin with
    income_remaining_balance = [principal] * (len(months))
    income_net_worth = [securities_value + existing_house_value + savings_initial] * (len(months))
    income_securities_value = [securities_value] * (len(months))
    income_savings_value = [savings_initial] * (len(months))

    house_sell_remaining_balance = [principal] * (len(months))
    house_sell_net_worth = [securities_value + savings_initial] * (len(months))
    house_sell_securities_value = [securities_value] * (len(months))
    house_sell_savings_value = [savings_initial] * (len(months))

    rent_remaining_balance = [principal] * (len(months))
    rent_net_worth = [securities_value + existing_house_value + savings_initial] * (len(months))
    rent_securities_value = [securities_value] * (len(months))
    rent_savings_value = [savings_initial] * (len(months))

    securities_remaining_balance = [principal] * (len(months))
    securities_net_worth = [existing_house_value + savings_initial] * (len(months))
    securities_securities_value = [securities_value] * (len(months))
    securities_savings_value = [savings_initial] * (len(months))
    
    # Combination strategy - Securities + Rent
    combo_remaining_balance = [principal] * (len(months))
    combo_net_worth = [existing_house_value + savings_initial] * (len(months))
    combo_securities_value = [securities_value] * (len(months))
    combo_savings_value = [savings_initial] * (len(months))

    # Initial cash flow (monthly)
    cash_flow = monthly_income - monthly_expenses

    # Keep track of securities value for each strategy
    securities_value_current = securities_value

    # Create arrays to track monthly cash flow and inflation-adjusted values
    income_monthly_cashflow = [0] * (len(months))
    house_sell_monthly_cashflow = [0] * (len(months))
    rent_monthly_cashflow = [0] * (len(months))
    securities_monthly_cashflow = [0] * (len(months))
    combo_monthly_cashflow = [0] * (len(months))

    # Create arrays to track inflation-adjusted values over time
    inflation_adjusted_income = [monthly_income] * (len(months))
    inflation_adjusted_expenses = [monthly_expenses] * (len(months))
    inflation_adjusted_rent = [existing_house_rent_income] * (len(months))
    inflation_adjusted_values = [1.0] * (len(months))  # Inflation impact multiplier (1.0 = no impact)

    # Calculate data for each month
    for month in range(1, int(n_payments) + 1):
        # Common values
        current_property_value = property_values[month]

        # Calculate inflation adjustment for this month
        monthly_inflation_rate = inflation_rate / 12
        inflation_adjusted_values[month] = inflation_adjusted_values[month-1] * (1 + monthly_inflation_rate)

        # Apply inflation adjustments if specified
        if apply_inflation_to_income:
            inflation_adjusted_income[month] = monthly_income * inflation_adjusted_values[month]
        else:
            inflation_adjusted_income[month] = monthly_income

        if apply_inflation_to_expenses:
            inflation_adjusted_expenses[month] = monthly_expenses * inflation_adjusted_values[month]
        else:
            inflation_adjusted_expenses[month] = monthly_expenses

        if apply_inflation_to_rent:
            inflation_adjusted_rent[month] = existing_house_rent_income * inflation_adjusted_values[month]
        else:
            inflation_adjusted_rent[month] = existing_house_rent_income

        # Calculate monthly savings (income after expenses and mortgage payment)
        monthly_savings_rate = savings_interest_rate / 12

        # Strategy 1: Normal income
        prev_balance = income_remaining_balance[month-1]
        interest_payment = prev_balance * (annual_rate / 12)
        principal_payment = monthly_payment - interest_payment
        new_balance = max(0, prev_balance - principal_payment)
        income_remaining_balance[month] = new_balance

        # Update securities with growth rate
        income_securities_value[month] = income_securities_value[month-1] * (1 + securities_growth_rate / 12)

        # Calculate savings (monthly leftover cash + interest on existing savings)
        interest_earned = income_savings_value[month-1] * monthly_savings_rate
        monthly_leftover = inflation_adjusted_income[month] - inflation_adjusted_expenses[month] - monthly_payment

        # Track total monthly cash flow (positive numbers are money going in, negative are money going out)
        income_monthly_cashflow[month] = monthly_leftover + interest_earned

        if monthly_leftover > 0:
            income_savings_value[month] = income_savings_value[month-1] * (1 + monthly_savings_rate) + monthly_leftover
        else:
            income_savings_value[month] = max(0, income_savings_value[month-1] * (1 + monthly_savings_rate) + monthly_leftover)

        current_equity = current_property_value - new_balance
        current_existing_house_value = existing_house_values[month]
        current_net_worth = current_equity + income_securities_value[month] + current_existing_house_value + income_savings_value[month]
        income_net_worth[month] = current_net_worth

        # Strategy 2: Sell existing house
        prev_balance = house_sell_remaining_balance[month-1]

        # Update securities with growth rate
        house_sell_securities_value[month] = house_sell_securities_value[month-1] * (1 + securities_growth_rate / 12)

        interest_payment = prev_balance * (annual_rate / 12)
        principal_payment = monthly_payment - interest_payment
        new_balance = max(0, prev_balance - principal_payment)
        house_sell_remaining_balance[month] = new_balance

        # Calculate monthly leftover cash
        monthly_leftover = inflation_adjusted_income[month] - inflation_adjusted_expenses[month] - monthly_payment
        
        # Apply interest to savings
        interest_earned = house_sell_savings_value[month-1] * monthly_savings_rate
        
        # Initialize this month's savings with previous month plus interest
        house_sell_savings_value[month] = house_sell_savings_value[month-1] * (1 + monthly_savings_rate)
        
        # Process house sale (negative months mean don't sell)
        if month == existing_house_sell_month and existing_house_sell_month >= 0:
            # Get the current value of the existing house with appreciation
            current_existing_house_value = existing_house_values[month]
            
            # Add house sale proceeds to savings
            house_sell_savings_value[month] += current_existing_house_value

        # Add monthly leftovers to savings
        if monthly_leftover > 0:
            house_sell_savings_value[month] += monthly_leftover
        else:
            # If negative leftover (drawing from savings), ensure we don't go below zero
            house_sell_savings_value[month] = max(0, house_sell_savings_value[month] + monthly_leftover)

        # Track total monthly cash flow
        house_sell_monthly_cashflow[month] = monthly_leftover + interest_earned

        # Adjust net worth
        current_equity = current_property_value - new_balance
        # If the house was sold, its value is 0, otherwise use the current appreciated value
        current_house_value = 0 if month >= existing_house_sell_month and existing_house_sell_month >= 0 else existing_house_values[month]

        current_net_worth = current_equity + house_sell_securities_value[month] + current_house_value + house_sell_savings_value[month]
        house_sell_net_worth[month] = current_net_worth

        # Strategy 3: Rent existing house
        prev_balance = rent_remaining_balance[month-1]
        interest_payment = prev_balance * (annual_rate / 12)

        # Update securities with growth rate
        rent_securities_value[month] = rent_securities_value[month-1] * (1 + securities_growth_rate / 12)

        # Additional income from rent (inflation-adjusted)
        additional_payment = inflation_adjusted_rent[month]
        principal_payment = monthly_payment - interest_payment + additional_payment
        new_balance = max(0, prev_balance - principal_payment)
        rent_remaining_balance[month] = new_balance

        # Calculate savings (monthly leftover cash + interest on existing savings)
        interest_earned = rent_savings_value[month-1] * monthly_savings_rate
        monthly_leftover = inflation_adjusted_income[month] - inflation_adjusted_expenses[month] - monthly_payment + inflation_adjusted_rent[month]

        # Track total monthly cash flow
        rent_monthly_cashflow[month] = monthly_leftover + interest_earned

        if monthly_leftover > 0:
            rent_savings_value[month] = rent_savings_value[month-1] * (1 + monthly_savings_rate) + monthly_leftover
        else:
            rent_savings_value[month] = max(0, rent_savings_value[month-1] * (1 + monthly_savings_rate) + monthly_leftover)

        current_equity = current_property_value - new_balance
        current_existing_house_value = existing_house_values[month]
        current_net_worth = current_equity + rent_securities_value[month] + current_existing_house_value + rent_savings_value[month]
        rent_net_worth[month] = current_net_worth

        # Strategy 4: Sell securities
        prev_balance = securities_remaining_balance[month-1]
        interest_payment = prev_balance * (annual_rate / 12)

        # Get securities value from previous month
        temp_securities_value = securities_securities_value[month-1]

        # Calculate how securities value changes with time and selling
        monthly_sell_amount = 0

        # Apply growth first
        temp_securities_value *= (1 + securities_growth_rate / 12)

        # Process securities selling
        if month < securities_sell_month or securities_sell_month == 0:
            # Process monthly selling (if any)
            if securities_monthly_sell > 0 and temp_securities_value >= securities_monthly_sell:
                monthly_sell_amount = securities_monthly_sell
                temp_securities_value -= securities_monthly_sell
            elif securities_monthly_sell > 0:
                # Sell whatever is left
                monthly_sell_amount = temp_securities_value
                temp_securities_value = 0

        elif month == securities_sell_month:
            # One-time complete sale of securities
            monthly_sell_amount = temp_securities_value
            temp_securities_value = 0

        # Store the updated securities value
        securities_securities_value[month] = temp_securities_value

        principal_payment = monthly_payment - interest_payment
        new_balance = max(0, prev_balance - principal_payment)
        securities_remaining_balance[month] = new_balance

        # Calculate monthly leftover cash
        monthly_leftover = inflation_adjusted_income[month] - inflation_adjusted_expenses[month] - monthly_payment
        
        # Apply interest to savings
        interest_earned = securities_savings_value[month-1] * monthly_savings_rate
        
        # Initialize this month's savings with previous month plus interest
        securities_savings_value[month] = securities_savings_value[month-1] * (1 + monthly_savings_rate)
        
        # Apply securities proceeds to savings account
        if monthly_sell_amount > 0:
            securities_savings_value[month] += monthly_sell_amount

        # Add monthly leftovers to savings
        if monthly_leftover > 0:
            securities_savings_value[month] += monthly_leftover
        else:
            # If negative leftover (drawing from savings), ensure we don't go below zero
            securities_savings_value[month] = max(0, securities_savings_value[month] + monthly_leftover)

        # Track total monthly cash flow
        securities_monthly_cashflow[month] = monthly_leftover + interest_earned

        current_equity = current_property_value - new_balance
        current_existing_house_value = existing_house_values[month]
        current_net_worth = current_equity + temp_securities_value + current_existing_house_value + securities_savings_value[month]
        securities_net_worth[month] = current_net_worth
        
        # Strategy 5: Combination - Rent existing house AND sell securities
        prev_balance = combo_remaining_balance[month-1]
        interest_payment = prev_balance * (annual_rate / 12)
        
        # Get securities value from previous month
        temp_securities_value = combo_securities_value[month-1]
        
        # Calculate how securities value changes with time and selling
        monthly_sell_amount = 0
        
        # Apply growth first
        temp_securities_value *= (1 + securities_growth_rate / 12)
        
        # Process securities selling
        if month < securities_sell_month or securities_sell_month == 0:
            # Process monthly selling (if any)
            if securities_monthly_sell > 0 and temp_securities_value >= securities_monthly_sell:
                monthly_sell_amount = securities_monthly_sell
                temp_securities_value -= securities_monthly_sell
            elif securities_monthly_sell > 0:
                # Sell whatever is left
                monthly_sell_amount = temp_securities_value
                temp_securities_value = 0
                
        elif month == securities_sell_month:
            # One-time complete sale of securities
            monthly_sell_amount = temp_securities_value
            temp_securities_value = 0
            
        # Store the updated securities value
        combo_securities_value[month] = temp_securities_value
        
        # Check if the existing house is still owned (not sold)
        house_is_owned = True
        if existing_house_sell_month >= 0 and month >= existing_house_sell_month:
            house_is_owned = False
            
        # Additional income from rent (inflation-adjusted) - only if house is still owned
        additional_payment = inflation_adjusted_rent[month] if house_is_owned else 0
        
        principal_payment = monthly_payment - interest_payment
        new_balance = max(0, prev_balance - principal_payment)
        combo_remaining_balance[month] = new_balance
        
        # Calculate monthly leftover cash with rental income (only if house is still owned)
        rental_income = inflation_adjusted_rent[month] if house_is_owned else 0
        monthly_leftover = inflation_adjusted_income[month] - inflation_adjusted_expenses[month] - monthly_payment + rental_income
        
        # Apply interest to savings
        interest_earned = combo_savings_value[month-1] * monthly_savings_rate
        
        # Initialize this month's savings with previous month plus interest
        combo_savings_value[month] = combo_savings_value[month-1] * (1 + monthly_savings_rate)
        
        # Apply securities proceeds to savings account
        if monthly_sell_amount > 0:
            combo_savings_value[month] += monthly_sell_amount
            
        # Add monthly leftovers to savings
        if monthly_leftover > 0:
            combo_savings_value[month] += monthly_leftover
        else:
            # If negative leftover (drawing from savings), ensure we don't go below zero
            combo_savings_value[month] = max(0, combo_savings_value[month] + monthly_leftover)
            
        # Track total monthly cash flow
        combo_monthly_cashflow[month] = monthly_leftover + interest_earned
        
        current_equity = current_property_value - new_balance
        
        # If house was sold, its value is 0, otherwise use the current appreciated value
        current_existing_house_value = 0 if existing_house_sell_month >= 0 and month >= existing_house_sell_month else existing_house_values[month]
        
        current_net_worth = current_equity + temp_securities_value + current_existing_house_value + combo_savings_value[month]
        combo_net_worth[month] = current_net_worth

    # Combine data into a DataFrame
    comparison_data = pd.DataFrame({
        "Month": months,
        "Property_Value": property_values,
        "Existing_House_Value": existing_house_values,
        # Balance data
        "Income_Balance": income_remaining_balance,
        "House_Sell_Balance": house_sell_remaining_balance,
        "Rent_Balance": rent_remaining_balance,
        "Securities_Balance": securities_remaining_balance,
        "Combo_Balance": combo_remaining_balance,
        # Net worth data
        "Income_Net_Worth": income_net_worth,
        "House_Sell_Net_Worth": house_sell_net_worth,
        "Rent_Net_Worth": rent_net_worth,
        "Securities_Net_Worth": securities_net_worth,
        "Combo_Net_Worth": combo_net_worth,
        # Securities values
        "Income_Securities": income_securities_value,
        "House_Sell_Securities": house_sell_securities_value,
        "Rent_Securities": rent_securities_value,
        "Securities_Securities": securities_securities_value,
        "Combo_Securities": combo_securities_value,
        # Savings values
        "Income_Savings": income_savings_value,
        "House_Sell_Savings": house_sell_savings_value,
        "Rent_Savings": rent_savings_value,
        "Securities_Savings": securities_savings_value,
        "Combo_Savings": combo_savings_value,
        # Monthly cash flow
        "Income_Monthly_Cashflow": income_monthly_cashflow,
        "House_Sell_Monthly_Cashflow": house_sell_monthly_cashflow,
        "Rent_Monthly_Cashflow": rent_monthly_cashflow,
        "Securities_Monthly_Cashflow": securities_monthly_cashflow,
        "Combo_Monthly_Cashflow": combo_monthly_cashflow,
        # Inflation adjusted values
        "Inflation_Multiplier": inflation_adjusted_values,
        "Inflation_Adjusted_Income": inflation_adjusted_income,
        "Inflation_Adjusted_Expenses": inflation_adjusted_expenses,
        "Inflation_Adjusted_Rent": inflation_adjusted_rent,
    })

    return comparison_data

# Define the app layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Advanced Mortgage Funding Calculator", className="text-center mt-4 mb-4"),
            html.P("Compare different strategies for funding mortgage payments", className="text-center mb-4"),
        ]),
    ]),

    dbc.Row([
        # Left column - Inputs
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Mortgage Parameters"),
                dbc.CardBody([
                    html.Label("Principal Amount ($)"),
                    dcc.Input(id="principal", type="number", value=300000, min=10000, step=10000, className="mb-2 form-control"),

                    html.Label("Annual Interest Rate (%)"),
                    dcc.Input(id="annual-rate", type="number", value=4.5, min=0, max=20, step=0.1, className="mb-2 form-control"),

                    html.Label("Term (Years)"),
                    dcc.Input(id="term-years", type="number", value=30, min=1, max=50, className="mb-2 form-control"),

                    html.Label("Home Appreciation Rate (% per year)"),
                    dcc.Input(id="appreciation-rate", type="number", value=3.0, min=0, max=10, step=0.1, className="mb-2 form-control"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Inflation Adjustments"),
                dbc.CardBody([
                    html.Label("Annual Inflation Rate (%)"),
                    dcc.Input(id="inflation-rate", type="number", value=2.0, min=0, max=20, step=0.1, className="mb-2 form-control"),

                    html.Label("Apply Inflation To:"),
                    dbc.Checklist(
                        id="inflation-apply-to",
                        options=[
                            {"label": "Income", "value": "income"},
                            {"label": "Expenses", "value": "expenses"},
                            {"label": "Rental Income", "value": "rent"},
                        ],
                        value=["income", "expenses", "rent"],
                        inline=True,
                        className="mb-2",
                    ),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Income & Expenses"),
                dbc.CardBody([
                    html.Label("Monthly Income ($)"),
                    dcc.Input(id="monthly-income", type="number", value=8000, min=0, step=500, className="mb-2 form-control"),

                    html.Label("Monthly Expenses ($) (excluding mortgage)"),
                    dcc.Input(id="monthly-expenses", type="number", value=4000, min=0, step=500, className="mb-2 form-control"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Existing House"),
                dbc.CardBody([
                    html.Label("Current Value ($)"),
                    dcc.Input(id="existing-house-value", type="number", value=200000, min=0, step=10000, className="mb-2 form-control"),

                    html.Label("Annual Appreciation Rate (%)"),
                    dcc.Input(id="existing-house-appreciation-rate", type="number", value=3.0, min=0, max=10, step=0.1, className="mb-2 form-control"),

                    html.Label("Sell in Month # (negative = don't sell)"),
                    dcc.Input(id="existing-house-sell-month", type="number", value=-1, min=-1, step=1, className="mb-2 form-control"),

                    html.P("Sale proceeds are automatically added to savings account", className="text-muted mb-2"),

                    html.Label("Monthly Rental Income ($)"),
                    dcc.Input(id="existing-house-rent", type="number", value=1500, min=0, step=100, className="mb-2 form-control"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Savings Account"),
                dbc.CardBody([
                    html.Label("Initial Balance ($)"),
                    dcc.Input(id="savings-initial", type="number", value=10000, min=0, step=1000, className="mb-2 form-control"),

                    html.Label("Annual Interest Rate (%)"),
                    dcc.Input(id="savings-interest-rate", type="number", value=1.5, min=0, max=10, step=0.1, className="mb-2 form-control"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Securities"),
                dbc.CardBody([
                    html.Label("Current Value ($)"),
                    dcc.Input(id="securities-value", type="number", value=150000, min=0, step=10000, className="mb-2 form-control"),

                    html.Label("Annual Growth Rate (%)"),
                    dcc.Input(id="securities-growth-rate", type="number", value=7.0, min=0, max=20, step=0.1, className="mb-2 form-control"),

                    html.Label("Sell in Month #"),
                    dcc.Input(id="securities-sell-month", type="number", value=0, min=0, step=1, className="mb-2 form-control"),

                    html.Label("Monthly Sell Amount ($)"),
                    dcc.Input(id="securities-monthly-sell", type="number", value=0, min=0, step=100, className="mb-2 form-control"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Scenario Management"),
                dbc.CardBody([
                    html.Label("Scenario Name"),
                    dcc.Input(id="scenario-name", type="text", placeholder="Enter a name for this scenario", className="mb-2 form-control"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Save Scenario", id="save-scenario-button", color="success", className="w-100 mb-2"),
                        ], width=6),
                        dbc.Col([
                            dbc.Button("Load Scenario", id="load-scenario-button", color="info", className="w-100 mb-2"),
                        ], width=6),
                    ]),
                    html.Label("Saved Scenarios"),
                    dbc.Select(
                        id="scenario-selector",
                        options=[],
                        className="mb-2",
                    ),
                    dbc.Button("Delete Scenario", id="delete-scenario-button", color="danger", className="w-100 mb-2"),
                    html.Div(id="scenario-message", className="mt-2"),
                ]),
            ], className="mb-4"),

            dbc.Button("Calculate", id="calculate-button", color="primary", className="mt-2 w-100"),
        ], md=4),

        # Right column - Results & Graphs
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Monthly Payment Overview"),
                dbc.CardBody([
                    html.Div(id="payment-overview"),
                ]),
            ], className="mb-4"),

            dbc.Card([
                dbc.CardHeader("Monthly Savings Cash Flow"),
                dbc.CardBody([
                    html.Div(id="cashflow-overview"),
                ]),
            ], className="mb-4"),
            
            dbc.Card([
                dbc.CardHeader("Affordability Analysis"),
                dbc.CardBody([
                    html.Div(id="affordability-overview"),
                ]),
            ], className="mb-4"),

            dbc.Tabs([
                dbc.Tab([
                    dcc.Graph(id="balance-comparison-graph"),
                ], label="Loan Balance Comparison"),

                dbc.Tab([
                    dcc.Graph(id="net-worth-comparison-graph"),
                ], label="Net Worth Comparison"),

                dbc.Tab([
                    dcc.Graph(id="amortization-graph"),
                ], label="Amortization Schedule"),

                dbc.Tab([
                    dcc.Graph(id="securities-comparison-graph"),
                ], label="Securities Values"),

                dbc.Tab([
                    dcc.Graph(id="savings-comparison-graph"),
                ], label="Savings Values"),

                dbc.Tab([
                    dcc.Graph(id="cashflow-comparison-graph"),
                ], label="Monthly Cash Flow"),

                dbc.Tab([
                    dcc.Graph(id="inflation-impact-graph"),
                ], label="Inflation Impact"),

                dbc.Tab([
                    html.Div(id="strategy-details", className="mt-3"),
                ], label="Strategy Details"),

                dbc.Tab([
                    html.Div([
                        html.H4("Scenario Comparison", className="mb-3"),
                        html.P("Select scenarios to compare their outcomes. The chart will update automatically."),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Select First Scenario"),
                                dbc.Select(id="compare-scenario-1", options=[], className="mb-3"),
                            ], md=6),
                            dbc.Col([
                                html.Label("Select Second Scenario"),
                                dbc.Select(id="compare-scenario-2", options=[], className="mb-3"),
                            ], md=6),
                        ]),
                        html.Label("Select Comparison Metric"),
                        dbc.Select(
                            id="comparison-metric",
                            options=[
                                {"label": "Net Worth (Income Strategy)", "value": "Income_Net_Worth"},
                                {"label": "Net Worth (House Sell Strategy)", "value": "House_Sell_Net_Worth"},
                                {"label": "Net Worth (Rent Strategy)", "value": "Rent_Net_Worth"},
                                {"label": "Net Worth (Securities Strategy)", "value": "Securities_Net_Worth"},
                                {"label": "Net Worth (Rent + Sell Securities)", "value": "Combo_Net_Worth"},
                                {"label": "Loan Balance (Income Strategy)", "value": "Income_Balance"},
                                {"label": "Loan Balance (House Sell Strategy)", "value": "House_Sell_Balance"},
                                {"label": "Loan Balance (Rent Strategy)", "value": "Rent_Balance"},
                                {"label": "Loan Balance (Securities Strategy)", "value": "Securities_Balance"},
                                {"label": "Loan Balance (Rent + Sell Securities)", "value": "Combo_Balance"},
                                {"label": "Savings (Income Strategy)", "value": "Income_Savings"},
                                {"label": "Savings (House Sell Strategy)", "value": "House_Sell_Savings"},
                                {"label": "Savings (Rent Strategy)", "value": "Rent_Savings"},
                                {"label": "Savings (Securities Strategy)", "value": "Securities_Savings"},
                                {"label": "Savings (Rent + Sell Securities)", "value": "Combo_Savings"},
                                {"label": "Monthly Cash Flow (Income Strategy)", "value": "Income_Monthly_Cashflow"},
                                {"label": "Monthly Cash Flow (House Sell Strategy)", "value": "House_Sell_Monthly_Cashflow"},
                                {"label": "Monthly Cash Flow (Rent Strategy)", "value": "Rent_Monthly_Cashflow"},
                                {"label": "Monthly Cash Flow (Securities Strategy)", "value": "Securities_Monthly_Cashflow"},
                                {"label": "Monthly Cash Flow (Rent + Sell Securities)", "value": "Combo_Monthly_Cashflow"},
                            ],
                            value="Income_Net_Worth",
                            className="mb-3",
                        ),
                        dcc.Graph(id="scenario-comparison-graph"),
                        html.Div(id="scenario-comparison-summary", className="mt-3"),
                    ]),
                ], label="Scenario Comparison"),
            ]),
        ], md=8),
    ]),

    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.P("Advanced Financial Mortgage Calculator", className="text-center"),
        ]),
    ]),
], fluid=True)

# Callbacks for interactive elements
@app.callback(
    [Output("payment-overview", "children"),
     Output("cashflow-overview", "children"),
     Output("affordability-overview", "children"),
     Output("balance-comparison-graph", "figure"),
     Output("net-worth-comparison-graph", "figure"),
     Output("amortization-graph", "figure"),
     Output("securities-comparison-graph", "figure"),
     Output("savings-comparison-graph", "figure"),
     Output("cashflow-comparison-graph", "figure"),
     Output("inflation-impact-graph", "figure"),
     Output("strategy-details", "children")],
    [Input("calculate-button", "n_clicks")],
    [State("principal", "value"),
     State("annual-rate", "value"),
     State("term-years", "value"),
     State("monthly-income", "value"),
     State("monthly-expenses", "value"),
     State("existing-house-value", "value"),
     State("existing-house-appreciation-rate", "value"),
     State("existing-house-sell-month", "value"),
     State("existing-house-rent", "value"),
     State("savings-initial", "value"),
     State("savings-interest-rate", "value"),
     State("securities-value", "value"),
     State("securities-growth-rate", "value"),
     State("securities-sell-month", "value"),
     State("securities-monthly-sell", "value"),
     State("appreciation-rate", "value"),
     State("inflation-rate", "value"),
     State("inflation-apply-to", "value")],
)
def update_results(n_clicks, principal, annual_rate, term_years,
                  monthly_income, monthly_expenses,
                  existing_house_value, existing_house_appreciation_rate, existing_house_sell_month,
                  existing_house_rent, savings_initial, savings_interest_rate,
                  securities_value, securities_growth_rate, securities_sell_month, securities_monthly_sell,
                  appreciation_rate, inflation_rate, inflation_apply_to):
    # Convert percentage inputs to decimal
    annual_rate_decimal = annual_rate / 100 if annual_rate else 0
    appreciation_rate_decimal = appreciation_rate / 100 if appreciation_rate else 0
    existing_house_appreciation_rate_decimal = existing_house_appreciation_rate / 100 if existing_house_appreciation_rate else 0
    savings_interest_rate_decimal = savings_interest_rate / 100 if savings_interest_rate else 0
    securities_growth_rate_decimal = securities_growth_rate / 100 if securities_growth_rate else 0
    inflation_rate_decimal = inflation_rate / 100 if inflation_rate else 0

    # Process inflation apply-to selections
    apply_inflation_to_income = "income" in inflation_apply_to if inflation_apply_to else False
    apply_inflation_to_expenses = "expenses" in inflation_apply_to if inflation_apply_to else False
    apply_inflation_to_rent = "rent" in inflation_apply_to if inflation_apply_to else False

    # Calculate monthly payment
    monthly_payment = calculate_mortgage_payment(principal, annual_rate_decimal, term_years)

    # Generate amortization schedule
    amortization_df = generate_amortization_schedule(principal, annual_rate_decimal, term_years)

    # Generate comparison data 
    # Note: house_sale_to_securities is now always False since all proceeds go to savings
    comparison_df = create_comparison_data(
        principal, annual_rate_decimal, term_years,
        monthly_income, monthly_expenses,
        existing_house_value, existing_house_sell_month, existing_house_rent, False,
        existing_house_appreciation_rate_decimal,
        securities_value, securities_growth_rate_decimal, securities_sell_month, securities_monthly_sell,
        savings_initial, savings_interest_rate_decimal,
        appreciation_rate_decimal,
        inflation_rate_decimal, apply_inflation_to_income, apply_inflation_to_expenses, apply_inflation_to_rent,
    )

    # Ensure values are not None for formatting
    safe_principal = 0 if principal is None else principal
    safe_term_years = 0 if term_years is None else term_years

    # Calculate affordability metrics
    # Calculate estimated monthly income from securities (if selling monthly)
    securities_monthly_income = securities_monthly_sell if securities_monthly_sell else 0
    # For affordability calculation, use rental income if available
    affordability = calculate_affordability(
        monthly_income, 
        monthly_expenses, 
        monthly_payment,
        existing_house_rent,  # Add rental income
        securities_monthly_income  # Add securities monthly income
    )

    # Create payment overview
    payment_overview = dbc.Row([
        dbc.Col([
            html.H4(f"${monthly_payment:.2f}", className="text-primary"),
            html.P("Monthly Payment"),
        ], className="text-center"),
        dbc.Col([
            html.H4(f"${float(safe_principal):.2f}", className="text-primary"),
            html.P("Loan Amount"),
        ], className="text-center"),
        dbc.Col([
            html.H4(f"${amortization_df['Total Interest Paid'].iloc[-1]:.2f}", className="text-primary"),
            html.P("Total Interest"),
        ], className="text-center"),
        dbc.Col([
            html.H4(f"{safe_term_years} years", className="text-primary"),
            html.P("Term Length"),
        ], className="text-center"),
    ])

    # Get the latest month with data
    current_month = min(120, len(comparison_df) - 1)  # Show month 120 (year 10) or the last month if earlier
    initial_month = 1  # Month 1 for initial cash flow

    # Create cashflow overview
    cashflow_overview = dbc.Row([
        dbc.Col([
            html.H5("Initial Monthly Cash Flow"),
            html.Div([
                html.P(f"Regular Income Strategy: ${comparison_df['Income_Monthly_Cashflow'].iloc[initial_month]:.2f}",
                       className="text-success" if comparison_df["Income_Monthly_Cashflow"].iloc[initial_month] >= 0 else "text-danger"),
                html.P(f"Sell House Strategy: ${comparison_df['House_Sell_Monthly_Cashflow'].iloc[initial_month]:.2f}",
                       className="text-success" if comparison_df["House_Sell_Monthly_Cashflow"].iloc[initial_month] >= 0 else "text-danger"),
                html.P(f"Rent House Strategy: ${comparison_df['Rent_Monthly_Cashflow'].iloc[initial_month]:.2f}",
                       className="text-success" if comparison_df["Rent_Monthly_Cashflow"].iloc[initial_month] >= 0 else "text-danger"),
                html.P(f"Securities Strategy: ${comparison_df['Securities_Monthly_Cashflow'].iloc[initial_month]:.2f}",
                       className="text-success" if comparison_df["Securities_Monthly_Cashflow"].iloc[initial_month] >= 0 else "text-danger"),
                html.P(f"Rent + Sell Securities: ${comparison_df['Combo_Monthly_Cashflow'].iloc[initial_month]:.2f}",
                       className="text-success" if comparison_df["Combo_Monthly_Cashflow"].iloc[initial_month] >= 0 else "text-danger"),
            ]),
        ], md=6),
        dbc.Col([
            html.H5(f"Month {current_month} Cash Flow"),
            html.Div([
                html.P(f"Regular Income Strategy: ${comparison_df['Income_Monthly_Cashflow'].iloc[current_month]:.2f}",
                       className="text-success" if comparison_df["Income_Monthly_Cashflow"].iloc[current_month] >= 0 else "text-danger"),
                html.P(f"Sell House Strategy: ${comparison_df['House_Sell_Monthly_Cashflow'].iloc[current_month]:.2f}",
                       className="text-success" if comparison_df["House_Sell_Monthly_Cashflow"].iloc[current_month] >= 0 else "text-danger"),
                html.P(f"Rent House Strategy: ${comparison_df['Rent_Monthly_Cashflow'].iloc[current_month]:.2f}",
                       className="text-success" if comparison_df["Rent_Monthly_Cashflow"].iloc[current_month] >= 0 else "text-danger"),
                html.P(f"Securities Strategy: ${comparison_df['Securities_Monthly_Cashflow'].iloc[current_month]:.2f}",
                       className="text-success" if comparison_df["Securities_Monthly_Cashflow"].iloc[current_month] >= 0 else "text-danger"),
                html.P(f"Rent + Sell Securities: ${comparison_df['Combo_Monthly_Cashflow'].iloc[current_month]:.2f}",
                       className="text-success" if comparison_df["Combo_Monthly_Cashflow"].iloc[current_month] >= 0 else "text-danger"),
            ]),
        ], md=6),
    ])
    
    # Create affordability overview
    affordability_overview = dbc.Row([
        dbc.Col([
            html.H5("Affordability Metrics"),
            html.Div([
                html.P(f"Primary Monthly Income: ${monthly_income:.2f}"),
                html.P(f"Rental Income: ${existing_house_rent:.2f}" if existing_house_rent > 0 else "No Rental Income"),
                html.P(f"Securities Monthly Income: ${securities_monthly_income:.2f}" if securities_monthly_income > 0 else "No Securities Monthly Income"),
                html.P(f"Total Monthly Income: ${affordability['total_monthly_income']:.2f}", className="font-weight-bold"),
                html.P(f"Monthly Mortgage Payment: ${monthly_payment:.2f}"),
                html.Hr(),
                html.P(f"Front-end Ratio: {affordability['front_end_ratio']:.2f}% " + 
                       ("(Affordable)" if affordability['is_front_end_affordable'] else "(Too High)"),
                       className="text-success" if affordability['is_front_end_affordable'] else "text-danger"),
                html.P(f"Back-end Ratio: {affordability['back_end_ratio']:.2f}% " + 
                       ("(Affordable)" if affordability['is_back_end_affordable'] else "(Too High)"),
                       className="text-success" if affordability['is_back_end_affordable'] else "text-danger"),
                html.P(f"Overall Assessment: " + 
                       ("Affordable" if affordability['is_affordable'] else "Not Affordable based on income ratios"),
                       className="text-success font-weight-bold" if affordability['is_affordable'] else "text-danger font-weight-bold"),
                html.P("Front-end ratio should be under 28% (mortgage payment to total income)"),
                html.P("Back-end ratio should be under 36% (all debt payments to total income)"),
            ]),
        ]),
    ])

    # Create balance comparison graph
    balance_fig = go.Figure()

    balance_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Income_Balance"],
                          mode="lines", name="Regular Income"))

    balance_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["House_Sell_Balance"],
                          mode="lines", name="Sell Existing House"))

    balance_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Rent_Balance"],
                          mode="lines", name="Rent Existing House"))

    balance_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Securities_Balance"],
                          mode="lines", name="Sell Securities"))
                          
    balance_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Combo_Balance"],
                          mode="lines", name="Rent + Sell Securities"))

    balance_fig.update_layout(
        title="Loan Balance Comparison",
        xaxis_title="Month",
        yaxis_title="Remaining Balance ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create net worth comparison graph with asset breakdown
    net_worth_fig = go.Figure()

    # Calculate home equity for each strategy
    home_equity_income = comparison_df["Property_Value"] - comparison_df["Income_Balance"]
    home_equity_house_sell = comparison_df["Property_Value"] - comparison_df["House_Sell_Balance"]
    home_equity_rent = comparison_df["Property_Value"] - comparison_df["Rent_Balance"]
    home_equity_securities = comparison_df["Property_Value"] - comparison_df["Securities_Balance"]
    home_equity_combo = comparison_df["Property_Value"] - comparison_df["Combo_Balance"]

    # Create arrays to track house values for each strategy, accounting for sales
    existing_house_values_income = comparison_df["Existing_House_Value"].copy()
    existing_house_values_rent = comparison_df["Existing_House_Value"].copy()
    existing_house_values_securities = comparison_df["Existing_House_Value"].copy()
    
    # For house sell strategy, set value to 0 after selling
    existing_house_values_sell = []
    existing_house_values_combo = []
    for month in range(len(comparison_df)):
        if existing_house_sell_month >= 0 and month >= existing_house_sell_month:
            existing_house_values_sell.append(0)
            existing_house_values_combo.append(0)  # Also set combo strategy house value to 0 after selling
        else:
            existing_house_values_sell.append(comparison_df["Existing_House_Value"][month])
            existing_house_values_combo.append(comparison_df["Existing_House_Value"][month])

    # Regular Income Strategy - Stacked assets
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=home_equity_income,
        name="Home Equity (Income)",
        marker_color="rgba(46, 204, 113, 0.7)",
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Income_Securities"],
        name="Securities (Income)",
        marker_color="rgba(52, 152, 219, 0.7)",
    ))

    # Use strategy-specific array for existing house value
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=existing_house_values_income,
        name="Existing House (Income)",
        marker_color="rgba(155, 89, 182, 0.7)",
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Income_Savings"],
        name="Savings (Income)",
        marker_color="rgba(241, 196, 15, 0.7)",
    ))

    # House Sell Strategy - Stacked assets
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=home_equity_house_sell,
        name="Home Equity (Sell House)",
        marker_color="rgba(231, 76, 60, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["House_Sell_Securities"],
        name="Securities (Sell House)",
        marker_color="rgba(41, 128, 185, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=existing_house_values_sell,
        name="Existing House (Sell House)",
        marker_color="rgba(142, 68, 173, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["House_Sell_Savings"],
        name="Savings (Sell House)",
        marker_color="rgba(243, 156, 18, 0.7)",
        visible=False,
    ))

    # Rent Strategy - Stacked assets
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=home_equity_rent,
        name="Home Equity (Rent)",
        marker_color="rgba(39, 174, 96, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Rent_Securities"],
        name="Securities (Rent)",
        marker_color="rgba(41, 128, 185, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=existing_house_values_rent,
        name="Existing House (Rent)",
        marker_color="rgba(142, 68, 173, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Rent_Savings"],
        name="Savings (Rent)",
        marker_color="rgba(243, 156, 18, 0.7)",
        visible=False,
    ))

    # Securities Strategy - Stacked assets
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=home_equity_securities,
        name="Home Equity (Securities)",
        marker_color="rgba(39, 174, 96, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Securities_Securities"],
        name="Securities (Securities)",
        marker_color="rgba(41, 128, 185, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=existing_house_values_securities,
        name="Existing House (Securities)",
        marker_color="rgba(142, 68, 173, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Securities_Savings"],
        name="Savings (Securities)",
        marker_color="rgba(243, 156, 18, 0.7)",
        visible=False,
    ))

    # Combo Strategy - Stacked assets
    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=home_equity_combo,
        name="Home Equity (Combo)",
        marker_color="rgba(39, 174, 96, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Combo_Securities"],
        name="Securities (Combo)",
        marker_color="rgba(41, 128, 185, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=existing_house_values_combo,
        name="Existing House (Combo)",
        marker_color="rgba(142, 68, 173, 0.7)",
        visible=False,
    ))

    net_worth_fig.add_trace(go.Bar(
        x=comparison_df["Month"],
        y=comparison_df["Combo_Savings"],
        name="Savings (Combo)",
        marker_color="rgba(243, 156, 18, 0.7)",
        visible=False,
    ))

    # Add total net worth lines for comparison
    net_worth_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=comparison_df["Income_Net_Worth"],
        mode="lines",
        name="Total (Income)",
        line=dict(color="rgba(46, 204, 113, 1)", width=3),
    ))

    net_worth_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=comparison_df["House_Sell_Net_Worth"],
        mode="lines",
        name="Total (Sell House)",
        line=dict(color="rgba(231, 76, 60, 1)", width=3),
        visible=False,
    ))

    net_worth_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=comparison_df["Rent_Net_Worth"],
        mode="lines",
        name="Total (Rent)",
        line=dict(color="rgba(52, 152, 219, 1)", width=3),
        visible=False,
    ))

    net_worth_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=comparison_df["Securities_Net_Worth"],
        mode="lines",
        name="Total (Securities)",
        line=dict(color="rgba(155, 89, 182, 1)", width=3),
        visible=False,
    ))
    
    net_worth_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=comparison_df["Combo_Net_Worth"],
        mode="lines",
        name="Total (Rent + Sell Securities)",
        line=dict(color="rgba(255, 165, 0, 1)", width=3),
        visible=False,
    ))

    # Add buttons to toggle between strategies
    net_worth_fig.update_layout(
        title="Net Worth Breakdown by Asset Type",
        xaxis_title="Month",
        yaxis_title="Net Worth ($)",
        barmode="stack",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.24, xanchor="center", x=0.5),
        height=700,  # Increase the height to make more room
        margin=dict(t=150),  # Add more top margin for the buttons and legend
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                x=0.5,
                y=1.12,
                xanchor="center",
                yanchor="top",
                buttons=list([
                    dict(
                        label="Income Strategy",
                        method="update",
                        args=[
                            {"visible": [True, True, True, True,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         True, False, False, False, False]},
                            {"title": "Net Worth Breakdown - Income Strategy"},
                        ],
                    ),
                    dict(
                        label="Sell House Strategy",
                        method="update",
                        args=[
                            {"visible": [False, False, False, False,
                                         True, True, True, True,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, True, False, False, False]},
                            {"title": "Net Worth Breakdown - Sell House Strategy"},
                        ],
                    ),
                    dict(
                        label="Rent Strategy",
                        method="update",
                        args=[
                            {"visible": [False, False, False, False,
                                         False, False, False, False,
                                         True, True, True, True,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, True, False, False]},
                            {"title": "Net Worth Breakdown - Rent Strategy"},
                        ],
                    ),
                    dict(
                        label="Securities Strategy",
                        method="update",
                        args=[
                            {"visible": [False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         True, True, True, True,
                                         False, False, False, False,
                                         False, False, False, True, False]},
                            {"title": "Net Worth Breakdown - Securities Strategy"},
                        ],
                    ),
                    dict(
                        label="Combo Strategy (Rent + Securities)",
                        method="update",
                        args=[
                            {"visible": [False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         True, True, True, True,
                                         False, False, False, False, True]},
                            {"title": "Net Worth Breakdown - Rent + Sell Securities Strategy"},
                        ],
                    ),
                    dict(
                        label="Compare All (Lines Only)",
                        method="update",
                        args=[
                            {"visible": [False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         False, False, False, False,
                                         True, True, True, True, True]},
                            {"title": "Net Worth Comparison - All Strategies"},
                        ],
                    ),
                ]),
            ),
        ],
    )

    # Create securities comparison graph
    securities_fig = go.Figure()

    securities_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Income_Securities"],
                           mode="lines", name="Regular Income"))

    securities_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["House_Sell_Securities"],
                           mode="lines", name="Sell Existing House"))

    securities_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Rent_Securities"],
                           mode="lines", name="Rent Existing House"))

    securities_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Securities_Securities"],
                           mode="lines", name="Sell Securities"))
                           
    securities_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Combo_Securities"],
                           mode="lines", name="Rent + Sell Securities"))

    securities_fig.update_layout(
        title="Securities Value Over Time",
        xaxis_title="Month",
        yaxis_title="Securities Value ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create savings comparison graph
    savings_fig = go.Figure()

    savings_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Income_Savings"],
                           mode="lines", name="Regular Income"))

    savings_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["House_Sell_Savings"],
                           mode="lines", name="Sell Existing House"))

    savings_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Rent_Savings"],
                           mode="lines", name="Rent Existing House"))

    savings_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Securities_Savings"],
                           mode="lines", name="Sell Securities"))
                           
    savings_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Combo_Savings"],
                           mode="lines", name="Rent + Sell Securities"))

    savings_fig.update_layout(
        title="Savings Account Value Over Time",
        xaxis_title="Month",
        yaxis_title="Savings Value ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create cash flow comparison graph
    cashflow_fig = go.Figure()

    cashflow_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Income_Monthly_Cashflow"],
                           mode="lines", name="Regular Income"))

    cashflow_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["House_Sell_Monthly_Cashflow"],
                           mode="lines", name="Sell Existing House"))

    cashflow_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Rent_Monthly_Cashflow"],
                           mode="lines", name="Rent Existing House"))

    cashflow_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Securities_Monthly_Cashflow"],
                           mode="lines", name="Sell Securities"))
                           
    cashflow_fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Combo_Monthly_Cashflow"],
                           mode="lines", name="Rent + Sell Securities"))

    # Add a horizontal line at y=0 to show the break-even point
    cashflow_fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="black")

    cashflow_fig.update_layout(
        title="Monthly Cash Flow Over Time",
        xaxis_title="Month",
        yaxis_title="Monthly Cash Flow ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create inflation impact graph
    inflation_fig = go.Figure()

    if apply_inflation_to_income:
        inflation_fig.add_trace(go.Scatter(
            x=comparison_df["Month"],
            y=comparison_df["Inflation_Adjusted_Income"],
            mode="lines",
            name="Monthly Income",
        ))

    if apply_inflation_to_expenses:
        inflation_fig.add_trace(go.Scatter(
            x=comparison_df["Month"],
            y=comparison_df["Inflation_Adjusted_Expenses"],
            mode="lines",
            name="Monthly Expenses",
        ))

    if apply_inflation_to_rent:
        inflation_fig.add_trace(go.Scatter(
            x=comparison_df["Month"],
            y=comparison_df["Inflation_Adjusted_Rent"],
            mode="lines",
            name="Monthly Rent",
        ))

    # Add inflation multiplier as a percentage on secondary y-axis
    inflation_percentage = [(value - 1) * 100 for value in comparison_df["Inflation_Multiplier"]]

    inflation_fig.add_trace(go.Scatter(
        x=comparison_df["Month"],
        y=inflation_percentage,
        mode="lines",
        name="Cumulative Inflation (%)",
        line=dict(dash="dash", color="red"),
    ))

    inflation_fig.update_layout(
        title="Impact of Inflation Over Time",
        xaxis_title="Month",
        yaxis_title="Amount ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create amortization graph
    amortization_fig = make_subplots(specs=[[{"secondary_y": True}]])

    amortization_fig.add_trace(
        go.Bar(x=amortization_df["Month"], y=amortization_df["Principal"], name="Principal"),
        secondary_y=False,
    )

    amortization_fig.add_trace(
        go.Bar(x=amortization_df["Month"], y=amortization_df["Interest"], name="Interest"),
        secondary_y=False,
    )

    amortization_fig.add_trace(
        go.Scatter(x=amortization_df["Month"], y=amortization_df["Remaining Balance"],
                  name="Remaining Balance", line=dict(color="red")),
        secondary_y=True,
    )

    amortization_fig.update_layout(
        title="Amortization Schedule",
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    amortization_fig.update_yaxes(title_text="Payment Amount ($)", secondary_y=False)
    amortization_fig.update_yaxes(title_text="Remaining Balance ($)", secondary_y=True)

    # Create strategy details
    strategy_details = html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("Strategy Comparison"),
                html.P("Below is a detailed comparison of different mortgage funding strategies based on your inputs."),

                dbc.Card([
                    dbc.CardHeader("Regular Income Strategy"),
                    dbc.CardBody([
                        html.P(f"Monthly Payment: ${monthly_payment:.2f}"),
                        html.P(f"Total Paid Over Loan Term: ${monthly_payment * safe_term_years * 12:.2f}"),
                        html.P(f"Net Worth After {safe_term_years} Years: ${comparison_df['Income_Net_Worth'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Selling Existing House Strategy"),
                    dbc.CardBody([
                        html.P(f"Initial House Value: ${existing_house_value if existing_house_value is not None else 0:.2f}"),
                        html.P(f"Annual Appreciation Rate: {existing_house_appreciation_rate if existing_house_appreciation_rate is not None else 3.0}%"),
                        html.P(f"Final Value Before Sale: ${comparison_df['Existing_House_Value'].iloc[-1]:.2f}"),
                        html.P(f"Sale Month: {existing_house_sell_month}" if existing_house_sell_month is not None and existing_house_sell_month >= 0 else "Not Planning to Sell"),
                        html.P("Proceeds Go To: Savings Account"),
                        html.P(f"Net Worth After {safe_term_years} Years: ${comparison_df['House_Sell_Net_Worth'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Renting Existing House Strategy"),
                    dbc.CardBody([
                        html.P(f"Initial House Value: ${existing_house_value if existing_house_value is not None else 0:.2f}"),
                        html.P(f"Annual Appreciation Rate: {existing_house_appreciation_rate if existing_house_appreciation_rate is not None else 3.0}%"),
                        html.P(f"Final House Value: ${comparison_df['Existing_House_Value'].iloc[-1]:.2f}"),
                        html.P(f"Monthly Rental Income: ${existing_house_rent if existing_house_rent is not None else 0:.2f}"),
                        html.P(f"Annual Rental Income: ${(existing_house_rent if existing_house_rent is not None else 0) * 12:.2f}"),
                        html.P(f"Net Worth After {safe_term_years} Years: ${comparison_df['Rent_Net_Worth'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Savings Account Details"),
                    dbc.CardBody([
                        html.P(f"Initial Savings: ${savings_initial if savings_initial is not None else 0:.2f}"),
                        html.P(f"Annual Interest Rate: {savings_interest_rate if savings_interest_rate is not None else 0}%"),
                        html.P(f"Final Savings (Regular Income Strategy): ${comparison_df['Income_Savings'].iloc[-1]:.2f}"),
                        html.P(f"Final Savings (House Sell Strategy): ${comparison_df['House_Sell_Savings'].iloc[-1]:.2f}"),
                        html.P(f"Final Savings (Rent Strategy): ${comparison_df['Rent_Savings'].iloc[-1]:.2f}"),
                        html.P(f"Final Savings (Securities Strategy): ${comparison_df['Securities_Savings'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Inflation Details"),
                    dbc.CardBody([
                        html.P(f"Annual Inflation Rate: {inflation_rate if inflation_rate is not None else 0}%"),
                        html.P("Inflation Applied To: " + ", ".join([i.capitalize() for i in inflation_apply_to]) if inflation_apply_to else "None"),
                        html.P(f"Cumulative Inflation After {safe_term_years} Years: {(comparison_df['Inflation_Multiplier'].iloc[-1] - 1) * 100:.2f}%"),
                        html.P(f"Final Monthly Income: ${comparison_df['Inflation_Adjusted_Income'].iloc[-1]:.2f}" if apply_inflation_to_income else "Income Not Adjusted For Inflation"),
                        html.P(f"Final Monthly Expenses: ${comparison_df['Inflation_Adjusted_Expenses'].iloc[-1]:.2f}" if apply_inflation_to_expenses else "Expenses Not Adjusted For Inflation"),
                        html.P(f"Final Monthly Rent: ${comparison_df['Inflation_Adjusted_Rent'].iloc[-1]:.2f}" if apply_inflation_to_rent else "Rent Not Adjusted For Inflation"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Selling Securities Strategy"),
                    dbc.CardBody([
                        html.P(f"Securities Value: ${securities_value if securities_value is not None else 0:.2f}"),
                        html.P(f"Annual Growth Rate: {securities_growth_rate if securities_growth_rate is not None else 0}%"),
                        html.P(f"Sale Month: {securities_sell_month}" if securities_sell_month is not None and securities_sell_month > 0 else "Not Planning One-Time Sale"),
                        html.P("Monthly Sell Amount: " + (f"${securities_monthly_sell:.2f}" if securities_monthly_sell is not None and securities_monthly_sell > 0 else "Not Selling Monthly")),
                        html.P("All Proceeds Go To: Savings Account"),
                        html.P(f"Initial Existing House Value: ${existing_house_value if existing_house_value is not None else 0:.2f}"),
                        html.P(f"House Appreciation Rate: {existing_house_appreciation_rate if existing_house_appreciation_rate is not None else 3.0}%"),
                        html.P(f"Final Existing House Value: ${comparison_df['Existing_House_Value'].iloc[-1]:.2f}"),
                        html.P(f"Net Worth After {safe_term_years} Years: ${comparison_df['Securities_Net_Worth'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader("Combination Strategy: Rent + Sell Securities"),
                    dbc.CardBody([
                        html.P("This strategy combines renting out your existing house while also selling securities according to your settings."),
                        html.P(f"Rental Income: ${existing_house_rent if existing_house_rent is not None else 0:.2f} per month" + 
                               (f" (until house is sold at month {existing_house_sell_month})" if existing_house_sell_month is not None and existing_house_sell_month >= 0 else "")),
                        html.P(f"Securities Selling: {securities_sell_month if securities_sell_month is not None and securities_sell_month > 0 else 'Not a one-time sale'}, Monthly: ${securities_monthly_sell if securities_monthly_sell is not None else 0:.2f}"),
                        html.P(f"Final Savings: ${comparison_df['Combo_Savings'].iloc[-1]:.2f}"),
                        html.P(f"Net Worth After {safe_term_years} Years: ${comparison_df['Combo_Net_Worth'].iloc[-1]:.2f}"),
                    ]),
                ], className="mb-3"),
                
                dbc.Card([
                    dbc.CardHeader("Affordability Details"),
                    dbc.CardBody([
                        html.P(f"Primary Monthly Income: ${monthly_income if monthly_income is not None else 0:.2f}"),
                        html.P(f"Rental Income: ${existing_house_rent:.2f}" if existing_house_rent > 0 else "No Rental Income"),
                        html.P(f"Securities Monthly Income: ${securities_monthly_income:.2f}" if securities_monthly_income > 0 else "No Securities Monthly Income"),
                        html.P(f"Total Monthly Income: ${affordability['total_monthly_income']:.2f}", className="font-weight-bold"),
                        html.P(f"Monthly Expenses (excluding mortgage): ${monthly_expenses if monthly_expenses is not None else 0:.2f}"),
                        html.P(f"Monthly Mortgage Payment: ${monthly_payment:.2f}"),
                        html.P(f"Front-end Ratio: {affordability['front_end_ratio']:.2f}% (Recommended: <28%)"),
                        html.P(f"Back-end Ratio: {affordability['back_end_ratio']:.2f}% (Recommended: <36%)"),
                        html.P("Mortgage is " + 
                              ("affordable" if affordability['is_affordable'] else "not affordable") + 
                              " based on standard income ratio guidelines", 
                              className="text-success font-weight-bold" if affordability['is_affordable'] else "text-danger font-weight-bold"),
                    ]),
                ], className="mb-3"),

                html.H5("Recommendation"),
                html.P("Based on net worth after the loan term, the best strategy appears to be: " +
                       max(
                           ("Regular Income", comparison_df["Income_Net_Worth"].iloc[-1]),
                           ("Sell Existing House", comparison_df["House_Sell_Net_Worth"].iloc[-1]),
                           ("Rent Existing House", comparison_df["Rent_Net_Worth"].iloc[-1]),
                           ("Sell Securities", comparison_df["Securities_Net_Worth"].iloc[-1]),
                           ("Rent + Sell Securities", comparison_df["Combo_Net_Worth"].iloc[-1]),
                           key=lambda x: x[1],
                       )[0]),
            ]),
        ]),
    ])

    return payment_overview, cashflow_overview, affordability_overview, balance_fig, net_worth_fig, amortization_fig, securities_fig, savings_fig, cashflow_fig, inflation_fig, strategy_details

# Scenario Management Callbacks
@app.callback(
    Output("scenario-message", "children"),
    Input("save-scenario-button", "n_clicks"),
    [State("scenario-name", "value"),
     State("principal", "value"),
     State("annual-rate", "value"),
     State("term-years", "value"),
     State("monthly-income", "value"),
     State("monthly-expenses", "value"),
     State("existing-house-value", "value"),
     State("existing-house-appreciation-rate", "value"),
     State("existing-house-sell-month", "value"),
     State("existing-house-rent", "value"),
     State("savings-initial", "value"),
     State("savings-interest-rate", "value"),
     State("securities-value", "value"),
     State("securities-growth-rate", "value"),
     State("securities-sell-month", "value"),
     State("securities-monthly-sell", "value"),
     State("appreciation-rate", "value"),
     State("inflation-rate", "value"),
     State("inflation-apply-to", "value")],
    prevent_initial_call=True,
)
def save_scenario(n_clicks, scenario_name, principal, annual_rate, term_years,
                 monthly_income, monthly_expenses, existing_house_value,
                 existing_house_appreciation_rate, existing_house_sell_month,
                 existing_house_rent, savings_initial, savings_interest_rate,
                 securities_value, securities_growth_rate, securities_sell_month,
                 securities_monthly_sell, appreciation_rate, inflation_rate, inflation_apply_to):
    if not scenario_name:
        return html.P("Please enter a scenario name", className="text-danger")

    # Store all parameters in a dictionary
    stored_scenarios[scenario_name] = {
        "principal": principal,
        "annual_rate": annual_rate,
        "term_years": term_years,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "existing_house_value": existing_house_value,
        "existing_house_appreciation_rate": existing_house_appreciation_rate,
        "existing_house_sell_month": existing_house_sell_month,
        "existing_house_rent": existing_house_rent,
        "savings_initial": savings_initial,
        "savings_interest_rate": savings_interest_rate,
        "securities_value": securities_value,
        "securities_growth_rate": securities_growth_rate,
        "securities_sell_month": securities_sell_month,
        "securities_monthly_sell": securities_monthly_sell,
        "appreciation_rate": appreciation_rate,
        "inflation_rate": inflation_rate,
        "inflation_apply_to": inflation_apply_to,
    }

    return html.P(f"Scenario '{scenario_name}' saved successfully!", className="text-success")

@app.callback(
    Output("scenario-selector", "options"),
    [Input("save-scenario-button", "n_clicks"),
     Input("delete-scenario-button", "n_clicks")],
    prevent_initial_call=True,
)
def update_scenario_options(save_clicks, delete_clicks):
    # Update the dropdown options with the list of saved scenarios
    return [{"label": name, "value": name} for name in stored_scenarios]

@app.callback(
    [Output("compare-scenario-1", "options"),
     Output("compare-scenario-2", "options")],
    [Input("save-scenario-button", "n_clicks"),
     Input("delete-scenario-button", "n_clicks")],
    prevent_initial_call=True,
)
def update_comparison_scenario_options(save_clicks, delete_clicks):
    # Update the comparison dropdown options with the list of saved scenarios
    options = [{"label": name, "value": name} for name in stored_scenarios]
    return options, options

@app.callback(
    Output("scenario-message", "children", allow_duplicate=True),
    Input("delete-scenario-button", "n_clicks"),
    State("scenario-selector", "value"),
    prevent_initial_call=True,
)
def delete_scenario(n_clicks, scenario_name):
    if not scenario_name:
        return html.P("Please select a scenario to delete", className="text-danger")

    if scenario_name in stored_scenarios:
        del stored_scenarios[scenario_name]
        return html.P(f"Scenario '{scenario_name}' deleted successfully!", className="text-success")
    return html.P(f"Scenario '{scenario_name}' not found", className="text-danger")

@app.callback(
    [Output("principal", "value"),
     Output("annual-rate", "value"),
     Output("term-years", "value"),
     Output("monthly-income", "value"),
     Output("monthly-expenses", "value"),
     Output("existing-house-value", "value"),
     Output("existing-house-appreciation-rate", "value"),
     Output("existing-house-sell-month", "value"),
     Output("existing-house-rent", "value"),
     Output("savings-initial", "value"),
     Output("savings-interest-rate", "value"),
     Output("securities-value", "value"),
     Output("securities-growth-rate", "value"),
     Output("securities-sell-month", "value"),
     Output("securities-monthly-sell", "value"),
     Output("appreciation-rate", "value"),
     Output("inflation-rate", "value"),
     Output("inflation-apply-to", "value"),
     Output("scenario-message", "children", allow_duplicate=True)],
    Input("load-scenario-button", "n_clicks"),
    State("scenario-selector", "value"),
    prevent_initial_call=True,
)
def load_scenario(n_clicks, scenario_name):
    if not scenario_name:
        return [dash.no_update] * 18 + [html.P("Please select a scenario to load", className="text-danger")]

    if scenario_name in stored_scenarios:
        scenario = stored_scenarios[scenario_name]
        return [
            scenario["principal"],
            scenario["annual_rate"],
            scenario["term_years"],
            scenario["monthly_income"],
            scenario["monthly_expenses"],
            scenario["existing_house_value"],
            scenario["existing_house_appreciation_rate"],
            scenario["existing_house_sell_month"],
            scenario["existing_house_rent"],
            scenario["savings_initial"],
            scenario["savings_interest_rate"],
            scenario["securities_value"],
            scenario["securities_growth_rate"],
            scenario["securities_sell_month"],
            scenario["securities_monthly_sell"],
            scenario["appreciation_rate"],
            scenario["inflation_rate"],
            scenario["inflation_apply_to"],
            html.P(f"Scenario '{scenario_name}' loaded successfully!", className="text-success"),
        ]
    return [dash.no_update] * 18 + [html.P(f"Scenario '{scenario_name}' not found", className="text-danger")]

@app.callback(
    [Output("scenario-comparison-graph", "figure"),
     Output("scenario-comparison-summary", "children")],
    [Input("compare-scenario-1", "value"),
     Input("compare-scenario-2", "value"),
     Input("comparison-metric", "value")],
    prevent_initial_call=True,
)
def update_scenario_comparison(scenario1, scenario2, metric):
    if not scenario1 or not scenario2 or not metric:
        return go.Figure(), html.P("Please select two scenarios and a metric to compare", className="text-muted")

    if scenario1 not in stored_scenarios or scenario2 not in stored_scenarios:
        return go.Figure(), html.P("One or both of the selected scenarios doesn't exist", className="text-danger")

    # Generate data for first scenario
    s1 = stored_scenarios[scenario1]
    s1_annual_rate = s1["annual_rate"] / 100 if s1["annual_rate"] else 0
    s1_appreciation_rate = s1["appreciation_rate"] / 100 if s1["appreciation_rate"] else 0
    s1_existing_house_appreciation_rate = s1["existing_house_appreciation_rate"] / 100 if s1["existing_house_appreciation_rate"] else 0
    s1_savings_interest_rate = s1["savings_interest_rate"] / 100 if s1["savings_interest_rate"] else 0
    s1_securities_growth_rate = s1["securities_growth_rate"] / 100 if s1["securities_growth_rate"] else 0
    s1_inflation_rate = s1["inflation_rate"] / 100 if s1["inflation_rate"] else 0
    s1_apply_inflation_to_income = "income" in s1["inflation_apply_to"] if s1["inflation_apply_to"] else False
    s1_apply_inflation_to_expenses = "expenses" in s1["inflation_apply_to"] if s1["inflation_apply_to"] else False
    s1_apply_inflation_to_rent = "rent" in s1["inflation_apply_to"] if s1["inflation_apply_to"] else False
    # All proceeds go to savings (house_sale_to_securities is always False)
    s1_house_sale_to_securities = False

    s1_data = create_comparison_data(
        s1["principal"], s1_annual_rate, s1["term_years"],
        s1["monthly_income"], s1["monthly_expenses"],
        s1["existing_house_value"], s1["existing_house_sell_month"], s1["existing_house_rent"], s1_house_sale_to_securities,
        s1_existing_house_appreciation_rate,
        s1["securities_value"], s1_securities_growth_rate, s1["securities_sell_month"], s1["securities_monthly_sell"],
        s1["savings_initial"], s1_savings_interest_rate,
        s1_appreciation_rate,
        s1_inflation_rate, s1_apply_inflation_to_income, s1_apply_inflation_to_expenses, s1_apply_inflation_to_rent,
    )

    # Generate data for second scenario
    s2 = stored_scenarios[scenario2]
    s2_annual_rate = s2["annual_rate"] / 100 if s2["annual_rate"] else 0
    s2_appreciation_rate = s2["appreciation_rate"] / 100 if s2["appreciation_rate"] else 0
    s2_existing_house_appreciation_rate = s2["existing_house_appreciation_rate"] / 100 if s2["existing_house_appreciation_rate"] else 0
    s2_savings_interest_rate = s2["savings_interest_rate"] / 100 if s2["savings_interest_rate"] else 0
    s2_securities_growth_rate = s2["securities_growth_rate"] / 100 if s2["securities_growth_rate"] else 0
    s2_inflation_rate = s2["inflation_rate"] / 100 if s2["inflation_rate"] else 0
    s2_apply_inflation_to_income = "income" in s2["inflation_apply_to"] if s2["inflation_apply_to"] else False
    s2_apply_inflation_to_expenses = "expenses" in s2["inflation_apply_to"] if s2["inflation_apply_to"] else False
    s2_apply_inflation_to_rent = "rent" in s2["inflation_apply_to"] if s2["inflation_apply_to"] else False
    # All proceeds go to savings (house_sale_to_securities is always False)
    s2_house_sale_to_securities = False

    s2_data = create_comparison_data(
        s2["principal"], s2_annual_rate, s2["term_years"],
        s2["monthly_income"], s2["monthly_expenses"],
        s2["existing_house_value"], s2["existing_house_sell_month"], s2["existing_house_rent"], s2_house_sale_to_securities,
        s2_existing_house_appreciation_rate,
        s2["securities_value"], s2_securities_growth_rate, s2["securities_sell_month"], s2["securities_monthly_sell"],
        s2["savings_initial"], s2_savings_interest_rate,
        s2_appreciation_rate,
        s2_inflation_rate, s2_apply_inflation_to_income, s2_apply_inflation_to_expenses, s2_apply_inflation_to_rent,
    )

    # Create comparison figure
    fig = go.Figure()

    # Add first scenario trace
    fig.add_trace(go.Scatter(
        x=s1_data["Month"],
        y=s1_data[metric],
        mode="lines",
        name=f"{scenario1}",
    ))

    # Add second scenario trace
    fig.add_trace(go.Scatter(
        x=s2_data["Month"],
        y=s2_data[metric],
        mode="lines",
        name=f"{scenario2}",
    ))

    # Get the metric name for the title
    metric_name = next((opt["label"] for opt in [
        {"label": "Net Worth (Income Strategy)", "value": "Income_Net_Worth"},
        {"label": "Net Worth (House Sell Strategy)", "value": "House_Sell_Net_Worth"},
        {"label": "Net Worth (Rent Strategy)", "value": "Rent_Net_Worth"},
        {"label": "Net Worth (Securities Strategy)", "value": "Securities_Net_Worth"},
        {"label": "Net Worth (Rent + Sell Securities)", "value": "Combo_Net_Worth"},
        {"label": "Loan Balance (Income Strategy)", "value": "Income_Balance"},
        {"label": "Loan Balance (House Sell Strategy)", "value": "House_Sell_Balance"},
        {"label": "Loan Balance (Rent Strategy)", "value": "Rent_Balance"},
        {"label": "Loan Balance (Securities Strategy)", "value": "Securities_Balance"},
        {"label": "Loan Balance (Rent + Sell Securities)", "value": "Combo_Balance"},
        {"label": "Savings (Income Strategy)", "value": "Income_Savings"},
        {"label": "Savings (House Sell Strategy)", "value": "House_Sell_Savings"},
        {"label": "Savings (Rent Strategy)", "value": "Rent_Savings"},
        {"label": "Savings (Securities Strategy)", "value": "Securities_Savings"},
        {"label": "Savings (Rent + Sell Securities)", "value": "Combo_Savings"},
        {"label": "Monthly Cash Flow (Income Strategy)", "value": "Income_Monthly_Cashflow"},
        {"label": "Monthly Cash Flow (House Sell Strategy)", "value": "House_Sell_Monthly_Cashflow"},
        {"label": "Monthly Cash Flow (Rent Strategy)", "value": "Rent_Monthly_Cashflow"},
        {"label": "Monthly Cash Flow (Securities Strategy)", "value": "Securities_Monthly_Cashflow"},
        {"label": "Monthly Cash Flow (Rent + Sell Securities)", "value": "Combo_Monthly_Cashflow"},
    ] if opt["value"] == metric), "Selected Metric")

    fig.update_layout(
        title=f"Scenario Comparison: {metric_name}",
        xaxis_title="Month",
        yaxis_title="Value ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        height=600,  # Consistent height
        margin=dict(t=80, b=50, l=50, r=50),  # Consistent margins
    )

    # Create a summary of key differences
    s1_final = s1_data[metric].iloc[-1]
    s2_final = s2_data[metric].iloc[-1]
    difference = s2_final - s1_final
    percentage = (difference / abs(s1_final)) * 100 if s1_final != 0 else float("inf")

    summary = html.Div([
        html.H5("Comparison Summary"),
        html.P(f"Final {metric_name} value for {scenario1}: ${s1_final:.2f}"),
        html.P(f"Final {metric_name} value for {scenario2}: ${s2_final:.2f}"),
        html.P(f"Absolute Difference: ${abs(difference):.2f} ({scenario2} {'higher' if difference > 0 else 'lower'} than {scenario1})"),
        html.P(f"Percentage Difference: {abs(percentage):.2f}%"),
        html.H5("Key Parameter Differences"),
        html.Table([
            html.Thead(html.Tr([html.Th("Parameter"), html.Th(scenario1), html.Th(scenario2)])),
            html.Tbody([
                html.Tr([html.Td("Principal"), html.Td(f"${s1['principal']:,.2f}"), html.Td(f"${s2['principal']:,.2f}")]),
                html.Tr([html.Td("Interest Rate"), html.Td(f"{s1['annual_rate']}%"), html.Td(f"{s2['annual_rate']}%")]),
                html.Tr([html.Td("Term Years"), html.Td(s1["term_years"]), html.Td(s2["term_years"])]),
                html.Tr([html.Td("Monthly Income"), html.Td(f"${s1['monthly_income']:,.2f}"), html.Td(f"${s2['monthly_income']:,.2f}")]),
                html.Tr([html.Td("Monthly Expenses"), html.Td(f"${s1['monthly_expenses']:,.2f}"), html.Td(f"${s2['monthly_expenses']:,.2f}")]),
                html.Tr([html.Td("Inflation Rate"), html.Td(f"{s1['inflation_rate']}%"), html.Td(f"{s2['inflation_rate']}%")]),
                html.Tr([html.Td("Securities Growth Rate"), html.Td(f"{s1['securities_growth_rate']}%"), html.Td(f"{s2['securities_growth_rate']}%")]),
            ]),
        ], className="table table-striped table-bordered"),
    ])

    return fig, summary

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
