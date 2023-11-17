#Step 1: Import the required libraries
import requests
import json
from fredapi import Fred
import numpy as np

#Step 2: Defining the function to scrape financial data, here The function takes input of a desired stock ticker and scrapes financial data from alphavantage.co and financialmodelingprep.com to be used in our DCF model. Things like revenue, EBIT, tax rate, changes in working capital, outstanding shares, etc. are stored as variables.  

def scrape_financial_data(symbol):
    try:
        url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey=IVXRW2N8O030BK98' 
        url2 = f'https://www.alphavantage.co/query?function=CASH_FLOW&symbol={symbol}&apikey=IVXRW2N8O030BK98' 
        url3 = f'https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11' 
        url4 = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11'

        response = requests.get(url)
        capex_response = requests.get(url2)
        shares_response = requests.get(url3)
        balance_sheet_response = requests.get(url4)
        
        response.raise_for_status()
        capex_response.raise_for_status()
        shares_response.raise_for_status()
        balance_sheet_response.raise_for_status()

        data = response.json()
        capex_data = capex_response.json()
        shares_data = shares_response.json()
        balance_sheet_data = balance_sheet_response.json()

        # Extract relevant financial data from the API response
        past_years= int(input("Number of years going back: "))
        revenue = [float(data["annualReports"][i]["totalRevenue"]) for i in range(past_years)]
        ebit = [float(data["annualReports"][i]["ebit"]) for i in range(past_years)]
        depreciation = [float(data["annualReports"][i]["depreciationAndAmortization"]) for i in range(past_years)]
        capex = [float(capex_data["annualReports"][i]["capitalExpenditures"]) for i in range(past_years)]
        tax_rate = [(float(data["annualReports"][i]["incomeTaxExpense"])/float(data["annualReports"][i]["incomeBeforeTax"])) for i in range (past_years)] 
        outs_shares = float(shares_data[0]["sharesOutstanding"])
        working_capital_current_year = [float(balance_sheet_data[i]['totalCurrentAssets'] - balance_sheet_data[i]['totalCurrentLiabilities']) for i in range(past_years)]
        working_capital_previous_year = [float(balance_sheet_data[i+1]['totalCurrentAssets'] - balance_sheet_data[i+1]['totalCurrentLiabilities']) for i in range(past_years)]
        changes_in_working_capital = [float(working_capital_current_year[i] - working_capital_previous_year[i]) for i in range (past_years)]
        operating_cf = [float(capex_data["annualReports"][i]["operatingCashflow"]) for i in range(past_years)]

        #Print results
        print(f'Revenue of the company: {revenue}')
        print(f'EBIT of the company: {ebit}') 
        print(f'Depreciation and Amortization: {depreciation}')
        print(f'Capital Expenditures: {capex}') 
        print(f'The effective tax rate: {tax_rate}')
        print(f'Shares Outstanding: {outs_shares}')
        print(f'Working capital current year: {working_capital_current_year}')
        print(f'Working capital previous year: {working_capital_previous_year}')
        print(f'Change in working capital: {changes_in_working_capital}')
        print(f'Operating cash flows for past {past_years}: {operating_cf}')

        return capex, outs_shares, past_years, operating_cf
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
    except json.JSONDecodeError as e:
        print(f"An error occurred while parsing the JSON response: {e}")
    except KeyError as e:
        print(f"An error occurred due to missing keys in the API response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

#Step 3: Calculating the Weighted Average Cost of Capital (WACC) which will be the discount rate that we would use to discount projected future free cash flows back to today's value. WACC is often used as a discount rate because it encapsulates the risk associated with a specific company's operations, basically a rate to determine whether the company is worth investing into. In this we calculate the cost of equity using the Capital Asset Pricing Model (CAPM), risk free rate + beta*(market return - risk free rate).

def wacc_calculation(symbol):
    try:
        financials_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11'
        debt_url = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11'
        tax_url = f'https://financialmodelingprep.com/api/v3/income-statement/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11'
        beta_url = f'https://financialmodelingprep.com/api/v3/company/profile/{symbol}?apikey=f5fcb8b1b5c88500a14b63b10e029b11'
        fred = Fred('7c9cf4c1355cd5a08c185b13e1a47a8b')
        
        finsponse = requests.get(financials_url)
        debtsponse = requests.get(debt_url)
        taxsponse = requests.get(tax_url)
        betasponse = requests.get(beta_url)

        finsponse.raise_for_status()
        debtsponse.raise_for_status()
        taxsponse.raise_for_status()
        betasponse.raise_for_status()

        financial_data = json.loads(finsponse.text)
        debt_data = json.loads(debtsponse.text)
        tax_data = json.loads(taxsponse.text)
        beta_data = json.loads(betasponse.text)

        #Extracting financial and debt data to calculate value of company
        market_cap = float(financial_data[0]["marketCap"])
        debt = float(debt_data[0]["totalDebt"])
        cash = float(debt_data[0]["cashAndCashEquivalents"])
        enterprise_value = market_cap + debt - cash

        #Extracting tax data to calculate tax rate between tax expense and pre-tax income
        tax_expense = float(tax_data[0]["incomeTaxExpense"])
        pretax_income = float(tax_data[0]["incomeBeforeTax"])
        tax_rate = tax_expense/pretax_income
        
        #Extracting the beta as a measure of a company's systematic risk
        beta = float(beta_data["profile"]["beta"])

        #Getting data for 10-year US Treasury bond yield and S&P 500 index
        treasury_data = fred.get_series('DGS10')
        sp_data = fred.get_series('SP500')

        #Calculating risk-free rate and yield of bond in decimal
        risk_free_rate = treasury_data.iloc[-1] / 100
        yield_of_bond = treasury_data.iloc[-1] / 100 #numerically the same, theoretically different

        #Calculating market return from S&P 500 index
        market_return = (sp_data.iloc[-1] - sp_data.iloc[-252]) / sp_data.iloc[-252]

        #Get latest closing price of S&P 500 index and its price one year ago
        latest_closing_price = sp_data.iloc[-1]
        price_one_year_ago = sp_data.iloc[-252]

        #Calculating cost of equity of the S&P500 using the Capital Asset Pricing Model (CAPM) formula
        cost_of_equity = yield_of_bond + beta * (market_return - yield_of_bond)

        #Calculate the cost of debt from the interest expense and total debt of the company
        interest_expense = float(tax_data[0]["interestExpense"])
        cost_of_debt = interest_expense/debt 

        #Putting it all together to get the WACC
        WACC = ( market_cap / enterprise_value ) * cost_of_equity + ( debt / enterprise_value ) * cost_of_debt * ( 1 - tax_rate )

        #Print results
        print(f'The enterprise value of {symbol}: {enterprise_value:.4f}')
        print(f'The appropriate tax-rate to value this company: {tax_rate:.4f}')
        print(f'The beta of the stock is {beta:.4f}')
        print(f'The risk-free rate of the 10-year US Treasury bond is {risk_free_rate:.4f}')
        print(f'The yield of the bond in decimal is {yield_of_bond:.4f}')
        print(f'The market return from the S&P 500 index is {market_return:.4f}')
        print(f'The latest closing price of the S&P 500 index is {latest_closing_price:.2f}')
        print(f'The price of the S&P 500 index one year ago was {price_one_year_ago:.2f}')
        print(f'Cost of Equity of the S&P500: {cost_of_equity:.4f}')
        print(f'The WACC: {WACC:.4f}')

        return WACC
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
    except json.JSONDecodeError as e:
        print(f"An error occurred while parsing the JSON response: {e}")
    except KeyError as e:
        print(f"An error occurred due to missing keys in the API response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

#Step 4: Calculating Compounded Annual Growth Rate (CAGR), which I use as the estimate growth rate of future cash flows over time. To me, CAGR is a good way to estimate future growth rates because it takes into account the compounding effect of returns over time. It provides a single number that represents the average annual growth rate of an investment over a specific period of time. There are however some limitations to using CAGR to project future cash flows because it assumes that the growth rate of an investment is constant over time, which may not be the case in reality. It also doesn't take into account the volatility of an investment’s returns, which can be significant in some cases. Use due diligence in these cases.

def get_cagr(symbol):
    try:
        api_key = "f5fcb8b1b5c88500a14b63b10e029b11"
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={api_key}"
        response = requests.get(url)
        data = response.json()

        # Extract historical price data
        prices = data["historical"]
        years = 4
        days = years * 252  # 252 trading days in a year

        # Getting initial value and ending value
        iv = prices[days]["close"]
        ev = prices[0]["close"]

        # Calculating CAGR using (Ending Value/Initial Value) ^ (1/No. of Periods) – 1
        cagr = ((ev / iv) ** (1 / years)) - 1

        # Print results
        print(f"The CAGR for {symbol} is {cagr:.2%}")
        return cagr
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
    except json.JSONDecodeError as e:
        print(f"An error occurred while parsing the JSON response: {e}")
    except KeyError as e:
        print(f"An error occurred due to missing keys in the API response: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

#Step 5: the DCF valuation function calculates the past free cash flows and projects the future free cash flows for a specified number of years before applying a discount rate to come to the present values. It uses the scraped financial data from the scrape_financial_data function in step 2. The future free cash flows for the projected number of years grow at the compounded annual growth rate calculated earlier. The CAGR is then adjusted to cascade for each iteration for the proceeding years (a company is unlikely to grow at a constant rate). Finally, it calculates the present value of each cash flow and sums them up to determine the fair value of the stock based on the shares outstanding.

def dcf_valuation(symbol):
    try:
        # Call functions to get necessary values
        capex, outs_shares, past_years, operating_cf = scrape_financial_data(symbol)
        cagr = get_cagr(symbol)
        discount_rate = wacc_calculation(symbol)  

        # Getting input for terminal growth rate
        print(
    "\nIn assuming terminal growth rate (g):-\n"
    "Initial growth rate (The company is seizing market share and is experiencing high revenue growth. Growth rate 0.1 or greater)\n"
    "Slowing growth rate (Company is somewhat established and gains competitors. Some resources diverted to keeping current market share. Growth rate between 0.05 and 0.08)\n"
    "Mature growth rate (Company is established and allocates a substantial amount of its resources to protecting its market share, Positive growth rates at this stage mirror the historical inflation rate, between 0.02 and 0.03. Historical GDP growth can be used alternatively which is between 0.04 and 0.05)\n"
    "Companies that have declining use cases will not have this growth rate.\n"
    "Also, the terminal growth rate has to be smaller than the WACC (scroll up)\n"
)

        terminal_growth_rate = float(input("Input chosen terminal growth rate (in decimal): "))

        # Calculating free cash flows of past years
        past_fcfs = [round(operating_cf[i] - capex[i]) for i in range(past_years)]

        # Calculating future free cash flows for the projected number of years
        future_fcf = []
        for i in range(num_years_projected):
            if cagr > terminal_growth_rate:
                future_fcf.append(round((operating_cf[0] - capex[0]) * (1 + cagr) ** i))
                print(f'Future FCF growth rate for year {i+1}: {cagr}')
            else:
                cagr = terminal_growth_rate
                future_fcf.append(round((operating_cf[0] - capex[0]) * (1 + cagr) ** i))
                print(f'Future FCF growth rate for year {i+1}: {cagr}')
            cagr /= 2

        # Calculating present value (PV) by discounting future free cash flows with the WACC
        present_value = [cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(future_fcf)]
        present_value_sum = round(np.sum(present_value))
        terminal_value = round((future_fcf[-1] * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate))

        # Print results
        print(f'The free cash flows of past {past_years} years: {past_fcfs}')
        print(f"Projected FCF for {num_years_projected} years: {future_fcf}")
        print(f"Present value of projected FCF (Discounted back to present): {present_value}")
        print(f"Terminal value at {terminal_growth_rate}: {terminal_value}")  
        print(f"Sum of present values: {present_value_sum}")

        # Calculate enterprise value and fair value per share
        enterprise_value = present_value_sum + terminal_value
        fair_value_per_share = enterprise_value / outs_shares

        return fair_value_per_share
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

#Step 6: Defining the function to determine if the stock is undervalued or overvalued against the current price. Thus giving you a flexible and timesaving DCF screening tool with valuable data, all from typing in the stock ticker.

def determine_valuation(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=IVXRW2N8O030BK98"
        response = requests.get(url)
        data = response.json()["Global Quote"]
        current_price = float(data["05. price"])
        fair_value = float(dcf_valuation(symbol))
        
        if response.status_code == 200:
            print(f"The current price of {symbol}: ${current_price}")
            print(f"The fair value: ${fair_value:.2f}")
            
            if current_price > fair_value:
                difference = fair_value - current_price
                diff_percentage = (difference / current_price) * 100
                return f'Stock is overvalued, margin of safety is {diff_percentage:.2f}% with a difference of ${difference:.2f} against the current price'
            elif current_price < fair_value:
                difference = fair_value - current_price
                diff_percentage = (difference / current_price) * 100
                return f'Stock is  undervalued, margin of safety is {diff_percentage:.2f}% with a difference of ${difference:.2f} against the current price'
            else:
                return "Stock is fairly valued"
        else:
            print("Error: Unable to retrieve data from Alpha Vantage API")
    except Exception as e:
        print(f"An error occurred: {e}")
    
symbol = input("Enter stock ticker: ")
num_years_projected = int(input("Number of years to be projected: "))
valuation_result = determine_valuation(symbol)
print(valuation_result)