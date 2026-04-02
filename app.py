import streamlit as st
import numpy as np
import math 
import numpy_financial as npf
import pandas as pd
import copy

st.set_page_config(page_title="REE Recovery Economics", layout="wide")

# You can adjust the width number to make it bigger or smaller
try:
    st.image("logo.png", width=250)
except FileNotFoundError:
    st.warning("Logo file not found. Make sure 'logo.png' is in the same folder as this script.")
# --------------------------

st.title("SPEK Materials: Rare Earth & Scandium Recovery Economics")
st.markdown("Compare the economic viability of three pretreatment flowsheet options based on the Turton CAPCOST method.")

# ==========================================
# SIDEBAR: ADJUSTABLE PARAMETERS
# ==========================================
st.sidebar.header("⚙️ Engineering Parameters")
eng_params = {
    "Ash Feed kg/day": st.sidebar.number_input("Ash Feed kg/day", value=30000.0, step=1000.0),
    "Ash Ree Content ppm": st.sidebar.number_input("Ash Ree Content ppm", value=300.0),
    "Ash Scandium Content ppm": st.sidebar.number_input("Ash Scandium Content ppm", value=75.0),
    "Liquid to Solid Ratio": st.sidebar.number_input("Liquid to Solid Ratio", value=2.5),
    "Leaching Time hours": st.sidebar.number_input("Leaching Time hours", value=2.0),
    "Leaching Efficiency %": st.sidebar.number_input("Leaching Efficiency %", value=55.0),
    "Acid Makeup kg/hr": st.sidebar.number_input("Acid Makeup kg/hr", value=8.0),
    "Ash Density kg/m^3": st.sidebar.number_input("Ash Density kg/m^3", value=2300.0),
    "Acid Density kg/m^3": st.sidebar.number_input("Acid Density kg/m^3", value=1200.0),
    "Water wash L/S Ratio": st.sidebar.number_input("Water wash L/S Ratio", value=3.0),
    "Wash Tank Residence Time hours": st.sidebar.number_input("Wash Tank Res Time hr", value=0.5),
    "Wash Tank Mass Reduction %": st.sidebar.number_input("Wash Tank Mass Red %", value=2.0),
    "Water Wash Nitric Acid Reduction %": st.sidebar.number_input("Water Wash Acid Red %", value=15.0)
}

st.sidebar.header("💲 Economic Parameters")
econ_params = {
    "Ash Cost $/kg": st.sidebar.number_input("Ash Cost $/kg", value=0.00),
    "Ree Price $/kg": st.sidebar.number_input("Ree Price $/kg", value=500.00, step=100.0),
    "Scandium Price $/kg": st.sidebar.number_input("Scandium Price $/kg", value=40000.00, step=1000.0),
    "Operational Time hours/year": st.sidebar.number_input("Op Time hours/year", value=8000.0),
    "Ash Byproduct Value $/kg": st.sidebar.number_input("Ash Byproduct Value $/kg", value=0.011, format="%.3f"),
    "Nitric Acid Cost $/kg": st.sidebar.number_input("Nitric Acid Cost $/kg", value=0.20),
    "Water Cost $/kg": st.sidebar.number_input("Water Cost $/kg", value=0.0005, format="%.4f"),
    "NaOH Cost $/kg": st.sidebar.number_input("NaOH Cost $/kg", value=0.30),
    "Kerosene Cost $/kg": st.sidebar.number_input("Kerosene Cost $/kg", value=1.00),
    "Oxalic Acid Cost $/kg": st.sidebar.number_input("Oxalic Acid Cost $/kg", value=0.80),
    "DEHPHA Cost $/kg": st.sidebar.number_input("DEHPHA Cost $/kg", value=4.00),
    "Labor Cost $/hour": st.sidebar.number_input("Labor Cost $/hour", value=25.00),
    "Project Lifetime years": st.sidebar.number_input("Project Lifetime years", value=10.0),
    "Discount Rate %": st.sidebar.number_input("Discount Rate %", value=10.0)
}

# ==========================================
# CORE CALCULATION FUNCTIONS
# ==========================================
def CapEx_calculation(equipment_dict):
    cepci_2001, cepci_current = 397, 818
    inflation_factor = cepci_current / cepci_2001
    total_capex = 0
    
    for eq_name, size in equipment_dict.items():
        if size <= 0: continue
            
        if "Leaching Reactor (CSTR)" in eq_name:
            K1, K2, K3 = 4.1052, 0.5320, -0.0005
            Cp_0 = 10 ** (K1 + K2*math.log10(size) + K3*(math.log10(size))**2)
            F_BM = 2.25 + 1.82 * 1.0 * 3.1 # Stainless steel
            total_capex += Cp_0 * F_BM * inflation_factor
            
        elif "Rotary Filter" in eq_name:
            K1, K2, K3 = 4.8123, 0.2858, 0.0420
            Cp_0 = 10 ** (K1 + K2*math.log10(size) + K3*(math.log10(size))**2)
            total_capex += Cp_0 * 1.65 * inflation_factor
            
        elif "Rotary Kiln" in eq_name:
            K1, K2, K3 = 3.5645, 1.1118, -0.0777
            Cp_0 = 10 ** (K1 + K2*math.log10(size) + K3*(math.log10(size))**2)
            total_capex += Cp_0 * 1.25 * inflation_factor

        elif "Wash Tank" in eq_name:
            K1, K2, K3 = 3.4974, 0.4485, 0.1074
            Cp_0 = 10 ** (K1 + K2*math.log10(size) + K3*(math.log10(size))**2)
            total_capex += Cp_0 * (2.25 + 1.82) * inflation_factor
            
    return total_capex

def OpEx_calculation(choice, total_capex, eng, econ):
    op_hours = econ["Operational Time hours/year"]
    ash_feed_kg_hr = eng["Ash Feed kg/day"] / 24
    annual_ash_kg = ash_feed_kg_hr * op_hours

    efficiency = eng["Leaching Efficiency %"] / 100
    scandium_produced_kg = annual_ash_kg * (eng["Ash Scandium Content ppm"] / 1000000) * efficiency
    ree_produced_kg = annual_ash_kg * (eng["Ash Ree Content ppm"] / 1000000) * efficiency

    sx_cost_total = scandium_produced_kg * ((1.0 * econ["Kerosene Cost $/kg"]) + 
                                            (1.5 * econ["Oxalic Acid Cost $/kg"]) + 
                                            (0.5 * econ["DEHPHA Cost $/kg"]))

    cost_nitric_acid = eng["Acid Makeup kg/hr"] * op_hours * econ["Nitric Acid Cost $/kg"]

    cost_water, cost_naoh = 0.0, 0.0
    if choice == "2": 
        naoh_kg_hr = ash_feed_kg_hr * 1.0
        cost_naoh = naoh_kg_hr * op_hours * econ["NaOH Cost $/kg"]
        cost_water = (ash_feed_kg_hr + naoh_kg_hr) * eng["Water wash L/S Ratio"] * op_hours * econ["Water Cost $/kg"]

        # --- ESTIMATED UTILITY PENALTY (Rotary Kiln Natural Gas) ---
        # Q = m * Cp * dT
        mass_to_heat_kg_hr = ash_feed_kg_hr + naoh_kg_hr
        cp_kJ_kgC = 1.0  # Assumed heat capacity of ash/NaOH mixture (kJ/kg C)
        delta_T_C = 480  # Heating from ambient 20 C up to 500 C
        
        # Energy required in MJ/hr (1000 kJ = 1 MJ)
        theoretical_heat_MJ_hr = (mass_to_heat_kg_hr * cp_kJ_kgC * delta_T_C) / 1000
        
        # Assume a 50% thermal efficiency for the rotary kiln (accounting for heat loss)
        actual_heat_MJ_hr = theoretical_heat_MJ_hr / 0.50
        
        # Industrial Natural Gas cost: ~$5.00 per 1000 MJ (approx. $5/MMBtu)
        gas_price_per_1000_MJ = 5.00
        cost_utility_penalty = (actual_heat_MJ_hr / 1000) * gas_price_per_1000_MJ * op_hours
        # -----------------------------------------------------------
        
    elif choice == "3": 
        cost_water = ash_feed_kg_hr * eng["Water wash L/S Ratio"] * op_hours * econ["Water Cost $/kg"]

    cost_labor = op_hours * econ["Labor Cost $/hour"]
    cost_maintenance = total_capex * 0.05

    total_opex = cost_nitric_acid + sx_cost_total + cost_water + cost_naoh + cost_labor + cost_maintenance
    return total_opex, scandium_produced_kg, ree_produced_kg

def Cash_Flow_calculation(total_capex, total_opex, scandium_produced_kg, ree_produced_kg, eng, econ):
    project_life = int(econ["Project Lifetime years"])
    discount_rate = econ["Discount Rate %"] / 100
    tax_rate = 0.21 
    
    annual_ash_kg = (eng["Ash Feed kg/day"] / 24) * econ["Operational Time hours/year"]
    total_revenue = (scandium_produced_kg * econ["Scandium Price $/kg"] + 
                     annual_ash_kg * econ["Ash Byproduct Value $/kg"] + 
                     ree_produced_kg * econ["Ree Price $/kg"])
    
    annual_depreciation = total_capex / project_life
    taxable_income = (total_revenue - total_opex) - annual_depreciation
    taxes = max(0, taxable_income * tax_rate) 
    annual_operating_cash_flow = (taxable_income - taxes) + annual_depreciation

    land_cost = 1000000
    cash_flows = [-(total_capex + land_cost)] + [annual_operating_cash_flow] * (project_life - 1)
    cash_flows.append(annual_operating_cash_flow + land_cost)

    npv = npf.npv(discount_rate, cash_flows)
    try: irr = npf.irr(cash_flows) * 100
    except: irr = float('nan') 
    
    return npv, irr, total_revenue

# ==========================================
# MASTER SIMULATION RUNNER
# ==========================================
def run_simulation(choice):
    # Deep copy parameters so modifications in one option don't bleed into others
    eng = copy.deepcopy(eng_params)
    econ = copy.deepcopy(econ_params)
    
    ash_feed_kg_hr = eng["Ash Feed kg/day"] / 24
    Q_ash = ash_feed_kg_hr / eng["Ash Density kg/m^3"]
    equipment_dict = {}
    
    if choice == "2": # Alkali Roasting
        eng["Leaching Efficiency %"] = 85.0
        eng["Liquid to Solid Ratio"] = 2.0 
        
        kiln_vol_m3 = ((ash_feed_kg_hr * 2.0) / eng["Ash Density kg/m^3"]) * 2.0 
        equipment_dict["Rotary Kiln"] = 2 * math.pi * (kiln_vol_m3 / (math.pi * 1.5**2))
        
        Q_water = (ash_feed_kg_hr * 2.0 * eng["Water wash L/S Ratio"]) / 1000 
        equipment_dict["Wash Tank"] = ((ash_feed_kg_hr * 2.0)/eng["Ash Density kg/m^3"] + Q_water) * eng["Wash Tank Residence Time hours"]
        equipment_dict["Rotary Filter"] = 5.0 
        
        ash_feed_kg_hr *= 0.80 
        Q_ash = ash_feed_kg_hr / eng["Ash Density kg/m^3"]

    elif choice == "3": # Water Washing
        eng["Acid Makeup kg/hr"] *= (1 - eng["Water Wash Nitric Acid Reduction %"] / 100)
        
        Q_water = (ash_feed_kg_hr * eng["Water wash L/S Ratio"]) / 1000
        equipment_dict["Wash Tank"] = (Q_ash + Q_water) * eng["Wash Tank Residence Time hours"]
        equipment_dict["Rotary Filter"] = 5.0 
        
        ash_feed_kg_hr *= (1 - eng["Wash Tank Mass Reduction %"] / 100)
        Q_ash = ash_feed_kg_hr / eng["Ash Density kg/m^3"]

    Q_total = Q_ash + (ash_feed_kg_hr * eng["Liquid to Solid Ratio"]) / eng["Acid Density kg/m^3"]
    equipment_dict["Leaching Reactor (CSTR)"] = Q_total * eng["Leaching Time hours"]

    total_capex = CapEx_calculation(equipment_dict)
    total_opex, sc_prod, ree_prod = OpEx_calculation(choice, total_capex, eng, econ)
    npv, irr, rev = Cash_Flow_calculation(total_capex, total_opex, sc_prod, ree_prod, eng, econ)

    return {
        "NPV ($)": npv, "IRR (%)": irr, "Revenue ($/yr)": rev, 
        "CapEx ($)": total_capex, "OpEx ($/yr)": total_opex, 
        "Scandium Produced (kg/yr)": sc_prod,
        "Equipment Needed": ", ".join(list(equipment_dict.keys()))
    }

# ==========================================
# MAIN DASHBOARD DISPLAY
# ==========================================
# Execute simulations
results_1 = run_simulation("1")
results_2 = run_simulation("2")
results_3 = run_simulation("3")

# Display 3 Side-by-Side Columns
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Option 1: Direct Leaching")
    st.metric("Net Present Value (NPV)", f"${results_1['NPV ($)']:,.0f}")
    st.metric("Internal Rate of Return", f"{results_1['IRR (%)']:.1f}%")
    st.info(f"**Equipment:** {results_1['Equipment Needed']}")

with col2:
    st.subheader("Option 2: Alkali Roasting")
    st.metric("Net Present Value (NPV)", f"${results_2['NPV ($)']:,.0f}")
    st.metric("Internal Rate of Return", f"{results_2['IRR (%)']:.1f}%")
    st.warning(f"**Equipment:** {results_2['Equipment Needed']}")

with col3:
    st.subheader("Option 3: Water Washing")
    st.metric("Net Present Value (NPV)", f"${results_3['NPV ($)']:,.0f}")
    st.metric("Internal Rate of Return", f"{results_3['IRR (%)']:.1f}%")
    st.success(f"**Equipment:** {results_3['Equipment Needed']}")

st.divider()

# Display Tabulated Data
st.subheader("📊 Detailed Economic Comparison Matrix")
df = pd.DataFrame([results_1, results_2, results_3], 
                  index=["Option 1: Direct Leaching", "Option 2: Alkali Roasting", "Option 3: Water Washing"]).T

# Drop the string row so the styling formatter doesn't crash, and force the rest to float
df_numeric = df.drop("Equipment Needed").astype(float)

# Format the dataframe for display
format_dict = {
    "Option 1: Direct Leaching": "{:,.2f}",
    "Option 2: Alkali Roasting": "{:,.2f}",
    "Option 3: Water Washing": "{:,.2f}"
}

# Applied the width='stretch' fix for the deprecation warning
st.dataframe(df_numeric.style.format(format_dict, na_rep="-"), width='stretch')

st.caption("*Note: IRR values are highly elevated because the downstream separation Battery Limits are excluded from this partial-NPV calculation.*")
