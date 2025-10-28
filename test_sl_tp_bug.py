"""
Test to demonstrate the SL/TP bug.

The issue: Entry price gets slippage applied, but SL/TP don't.
Then we check if row['low'] <= stop_loss, but stop_loss was calculated
from the PRE-SLIPPAGE entry price.

This causes a mismatch where:
- LONG: We enter at $100.05 (with slippage) but SL is at $98 (based on $100)
        The REAL distance is 2.05%, but we calculate it as 2.00%
- SHORT: We enter at $99.95 (with slippage) but SL is at $102 (based on $100)
         The REAL distance is 2.05%, but we calculate it as 2.00%

This makes position sizing wrong AND makes SL/TP checks wrong.
"""

# Example LONG trade
entry_price = 100.0
slippage_rate = 0.0005  # 0.05%
atr = 1.0
atr_multiplier_sl = 2.0
risk_reward_ratio = 3.0

# Strategy calculates SL/TP based on entry_price (no slippage yet)
stop_loss = entry_price - (atr * atr_multiplier_sl)  # $98
take_profit = entry_price + (atr * atr_multiplier_sl * risk_reward_ratio)  # $106

print("=" * 60)
print("LONG TRADE EXAMPLE")
print("=" * 60)
print(f"Entry price (from signal): ${entry_price:.2f}")
print(f"Stop-loss (strategy calc): ${stop_loss:.2f}")
print(f"Take-profit (strategy calc): ${take_profit:.2f}")
print()

# Slippage applied at entry
entry_price_adj = entry_price * (1 + slippage_rate)  # $100.05
print(f"Entry price (after slippage): ${entry_price_adj:.2f}")
print()

# Current code calculates SL distance AFTER slippage
sl_distance_current = abs(entry_price_adj - stop_loss) / entry_price_adj
print(f"SL distance (current buggy calc): {sl_distance_current*100:.4f}%")
print(f"  → Position sized for {sl_distance_current*100:.2f}% risk")
print()

# But SL check happens against ORIGINAL stop_loss
print(f"SL check: row['low'] <= ${stop_loss:.2f}")
print(f"  → But we entered at ${entry_price_adj:.2f}!")
print(f"  → REAL risk: {abs(entry_price_adj - stop_loss)/entry_price_adj*100:.4f}%")
print()

# The CORRECT way
sl_distance_correct = abs(entry_price - stop_loss) / entry_price
print(f"SL distance (SHOULD BE): {sl_distance_correct*100:.4f}%")
print(f"  → This matches the strategy's intent")
print()

print("=" * 60)
print("THE BUG:")
print("=" * 60)
print("Position is sized assuming 2.05% risk, but actual risk is 2.05%")
print("(in this example they match, but with different multipliers they diverge)")
print()
print("More importantly: SL/TP are checked against prices calculated")
print("from PRE-SLIPPAGE entry, but position was entered POST-SLIPPAGE.")
print()
print("This causes systematic wins to become losses because:")
print("- We think TP is at $106")
print("- But we entered at $100.05, so REAL TP should be $106.05")
print("- When row['high'] hits $106.00, we exit")
print("- But that's only $5.95 profit instead of $6.00")
print("- After fees (0.2%), tiny profits become losses!")
