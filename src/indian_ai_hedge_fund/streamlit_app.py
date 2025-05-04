import streamlit as st
import pandas as pd
from datetime import datetime
import traceback
import io

# Project specific imports - adjust paths if needed after project structure review
from indian_ai_hedge_fund.tools.zerodha import get_holdings
from indian_ai_hedge_fund.llm.models import llm
from indian_ai_hedge_fund.utils.logging_config import logger # Use logger if needed, Streamlit handles some logging
from indian_ai_hedge_fund.analysts.config import get_analysts
from indian_ai_hedge_fund.prompts.portfolio_review import SYSTEM_PROMPT, HUMAN_SYNTHESIS_TEMPLATE
from indian_ai_hedge_fund.utils.formatting import format_holdings_for_prompt, format_analyst_report_for_prompt
from indian_ai_hedge_fund.utils.pdf_generator import generate_pdf_report
from langchain_core.prompts import ChatPromptTemplate
from rich.table import Table as RichTable # Keep for potential table formatting logic reuse
from io import StringIO # For potential string IO if needed

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Indian AI Hedge Fund Analysis", layout="wide")

st.title("📈 Indian AI Hedge Fund Analysis")
st.markdown("Select analysts, run the analysis on your Zerodha holdings, and view the synthesized report.")

# --- Analyst Selection ---
st.sidebar.header("Configuration")
available_analysts = get_analysts() # Fetch {name: (name, func)} dict
analyst_names = list(available_analysts.keys())

selected_analyst_names = st.sidebar.multiselect(
    "Select AI Analysts:",
    options=analyst_names,
    default=analyst_names[:1] # Default to selecting the first analyst if available
)

# --- Main Execution Logic ---
if st.sidebar.button("🚀 Run Analysis", use_container_width=True):
    if not selected_analyst_names:
        st.warning("Please select at least one analyst.")
    else:
        selected_analysts = [available_analysts[name] for name in selected_analyst_names]
        selected_names_str = ", ".join([name for name, _ in selected_analysts])
        st.info(f"Starting analysis with: {selected_names_str}")

        # Placeholder for general status updates
        main_status_text = st.empty()

        # Initialize placeholders for results
        holdings_data = None
        holdings_df = None
        analyst_reports = {}
        final_response = None
        pdf_buffer = None
        error_occurred = False

        # --- Step 1: Fetch Holdings ---
        main_status_text.text("⏳ Fetching portfolio holdings...")
        with st.spinner("Fetching portfolio holdings..."):
            try:
                logger.info("Fetching portfolio holdings...")
                # Direct call, progress shown by spinner
                holdings_data = get_holdings()
                logger.info("Successfully fetched holdings.")

                if isinstance(holdings_data, list) and holdings_data:
                     holdings_df = pd.DataFrame(holdings_data)
                     logger.debug("Converted holdings to DataFrame.")
                     logger.debug(f"Holdings DataFrame head:\n{holdings_df.head().to_string()}")
                elif isinstance(holdings_data, pd.DataFrame):
                     holdings_df = holdings_data # Already a DataFrame
                     logger.debug(f"Holdings received as DataFrame head:\n{holdings_df.head().to_string()}")
                else:
                     logger.warning(f"Holdings data is not a list or DataFrame: {type(holdings_data)}")
                     st.warning(f"Holdings data received in unexpected format: {type(holdings_data)}")

                st.success("Holdings fetched successfully!")
                st.subheader("Current Holdings")
                if holdings_df is not None:
                    st.dataframe(holdings_df)
                elif holdings_data:
                     st.json(holdings_data) # Display raw data if not convertible to DF
                else:
                    st.warning("No holdings data found.")

            except Exception as e:
                logger.error(f"Failed to fetch or process holdings: {e}", exc_info=True)
                st.error(f"Error fetching holdings: {e}")
                main_status_text.error(f"❌ Error fetching holdings: {e}") # Update status on error
                error_occurred = True
                st.stop() # Stop execution if holdings fail

        main_status_text.text("✅ Holdings fetched successfully!") # Update status on success

        # --- Step 2: Extract Tickers ---
        tickers = []
        if not error_occurred:
            if holdings_df is not None and 'tradingsymbol' in holdings_df.columns:
                tickers = holdings_df['tradingsymbol'].unique().tolist()
                logger.info(f"Extracted {len(tickers)} unique tickers: {tickers}")
                st.write(f"Found {len(tickers)} unique tickers for analysis.")
            elif holdings_df is not None:
                 logger.warning("Could not find 'tradingsymbol' column in holdings DataFrame.")
                 st.warning("Warning: Could not extract tickers from holdings data (missing 'tradingsymbol' column). Analysis might be limited.")
            else:
                 logger.warning("Holdings data is not available or not in expected format to extract tickers.")
                 st.warning("Warning: Holdings data unavailable or malformed. Cannot extract tickers. Analysis might be limited.")

            if not tickers:
                st.warning("No tickers found to analyze. Skipping analyst reports.")
                analyst_reports = {} # Ensure analyst_reports exists even if empty

        # --- Step 3: Run Selected Analysts ---
        if not error_occurred and tickers:
            st.subheader("Running Analyst Reports")
            num_analysts = len(selected_analysts)
            num_tickers = len(tickers)
            st.write(f"Running {num_analysts} selected analyst(s) on {num_tickers} ticker(s)...")

            # Use main status for overall analyst step
            main_status_text.text(f"⚙️ Running {num_analysts} analysts...")

            progress_bar = st.progress(0)
            status_text = st.empty() # Keep this for individual analyst status within the loop

            for i, (name, analyst_func) in enumerate(selected_analysts):
                # Update specific analyst status
                status_text.text(f"Running analyst: {name} ({i+1}/{num_analysts})...")
                logger.info(f"Running analyst: {name}")
                try:
                    # Direct call, progress shown by loop/spinner
                    report = analyst_func(tickers=tickers)
                    analyst_reports[name] = report
                    logger.info(f"Analyst {name} completed.")
                except Exception as e:
                    error_msg = f"Error running analyst {name}: {e}"
                    logger.error(error_msg, exc_info=True)
                    st.error(f"Error running analyst {name}: {e}")
                    analyst_reports[name] = f"Error: Failed to generate report - {e}" # Store error message
                progress_bar.progress((i + 1) / num_analysts)

            # Clear individual analyst status and update main status after loop
            status_text.empty()
            main_status_text.text("✅ Analyst reports generated.")
            st.success("Analyst reports generated.")

        elif not error_occurred and not tickers:
             # Update main status if skipping analysts
             main_status_text.info("ℹ️ No tickers found, skipping analyst reports.")
        elif error_occurred:
             st.info("Skipped individual analyst reports due to previous errors.")


        # --- Step 5: Synthesize Analysis ---
        if not error_occurred:
            st.markdown("---")
            st.subheader("Synthesizing Analysis")
            main_status_text.text("🧠 Synthesizing analysis...") # Update main status
            with st.spinner("Generating final synthesized report..."):
                try:
                    logger.info("Preparing final prompt for LLM synthesis")

                    # Format holdings
                    formatted_holdings = format_holdings_for_prompt(holdings_df if holdings_df is not None else holdings_data)
                    holdings_str = f"## Holdings\n\n{formatted_holdings}"
                    logger.debug(f"Formatted holdings string sample: {holdings_str[:200]}...")

                    # Format analyst reports
                    reports_str = "## Analyst Reports\n\n"
                    if analyst_reports:
                        for name, report in analyst_reports.items():
                             reports_str += format_analyst_report_for_prompt(name, report)
                    else:
                        reports_str += "No analyst reports were generated or available for synthesis."
                    logger.debug(f"Formatted reports string sample: {reports_str[:200]}...")

                    # Prepare LLM Chain
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", SYSTEM_PROMPT),
                        ("human", HUMAN_SYNTHESIS_TEMPLATE)
                    ])
                    chain = prompt | llm

                    logger.info("Invoking LLM for final synthesis")
                    invoke_input = {
                        "holdings_data": holdings_str,
                        "analyst_reports": reports_str
                    }
                    response_obj = chain.invoke(invoke_input)
                    final_response = response_obj.content # Extract content
                    logger.info("LLM synthesis completed successfully.")
                    st.success("Analysis synthesized successfully!")

                except Exception as e:
                    logger.error(f"Error during LLM synthesis: {e}", exc_info=True)
                    st.error(f"Error during final synthesis: {e}")
                    final_response = f"Error during synthesis: {e}" # Store error message
                    main_status_text.error("❌ Error during synthesis.") # Update main status on error

            # Update main status only if no error occurred during synthesis
            if not final_response or not final_response.startswith("Error during synthesis:"):
                main_status_text.text("✅ Analysis synthesized successfully!")

        # --- Step 6: Display Final Report ---
        if final_response:
             st.markdown("---")
             st.subheader("Synthesized Analysis Results")
             st.markdown(final_response)
        elif not error_occurred:
             st.warning("Final synthesis could not be completed.")

        # --- Step 7: Generate and Offer PDF Download ---
        if not error_occurred and final_response and not final_response.startswith("Error during synthesis:"):
            st.markdown("---")
            st.subheader("Download Report")
            main_status_text.text("📄 Generating PDF report...") # Update main status
            with st.spinner("Generating PDF report..."):
                try:
                    holdings_for_pdf = holdings_df if holdings_df is not None else holdings_data
                    report_date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    pdf_filename = f"indian_ai_hedge_fund_analysis_{report_date_str}.pdf"

                    # Generate PDF into a BytesIO buffer
                    pdf_buffer = io.BytesIO()
                    generate_pdf_report(holdings_for_pdf, analyst_reports, final_response, pdf_buffer)
                    pdf_buffer.seek(0) # Rewind buffer to the beginning
                    logger.info(f"PDF report generated successfully ({pdf_filename})")
                    st.success("PDF report generated.")

                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_buffer,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )

                except Exception as e:
                    logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
                    st.error(f"Error generating PDF report: {e}")
                    main_status_text.error("❌ Error generating PDF report.") # Update main status on error

            # Update main status only if PDF generation didn't explicitly error out here
            # (It might have succeeded but buffer is empty/invalid - download button handles that)
            if not 'pdf_buffer' in locals() or pdf_buffer: # Basic check if buffer likely created
                 main_status_text.text("✅ PDF report ready for download.")

        st.balloons() # Fun indicator that the process finished

# --- Footer or Additional Info ---
st.sidebar.markdown("---")
st.sidebar.info("Developed by the Indian AI Hedge Fund Team.")

# --- How to Run ---
# In your terminal, navigate to the project root directory and run:
# streamlit run src/indian_ai_hedge_fund/streamlit_app.py