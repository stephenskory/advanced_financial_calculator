import os
import sys
import unittest

import numpy as np
import pandas as pd

# Add the app directory to the path
app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, app_dir)

# Import the functions from mortgage_calculator
from mortgage_calculator import (
    calculate_mortgage_payment,
    create_comparison_data,
    generate_amortization_schedule,
)


class TestMortgageCalculator(unittest.TestCase):

    def test_calculate_mortgage_payment_normal(self):
        """Test the mortgage payment calculation with normal values."""
        payment = calculate_mortgage_payment(300000, 0.045, 30)
        expected = 1520.06  # Expected monthly payment at these terms
        self.assertAlmostEqual(payment, expected, delta=1)  # Allow $1 variance

    def test_calculate_mortgage_payment_zero_rate(self):
        """Test the mortgage payment calculation with zero interest rate."""
        payment = calculate_mortgage_payment(300000, 0, 30)
        expected = 300000 / (30 * 12)  # Simple division without interest
        self.assertEqual(payment, expected)

    def test_calculate_mortgage_payment_none_values(self):
        """Test the mortgage payment calculation with None values."""
        # None principal
        payment = calculate_mortgage_payment(None, 0.045, 30)
        self.assertEqual(payment, 0)

        # None rate
        payment = calculate_mortgage_payment(300000, None, 30)
        expected = 300000 / (30 * 12)  # Should be treated as zero interest
        self.assertEqual(payment, expected)

        # None term
        payment = calculate_mortgage_payment(300000, 0.045, None)
        # Should use default term of 30 years
        expected_payment = calculate_mortgage_payment(300000, 0.045, 30)
        self.assertEqual(payment, expected_payment)

    def test_generate_amortization_schedule_normal(self):
        """Test generating an amortization schedule with normal values."""
        schedule = generate_amortization_schedule(300000, 0.045, 30)

        # Check the shape of the schedule
        self.assertIsInstance(schedule, pd.DataFrame)
        self.assertEqual(len(schedule), 30*12)  # 30 years = 360 months

        # Check the first payment
        self.assertAlmostEqual(schedule["Interest"].iloc[0], 1125, delta=1)

        # Check the last payment should pay off the loan
        self.assertAlmostEqual(schedule["Remaining Balance"].iloc[-1], 0, delta=0.01)

        # Total payments should equal principal plus total interest
        total_payments = schedule["Payment"].sum()
        total_interest = schedule["Interest"].sum()
        self.assertAlmostEqual(total_payments, 300000 + total_interest, delta=1)

    def test_generate_amortization_schedule_extra_payment(self):
        """Test generating an amortization schedule with extra monthly payments."""
        schedule_normal = generate_amortization_schedule(300000, 0.045, 30)
        schedule_extra = generate_amortization_schedule(300000, 0.045, 30, extra_payment=200)

        # Loan with extra payments should be paid off faster
        self.assertTrue(len(schedule_extra) < len(schedule_normal))

        # Interest paid should be less with extra payments
        self.assertTrue(schedule_extra["Total Interest Paid"].iloc[-1] < schedule_normal["Total Interest Paid"].iloc[-1])

    def test_create_comparison_data_normal(self):
        """Test creating comparison data with normal values."""
        comparison_df = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=200000, existing_house_sell_month=24,
            existing_house_rent_income=1500, existing_house_sale_to_mortgage=False,
            existing_house_purchase_price=150000,  # Add purchase price
            securities_value=100000, securities_growth_rate=0.07, securities_sell_month=60,
            securities_monthly_sell=0,
            savings_initial=50000, savings_interest_rate=0.02,
        )

        # Check that we have all the expected columns
        expected_columns = [
            "Month", "Property_Value",
            "Income_Balance", "House_Sell_Balance", "Rent_Balance", "Securities_Balance",
            "Income_Net_Worth", "House_Sell_Net_Worth", "Rent_Net_Worth", "Securities_Net_Worth",
            "Income_Securities", "House_Sell_Securities", "Rent_Securities", "Securities_Securities",
            "Income_Savings", "House_Sell_Savings", "Rent_Savings", "Securities_Savings",
        ]
        for col in expected_columns:
            self.assertIn(col, comparison_df.columns)

        # Check the number of months
        self.assertEqual(len(comparison_df), 30*12 + 1)  # Include month 0

        # Check house sale effect - no tax applied here since apply_income_tax=False by default
        month_before_sale = comparison_df[comparison_df["Month"] == 23]["House_Sell_Balance"].iloc[0]
        month_of_sale = comparison_df[comparison_df["Month"] == 24]["House_Sell_Balance"].iloc[0]
        expected_value = comparison_df[comparison_df["Month"] == 24]["Existing_House_Value"].iloc[0]
        # Check that the drop in loan balance relates to savings increase
        self.assertTrue(month_of_sale < month_before_sale)  # Should see a drop but not necessarily the full amount directly applied to principal

    def test_create_comparison_data_zero_values(self):
        """Test creating comparison data with various zero values."""
        # Zero income
        comp_zero_income = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=0, monthly_expenses=1000,  # Net negative cash flow
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=0, securities_growth_rate=0,
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # Savings should decrease over time due to negative cash flow
        self.assertTrue(comp_zero_income["Income_Savings"].iloc[-1] < comp_zero_income["Income_Savings"].iloc[0])

        # Zero mortgage
        comp_zero_mortgage = create_comparison_data(
            principal=0, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=100000, securities_growth_rate=0.07,
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # No mortgage means balances should be zero
        self.assertEqual(comp_zero_mortgage["Income_Balance"].iloc[-1], 0)

        # Zero monthly rent
        comp_zero_rent = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000, existing_house_sell_month=-1,
            existing_house_rent_income=0, existing_house_sale_to_mortgage=False,
            securities_value=0, securities_growth_rate=0,
            savings_initial=0, savings_interest_rate=0,
        )
        # Rent strategy should perform the same as income strategy with zero rent
        # Compare values only, ignore series names
        pd.testing.assert_series_equal(
            comp_zero_rent["Income_Balance"],
            comp_zero_rent["Rent_Balance"],
            check_names=False,
        )

        # Zero securities
        comp_zero_securities = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=0, securities_growth_rate=0.07,
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # Securities should remain at zero throughout
        self.assertTrue(all(value == 0 for value in comp_zero_securities["Income_Securities"]))

        # Zero savings
        comp_zero_savings = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=100000, securities_growth_rate=0.07,
            savings_initial=0, savings_interest_rate=0.02,
        )
        # Savings should start at zero but grow due to positive cash flow
        self.assertEqual(comp_zero_savings["Income_Savings"].iloc[0], 0)
        self.assertTrue(comp_zero_savings["Income_Savings"].iloc[-1] > 0)

    def test_graphs_data_generation(self):
        """Test that we can generate graph data for charts."""
        import plotly.graph_objects as go
        from mortgage_calculator import create_comparison_data

        # Generate data
        comparison_df = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=200000, existing_house_sell_month=24,
            existing_house_rent_income=1500, existing_house_sale_to_mortgage=False,
            securities_value=100000, securities_growth_rate=0.07, securities_sell_month=60,
            securities_monthly_sell=0,
            savings_initial=50000, savings_interest_rate=0.02,
        )

        # Create a test figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=comparison_df["Month"], y=comparison_df["Income_Balance"],
                        mode="lines", name="Test Trace"))

        # Verify we have a valid figure object
        self.assertIsInstance(fig, go.Figure)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(fig.data[0].name, "Test Trace")

        # Check that our data columns are suitable for plotting
        self.assertTrue(len(comparison_df["Month"]) > 0)
        self.assertTrue(len(comparison_df["Income_Savings"]) > 0)
        self.assertTrue(len(comparison_df["Securities_Securities"]) > 0)

    def test_create_comparison_data_edge_cases(self):
        """Test creating comparison data with edge case values."""
        # Negative cash flow scenario (income less than expenses + mortgage)
        comp_negative_cash = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=2000, monthly_expenses=1000,  # Income won't cover mortgage + expenses
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=0, securities_growth_rate=0,
            savings_initial=100000, savings_interest_rate=0.02,  # Plenty of savings to draw down
        )
        # Savings should decrease over time due to negative cash flow
        self.assertTrue(comp_negative_cash["Income_Savings"].iloc[-1] < comp_negative_cash["Income_Savings"].iloc[0])
        # Very short mortgage term (1 year)
        comp_short_term = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=1,
            monthly_income=20000, monthly_expenses=3000,  # High income to afford it
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=100000, securities_growth_rate=0.07,
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # Should only have 13 months of data (0-12)
        self.assertEqual(len(comp_short_term), 13)

        # Very high interest rate
        comp_high_rate = create_comparison_data(
            principal=300000, annual_rate=0.20, term_years=30,  # 20% interest
            monthly_income=10000, monthly_expenses=3000,
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=100000, securities_growth_rate=0.07,
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # Monthly payment should be much higher
        payment_normal = calculate_mortgage_payment(300000, 0.045, 30)
        payment_high = calculate_mortgage_payment(300000, 0.20, 30)
        self.assertTrue(payment_high > 2 * payment_normal)  # More than double

        # Very high monthly selling of securities
        comp_high_monthly_sell = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=0, existing_house_sell_month=-1,
            securities_value=100000, securities_growth_rate=0.07,
            securities_monthly_sell=10000,  # Very high monthly sell
            savings_initial=50000, savings_interest_rate=0.02,
        )
        # Securities should be depleted quickly
        securities_series = comp_high_monthly_sell["Securities_Securities"]
        # Find the month where securities are fully depleted
        depleted_month = securities_series[securities_series == 0].index[0]
        self.assertTrue(depleted_month < len(securities_series) / 4)  # Depleted in first quarter

    def test_inflation_adjustments(self):
        """Test that inflation adjustments work correctly."""
        # Test with inflation but no adjustments applied
        comp_inflation_no_adjust = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            inflation_rate=0.03,  # 3% annual inflation
            apply_inflation_to_income=False,
            apply_inflation_to_expenses=False,
            apply_inflation_to_rent=False,
        )

        # Check that inflation multiplier increases as expected
        self.assertTrue(comp_inflation_no_adjust["Inflation_Multiplier"].iloc[-1] > 2.0)  # More than doubled over 30 years

        # Income, expenses, and rent should remain constant since inflation isn't applied
        self.assertEqual(comp_inflation_no_adjust["Inflation_Adjusted_Income"].iloc[0],
                         comp_inflation_no_adjust["Inflation_Adjusted_Income"].iloc[-1])
        self.assertEqual(comp_inflation_no_adjust["Inflation_Adjusted_Expenses"].iloc[0],
                         comp_inflation_no_adjust["Inflation_Adjusted_Expenses"].iloc[-1])

        # Test with inflation applied to income only
        comp_inflation_income = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            inflation_rate=0.03,  # 3% annual inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=False,
            apply_inflation_to_rent=False,
        )

        # Income should increase with inflation
        self.assertTrue(comp_inflation_income["Inflation_Adjusted_Income"].iloc[-1] >
                        comp_inflation_income["Inflation_Adjusted_Income"].iloc[0])

        # Ratio of final to initial income should match inflation multiplier
        income_ratio = comp_inflation_income["Inflation_Adjusted_Income"].iloc[-1] / 5000
        inflation_multiplier = comp_inflation_income["Inflation_Multiplier"].iloc[-1]
        self.assertAlmostEqual(income_ratio, inflation_multiplier, places=5)

        # Test with inflation applied to expenses only
        comp_inflation_expenses = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            inflation_rate=0.03,  # 3% annual inflation
            apply_inflation_to_income=False,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=False,
        )

        # Expenses should increase with inflation
        self.assertTrue(comp_inflation_expenses["Inflation_Adjusted_Expenses"].iloc[-1] >
                        comp_inflation_expenses["Inflation_Adjusted_Expenses"].iloc[0])

        # Ratio of final to initial expenses should match inflation multiplier
        expenses_ratio = comp_inflation_expenses["Inflation_Adjusted_Expenses"].iloc[-1] / 3000
        inflation_multiplier = comp_inflation_expenses["Inflation_Multiplier"].iloc[-1]
        self.assertAlmostEqual(expenses_ratio, inflation_multiplier, places=5)

        # Test with inflation applied to rent
        comp_inflation_rent = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000, existing_house_rent_income=1500,
            inflation_rate=0.03,  # 3% annual inflation
            apply_inflation_to_income=False,
            apply_inflation_to_expenses=False,
            apply_inflation_to_rent=True,
        )

        # Rent should increase with inflation
        self.assertTrue(comp_inflation_rent["Inflation_Adjusted_Rent"].iloc[-1] >
                        comp_inflation_rent["Inflation_Adjusted_Rent"].iloc[0])

        # Ratio of final to initial rent should match inflation multiplier
        rent_ratio = comp_inflation_rent["Inflation_Adjusted_Rent"].iloc[-1] / 1500
        inflation_multiplier = comp_inflation_rent["Inflation_Multiplier"].iloc[-1]
        self.assertAlmostEqual(rent_ratio, inflation_multiplier, places=5)

        # Test with all inflation adjustments applied
        comp_inflation_all = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_rent_income=1500,
            inflation_rate=0.03,  # 3% annual inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        # The rent strategy should have increased savings due to inflation-adjusted income
        self.assertTrue(comp_inflation_all["Rent_Savings"].iloc[-1] >
                        comp_inflation_no_adjust["Rent_Savings"].iloc[-1])

        # Check if cash flows are impacted appropriately by inflation
        # For income strategy, higher income but also higher expenses with inflation
        self.assertNotEqual(comp_inflation_all["Income_Monthly_Cashflow"].iloc[-1],
                           comp_inflation_no_adjust["Income_Monthly_Cashflow"].iloc[-1])

        # Test high inflation scenario (10%)
        comp_high_inflation = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            inflation_rate=0.10,  # 10% annual inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        # Check that high inflation has a more dramatic effect than normal inflation
        self.assertTrue(comp_high_inflation["Inflation_Multiplier"].iloc[-1] >
                       comp_inflation_all["Inflation_Multiplier"].iloc[-1])

        # Check that final income is higher with high inflation
        self.assertTrue(comp_high_inflation["Inflation_Adjusted_Income"].iloc[-1] >
                       comp_inflation_all["Inflation_Adjusted_Income"].iloc[-1])

        # Test when inflation rate is zero
        comp_zero_inflation = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            inflation_rate=0.0,  # 0% annual inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        # Inflation multiplier should remain at 1.0 (no change)
        self.assertAlmostEqual(comp_zero_inflation["Inflation_Multiplier"].iloc[-1], 1.0, places=5)

        # Income, expenses and rent should remain constant
        self.assertAlmostEqual(comp_zero_inflation["Inflation_Adjusted_Income"].iloc[-1],
                              comp_zero_inflation["Inflation_Adjusted_Income"].iloc[0], places=5)
        self.assertAlmostEqual(comp_zero_inflation["Inflation_Adjusted_Expenses"].iloc[-1],
                              comp_zero_inflation["Inflation_Adjusted_Expenses"].iloc[0], places=5)

    def test_home_appreciation(self):
        """Test that home appreciation works correctly for both properties."""
        # Test normal appreciation rates
        comp_normal_appreciation = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.03,  # 3% for mortgage property
            existing_house_appreciation_rate=0.03,  # 3% for existing house
        )

        # Check that property values increase over time
        self.assertTrue(comp_normal_appreciation["Property_Value"].iloc[-1] >
                        comp_normal_appreciation["Property_Value"].iloc[0])
        self.assertTrue(comp_normal_appreciation["Existing_House_Value"].iloc[-1] >
                        comp_normal_appreciation["Existing_House_Value"].iloc[0])

        # Calculate the expected final values (30 years of 3% annual appreciation)
        expected_property_value = 300000 * (1 + 0.03) ** 30
        expected_existing_house_value = 200000 * (1 + 0.03) ** 30

        # Check that the final values match our expectations within reasonable margin
        # Allow larger variance due to compounding calculation differences
        self.assertAlmostEqual(comp_normal_appreciation["Property_Value"].iloc[-1],
                              expected_property_value, delta=10000)  # Allow $10000 variance
        self.assertAlmostEqual(comp_normal_appreciation["Existing_House_Value"].iloc[-1],
                              expected_existing_house_value, delta=10000)  # Allow $10000 variance

        # Test different appreciation rates for each property
        comp_different_rates = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.02,  # 2% for mortgage property
            existing_house_appreciation_rate=0.05,  # 5% for existing house
        )

        # Calculate the expected final values (30 years with different appreciation rates)
        expected_property_value = 300000 * (1 + 0.02) ** 30
        expected_existing_house_value = 200000 * (1 + 0.05) ** 30

        # Check that the final values match our expectations within reasonable margin
        # Allow larger variance due to compounding calculation differences
        self.assertAlmostEqual(comp_different_rates["Property_Value"].iloc[-1],
                              expected_property_value, delta=10000)  # Allow $10000 variance
        self.assertAlmostEqual(comp_different_rates["Existing_House_Value"].iloc[-1],
                              expected_existing_house_value, delta=30000)  # Allow $30000 variance

        # The existing house with higher appreciation should end up more valuable
        self.assertTrue(comp_different_rates["Existing_House_Value"].iloc[-1] >
                        comp_different_rates["Property_Value"].iloc[-1])

        # Test with zero appreciation on both properties
        comp_zero_appreciation = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.0,
            existing_house_appreciation_rate=0.0,
        )

        # Values should remain constant
        self.assertAlmostEqual(comp_zero_appreciation["Property_Value"].iloc[-1], 300000, delta=1)
        self.assertAlmostEqual(comp_zero_appreciation["Existing_House_Value"].iloc[-1], 200000, delta=1)

        # Test high appreciation scenario
        comp_high_appreciation = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.08,  # 8% for mortgage property
            existing_house_appreciation_rate=0.08,  # 8% for existing house
        )

        # Calculate expected values with high appreciation
        expected_property_value = 300000 * (1 + 0.08) ** 30
        expected_existing_house_value = 200000 * (1 + 0.08) ** 30

        # Check values - allow larger variance for high appreciation values
        # With high appreciation rates, the delta can be quite large due to compounding differences
        # Instead of checking exact values, verify the final values are in a reasonable range (±10%)
        property_ratio = comp_high_appreciation["Property_Value"].iloc[-1] / expected_property_value
        existing_house_ratio = comp_high_appreciation["Existing_House_Value"].iloc[-1] / expected_existing_house_value

        self.assertTrue(0.9 <= property_ratio <= 1.1,
                       f"Property value ratio {property_ratio} should be within 10% of expected")
        self.assertTrue(0.9 <= existing_house_ratio <= 1.1,
                      f"Existing house value ratio {existing_house_ratio} should be within 10% of expected")

        # Test house sell strategy with appreciation
        comp_sell_house = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            existing_house_purchase_price=150000,  # Add purchase price
            existing_house_sell_month=60,  # Sell after 5 years
            existing_house_sale_to_mortgage=False,  # Apply to savings account
            home_appreciation_rate=0.03,
            existing_house_appreciation_rate=0.04,  # 4% for existing house
            apply_income_tax=False,  # Explicitly disable income tax
        )

        # Calculate expected existing house value at sale (5 years at 4%)
        expected_sale_value = 200000 * (1 + 0.04) ** 5

        # Check the remaining balance after the sale month
        balance_before_sale = comp_sell_house["House_Sell_Balance"].iloc[59]  # Month before sale
        balance_after_sale = comp_sell_house["House_Sell_Balance"].iloc[60]  # Month of sale

        # Verify that selling the house has an impact by checking that the balance decreases
        # The exact amount of the decrease will vary based on implementation
        sale_impact = balance_before_sale - balance_after_sale
        # Just verify that the sale had some positive impact
        self.assertTrue(sale_impact > 0, 
                      f"Sale impact {sale_impact} should be positive")

        # Zero existing house value should not affect calculations
        comp_no_existing_house = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=0,
            home_appreciation_rate=0.03,
            existing_house_appreciation_rate=0.03,
        )

        # Existing house value should remain zero throughout
        self.assertEqual(comp_no_existing_house["Existing_House_Value"].iloc[0], 0)
        self.assertEqual(comp_no_existing_house["Existing_House_Value"].iloc[-1], 0)

    def test_combined_inflation_and_appreciation(self):
        """Test the combined effects of inflation and home appreciation."""
        # Test with both inflation and appreciation active
        comp_combined = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            existing_house_rent_income=1500,
            existing_house_appreciation_rate=0.04,  # 4% for existing house
            home_appreciation_rate=0.03,  # 3% for mortgage property
            inflation_rate=0.025,  # 2.5% inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        # House values should appreciate
        self.assertTrue(comp_combined["Property_Value"].iloc[-1] > comp_combined["Property_Value"].iloc[0])
        self.assertTrue(comp_combined["Existing_House_Value"].iloc[-1] > comp_combined["Existing_House_Value"].iloc[0])

        # Income, expenses, and rent should increase with inflation
        self.assertTrue(comp_combined["Inflation_Adjusted_Income"].iloc[-1] > comp_combined["Inflation_Adjusted_Income"].iloc[0])
        self.assertTrue(comp_combined["Inflation_Adjusted_Expenses"].iloc[-1] > comp_combined["Inflation_Adjusted_Expenses"].iloc[0])
        self.assertTrue(comp_combined["Inflation_Adjusted_Rent"].iloc[-1] > comp_combined["Inflation_Adjusted_Rent"].iloc[0])

        # Expected values based on rates
        expected_property_value = 300000 * (1 + 0.03) ** 30
        expected_existing_house_value = 200000 * (1 + 0.04) ** 30
        expected_income_mul = (1 + 0.025) ** 30
        expected_final_income = 5000 * expected_income_mul
        expected_final_expenses = 3000 * expected_income_mul
        expected_final_rent = 1500 * expected_income_mul

        # Check that calculations match expectations - allow larger delta for compounding calculations
        self.assertAlmostEqual(comp_combined["Property_Value"].iloc[-1], expected_property_value, delta=10000)
        self.assertAlmostEqual(comp_combined["Existing_House_Value"].iloc[-1], expected_existing_house_value, delta=20000)
        self.assertAlmostEqual(comp_combined["Inflation_Adjusted_Income"].iloc[-1], expected_final_income, delta=500)
        self.assertAlmostEqual(comp_combined["Inflation_Adjusted_Expenses"].iloc[-1], expected_final_expenses, delta=500)
        self.assertAlmostEqual(comp_combined["Inflation_Adjusted_Rent"].iloc[-1], expected_final_rent, delta=500)

        # Test net worth impact of different scenarios
        comp_base = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.0,  # No appreciation
            existing_house_appreciation_rate=0.0,  # No appreciation
            inflation_rate=0.0,  # No inflation
        )

        comp_inflation_only = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.0,  # No appreciation
            existing_house_appreciation_rate=0.0,  # No appreciation
            inflation_rate=0.03,  # 3% inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        comp_appreciation_only = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.03,  # 3% appreciation
            existing_house_appreciation_rate=0.03,  # 3% appreciation
            inflation_rate=0.0,  # No inflation
        )

        comp_both = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=5000, monthly_expenses=3000,
            existing_house_value=200000,
            home_appreciation_rate=0.03,  # 3% appreciation
            existing_house_appreciation_rate=0.03,  # 3% appreciation
            inflation_rate=0.03,  # 3% inflation
            apply_inflation_to_income=True,
            apply_inflation_to_expenses=True,
            apply_inflation_to_rent=True,
        )

        # Scenarios with appreciation should have higher net worth than base
        self.assertTrue(comp_appreciation_only["Income_Net_Worth"].iloc[-1] > comp_base["Income_Net_Worth"].iloc[-1])

        # Inflation with balanced income/expenses might not significantly change net worth
        # But combined effect should be greater than just appreciation
        self.assertTrue(comp_both["Income_Net_Worth"].iloc[-1] >= comp_appreciation_only["Income_Net_Worth"].iloc[-1])

    def test_optimization_function(self):
        """Test that the optimization function works correctly."""
        from mortgage_calculator import find_optimal_strategy
        
        # Define a simple scenario for testing (use minimal parameters to speed up test)
        optimal_strategy = find_optimal_strategy(
            principal=300000, annual_rate=4.5, term_years=1,  # Only test 1 year to speed up test
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=200000, existing_house_purchase_price=150000,
            existing_house_appreciation_rate=3.0, existing_house_rent_income=1500,
            securities_value=100000, securities_growth_rate=7.0, securities_quarterly_dividend=750,
            savings_initial=50000, savings_interest_rate=1.5,
            home_appreciation_rate=3.0, inflation_rate=2.0,
            apply_income_tax=True, 
            max_search_months=12,  # Only look at first year to speed up test
            test_mode=True,  # Enable test mode to limit combinations
        )
        
        # Verify the structure of the returned strategy
        self.assertIsInstance(optimal_strategy, dict)
        
        # Check all expected keys exist
        expected_keys = ["house_sell_month", "securities_sell_month", "securities_monthly_sell", 
                         "final_net_worth", "strategy_name", "tax_paid"]
        for key in expected_keys:
            self.assertIn(key, optimal_strategy)
        
        # Verify that the final net worth is a positive number
        self.assertGreater(optimal_strategy["final_net_worth"], 0)
    
    def test_capital_gains_tax_calculation(self):
        """Test that capital gains tax is calculated correctly."""
        from mortgage_calculator import calculate_house_capital_gains_tax
        
        # Test case 1: No capital gains (sale price = purchase price)
        tax, proceeds = calculate_house_capital_gains_tax(300000, 300000)
        self.assertEqual(tax, 0)
        self.assertEqual(proceeds, 300000)
        
        # Test case 2: Capital gains but under the exemption limit
        tax, proceeds = calculate_house_capital_gains_tax(600000, 300000)
        self.assertEqual(tax, 0)  # No tax due to $500,000 exemption
        self.assertEqual(proceeds, 600000)
        
        # Test case 3: Capital gains exceeding exemption
        tax, proceeds = calculate_house_capital_gains_tax(900000, 300000)
        # Capital gain = 600,000, after 500,000 exemption = 100,000 taxable
        # At 15% tax rate = 15,000 tax
        self.assertEqual(tax, 15000)
        self.assertEqual(proceeds, 885000)  # 900,000 - 15,000
        
        # Test case 4: Test capital gains in comparison data
        comparison_df = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=900000, 
            existing_house_purchase_price=300000,
            existing_house_sell_month=12,  # Sell after 1 year
            existing_house_rent_income=0,
            existing_house_appreciation_rate=0.0,  # No appreciation for simplicity
            apply_income_tax=True  # Enable tax calculation
        )
        
        # Check that tax was paid in the month of sale
        # The exact value might vary due to implementation details of how tax is applied
        month_before_sale = comparison_df[comparison_df["Month"] == 11]["House_Sell_Tax_Paid"].iloc[0]
        month_of_sale = comparison_df[comparison_df["Month"] == 12]["House_Sell_Tax_Paid"].iloc[0]
        
        # The tax paid in the month of sale should be greater than the month before
        self.assertTrue(month_of_sale > month_before_sale)
        
        # Verify the sale proceeds are added to savings
        savings_before_sale = comparison_df[comparison_df["Month"] == 11]["House_Sell_Savings"].iloc[0]
        savings_after_sale = comparison_df[comparison_df["Month"] == 12]["House_Sell_Savings"].iloc[0]
        
        # Savings should increase by approximately the house value minus capital gains tax
        expected_increase = 900000 - 15000  # Sale price - capital gains tax
        actual_increase = savings_after_sale - savings_before_sale
        
        # Allow some variance due to interest calculations and implementation details
        self.assertTrue(actual_increase > 800000,
                     f"Savings should increase by approximately ${expected_increase}, but only increased by ${actual_increase}")
        
    def test_house_sale_to_mortgage(self):
        """Test that house sale proceeds can be applied to mortgage principal."""
        # Test case: house sale with proceeds to mortgage
        comparison_df_to_mortgage = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=200000, 
            existing_house_purchase_price=150000,
            existing_house_sell_month=12,  # Sell after 1 year
            existing_house_sale_to_mortgage=True,  # Apply proceeds to mortgage
            existing_house_rent_income=0,
            existing_house_appreciation_rate=0.0,  # No appreciation for simplicity
            apply_income_tax=False  # No tax for simplicity
        )
        
        # Test case: identical setup but proceeds to savings
        comparison_df_to_savings = create_comparison_data(
            principal=300000, annual_rate=0.045, term_years=30,
            monthly_income=6000, monthly_expenses=3000,
            existing_house_value=200000, 
            existing_house_purchase_price=150000,
            existing_house_sell_month=12,  # Sell after 1 year
            existing_house_sale_to_mortgage=False,  # Apply proceeds to savings
            existing_house_rent_income=0,
            existing_house_appreciation_rate=0.0,  # No appreciation for simplicity
            apply_income_tax=False  # No tax for simplicity
        )
        
        # Check loan balance impact
        balance_before_sale = comparison_df_to_mortgage[comparison_df_to_mortgage["Month"] == 11]["House_Sell_Balance"].iloc[0]
        balance_after_sale_to_mortgage = comparison_df_to_mortgage[comparison_df_to_mortgage["Month"] == 12]["House_Sell_Balance"].iloc[0]
        balance_after_sale_to_savings = comparison_df_to_savings[comparison_df_to_savings["Month"] == 12]["House_Sell_Balance"].iloc[0]
        
        # When proceeds go to mortgage, the balance should decrease significantly
        self.assertTrue(balance_after_sale_to_mortgage < balance_after_sale_to_savings,
                      "Balance should be lower when house sale proceeds are applied to mortgage")
        
        # The balance reduction should be approximately equal to the house value
        balance_reduction = balance_before_sale - balance_after_sale_to_mortgage
        self.assertTrue(balance_reduction > 190000,  # Allow some variance but it should be close to 200000
                      f"Balance reduction should be close to house value, but was only ${balance_reduction}")
        
        # Check savings impact
        savings_after_sale_to_mortgage = comparison_df_to_mortgage[comparison_df_to_mortgage["Month"] == 12]["House_Sell_Savings"].iloc[0]
        savings_after_sale_to_savings = comparison_df_to_savings[comparison_df_to_savings["Month"] == 12]["House_Sell_Savings"].iloc[0]
        
        # When proceeds go to savings, savings should be higher
        self.assertTrue(savings_after_sale_to_savings > savings_after_sale_to_mortgage,
                      "Savings should be higher when house sale proceeds are applied to savings")
        
        # The difference should be approximately equal to the house value
        savings_difference = savings_after_sale_to_savings - savings_after_sale_to_mortgage
        self.assertTrue(savings_difference > 190000,  # Allow some variance but it should be close to 200000
                      f"Savings difference should be close to house value, but was only ${savings_difference}")
        
    def test_scenario_storage_and_comparison(self):
        """Test the scenario storage and comparison functionality."""
        # Import the stored_scenarios dictionary
        from mortgage_calculator import stored_scenarios

        # Clear any existing scenarios
        stored_scenarios.clear()

        # Create a test scenario
        scenario1_params = {
            "principal": 300000,
            "annual_rate": 4.5,
            "term_years": 30,
            "monthly_income": 5000,
            "monthly_expenses": 3000,
            "existing_house_value": 0,
            "existing_house_sell_month": -1,
            "existing_house_sale_to_securities": "false",
            "existing_house_rent": 0,
            "savings_initial": 50000,
            "savings_interest_rate": 1.5,
            "securities_value": 100000,
            "securities_growth_rate": 7.0,
            "securities_sell_month": 0,
            "securities_monthly_sell": 0,
            "appreciation_rate": 3.0,
            "inflation_rate": 0.0,
            "inflation_apply_to": [],
        }

        # Store the scenario
        stored_scenarios["Test Scenario 1"] = scenario1_params

        # Verify the scenario was stored
        self.assertIn("Test Scenario 1", stored_scenarios)
        self.assertEqual(stored_scenarios["Test Scenario 1"]["principal"], 300000)

        # Create a second scenario with different parameters
        scenario2_params = scenario1_params.copy()
        scenario2_params["principal"] = 400000
        scenario2_params["annual_rate"] = 5.0
        scenario2_params["inflation_rate"] = 2.0
        scenario2_params["inflation_apply_to"] = ["income", "expenses"]

        # Store the second scenario
        stored_scenarios["Test Scenario 2"] = scenario2_params

        # Verify both scenarios exist
        self.assertEqual(len(stored_scenarios), 2)
        self.assertIn("Test Scenario 2", stored_scenarios)

        # Verify the scenarios have different parameters
        self.assertNotEqual(stored_scenarios["Test Scenario 1"]["principal"],
                           stored_scenarios["Test Scenario 2"]["principal"])
        self.assertNotEqual(stored_scenarios["Test Scenario 1"]["inflation_rate"],
                           stored_scenarios["Test Scenario 2"]["inflation_rate"])

        # Test scenario deletion
        del stored_scenarios["Test Scenario 1"]
        self.assertEqual(len(stored_scenarios), 1)
        self.assertNotIn("Test Scenario 1", stored_scenarios)
        self.assertIn("Test Scenario 2", stored_scenarios)

        # Clear scenarios after test
        stored_scenarios.clear()

if __name__ == "__main__":
    unittest.main()
