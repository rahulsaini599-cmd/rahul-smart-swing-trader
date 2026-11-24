# Rahul Smart Swing Trader V1.0 (Paper Trading)

## What this is
A local Windows-friendly Streamlit prototype that scans a bundled Nifty 50 symbol list using daily Yahoo Finance data and supports virtual paper positions.

## Important limitations
- It is NOT connected to Groww and cannot place real orders.
- Yahoo Finance data is unofficial and may be delayed, incomplete, rate-limited, or unavailable.
- The Nifty 50 list is static in this prototype and should be reviewed against the official index list.
- This first version is not a continuously running service. Open the dashboard and refresh data to update it.
- It does not guarantee profits. Paper fills are simplified and do not fully model slippage, brokerage, taxes, corporate actions, or overnight gaps.
- The scanner signal is a technical rule set, not a verified expert trader's track record or an AI prediction.

## Install on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/
2. During installation, tick "Add Python to PATH".
3. Extract this ZIP to a folder, for example Desktop\RahulSmartSwingTrader.
4. Open Command Prompt in that folder.
5. Run:
   ```
   py -m pip install -r requirements.txt
   py -m streamlit run app.py
   ```
6. A browser tab should open with the dashboard. If not, visit http://localhost:8501

## Paper trading
- Use "BUY संकेतों पर पेपर ट्रेड चलाएं" to create virtual entries.
- "सभी ओपन पोजीशन पेपर में बंद करें" closes all virtual positions at the latest downloaded close.
- The app saves state in `paper_state.json` in the folder.
- Download trade history as CSV.

## Risk model
- Starting virtual capital: ₹10,000
- Risk budget per trade: ₹50
- Max notional per position: ₹2,500
- Max positions: 2
- Initial stop: 2% below entry
- Target: 2R
- No F&O, no live orders.

## Reset
Close the app, then delete `paper_state.json` to reset the virtual account to ₹10,000.
