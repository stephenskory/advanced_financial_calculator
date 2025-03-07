# Advanced Mortgage Funding Calculator

An interactive dashboard that compares different strategies for funding a mortgage, including:

* Normal earned income
* Selling an existing house
* Renting an existing house
* Pledged asset mortgage
* Selling securities

## Features

- Compare multiple funding strategies side-by-side
- Visualize loan balances over time
- Track net worth across different strategies
- View detailed amortization schedules
- Monitor securities values and savings account growth over time
- Track monthly cash flow into/out of savings for each strategy
- Visualize savings cash flow over time with detailed charts
- Adjust parameters for all funding sources
- Apply inflation adjustments to income, expenses, and rental income
- Save and compare different scenarios with detailed comparison charts
- Receive strategy recommendations based on net worth outcomes
- Comprehensive unit tests covering all major components

## Screenshots

![Dashboard Preview](screenshot.png)

## Installation

1. Clone this repository
2. Create a virtual environment (recommended)
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required packages
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python app/mortgage_calculator.py
   ```
   Or use the convenience script:
   ```
   ./run.py
   ```
2. Open your web browser and navigate to:
   ```
   http://127.0.0.1:8050/
   ```
3. Adjust the parameters to match your financial situation
4. Click "Calculate" to see the results

## Running Tests

To run the comprehensive unit tests:

```
./run_tests.py
```

The tests cover various scenarios including:
- Normal mortgage calculations
- Edge cases (zero interest rate, very short terms)
- Zero value inputs (no income, no mortgage, etc.)
- Different combinations of strategies
- Inflation adjustments and their impact on cash flow
- Scenario storage and comparison functionality

## Parameters

### Mortgage Parameters
- Principal Amount: The total amount of the mortgage loan
- Annual Interest Rate: The annual interest rate of the mortgage
- Term: The length of the mortgage in years
- Home Appreciation Rate: The expected annual appreciation rate of the home

### Inflation Adjustments
- Annual Inflation Rate: The expected annual inflation rate
- Apply Inflation To: Select which values (income, expenses, rent) should be adjusted for inflation over time

### Income & Expenses
- Monthly Income: Your total monthly income
- Monthly Expenses: Your monthly expenses (excluding mortgage payments)

### Existing House
- Current Value: The value of your existing house, if any
- Sell in Month #: When you plan to sell your existing house (negative = don't sell)
- Sale Proceeds Destination: Choose to either pay down mortgage principal or buy securities
- Monthly Rental Income: Expected rental income if you rent out your existing house

### Savings Account
- Initial Balance: Starting balance of your savings account
- Annual Interest Rate: The annual interest rate on your savings account

### Securities
- Current Value: The total value of securities you own
- Annual Growth Rate: The expected annual growth rate of your securities
- Sell in Month #: When you plan to sell all your securities at once (0 = not selling all at once)
- Monthly Sell Amount: Amount of securities to sell each month (0 = not selling monthly)

### Scenario Management
- Scenario Name: Name for the current set of parameters
- Save Scenario: Store the current parameters for later comparison
- Load Scenario: Load a previously saved set of parameters
- Delete Scenario: Remove a saved scenario
- Scenario Comparison: Compare the outcomes of two saved scenarios side-by-side

## Technical Details

This application is built using:

- [Dash](https://dash.plotly.com/) - A Python framework for building web applications
- [Plotly](https://plotly.com/python/) - For interactive data visualization
- [Pandas](https://pandas.pydata.org/) - For data manipulation
- [NumPy](https://numpy.org/) - For numerical calculations
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/) - For responsive layout

## License

MIT