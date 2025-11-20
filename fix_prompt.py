import re

# Read the file
with open('investor_agent/prompts.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all [PLACEHOLDER] with <PLACEHOLDER> to avoid ADK template variable conflicts
# This preserves actual list syntax like [1, 2, 3] or [RELIANCE, TCS, HDFC]
replacements = {
    r'\[SYMBOL\]': '<SYMBOL>',
    r'\[SYMBOL1\]': '<SYMBOL1>',
    r'\[SYMBOL2\]': '<SYMBOL2>',
    r'\[SYMBOL3\]': '<SYMBOL3>',
    r'\[SYMBOL4\]': '<SYMBOL4>',
    r'\[SYMBOL5\]': '<SYMBOL5>',
    r'\[SYMBOL 1\]': '<SYMBOL_1>',
    r'\[SYMBOL 2\]': '<SYMBOL_2>',
    r'\[SYMBOL 3\]': '<SYMBOL_3>',
    r'\[SYMBOL 4\]': '<SYMBOL_4>',
    r'\[X\]': '<X>',
    r'\[Y\]': '<Y>',
    r'\[Z\]': '<Z>',
    r'\[SYM1\]': '<SYM1>',
    r'\[SYM2\]': '<SYM2>',
    r'\[Start Date\]': '<Start_Date>',
    r'\[End Date\]': '<End_Date>',
    r'\[Sentiment Emoji\]': '<Sentiment_Emoji>',
    r'\[Count\]': '<Count>',
    r'\[Price Range\]': '<Price_Range>',
    r'\[Price move\]': '<Price_move>',
    r'\[Brief news\]': '<Brief_news>',
    r'\[Your take\]': '<Your_take>',
    r'\[Sector Name\]': '<Sector_Name>',
    r'\[Reason\]': '<Reason>',
    r'\[up/down\]': '<up_or_down>',
    r'\[Confidence Level: High/Medium\]': '<Confidence_Level>',
    r'\[Reason for watchlist\]': '<Reason_for_watchlist>',
    r'\[One line reason combining data \+ news\]': '<One_line_reason>',
    r'\[Bullish/Bearish/Mixed\]': '<Market_mood>',
    r'\[One line justification\]': '<Justification>',
    r'\[date range\]': '<date_range>',
    r'\[Your interpretation\]': '<Your_interpretation>',
    r'\[\.\.\.rest of table\.\.\.\]': '<rest_of_table>',
    r'\[\.\.\.rest of structured output\.\.\.\]': '<rest_of_output>',
    r'\[\.\.\.repeat for each stock\.\.\.\]': '<repeat_for_each_stock>',
    r'\[\.\.\.Table with performance data\.\.\.\]': '<Table_with_performance_data>',
    r'\[\.\.\.Complete structured report as per Merger Agent template\]': '<Complete_report>',
    r'\[\.\.\.Complete report as per Merger Agent template\]': '<Complete_report>',
    r'\[\.\.\.Complete structured report\]': '<Complete_report>',
    r'\[COMPANY NAME\]': '<COMPANY_NAME>',
    r'\[Brief description of main news catalyst, max 1 line\]': '<Brief_description>',
    r'\[Publication name, date\]': '<Publication_name_date>',
    r'\[Positive/Negative/Neutral \+ brief reason\]': '<Sentiment>',
    r'\[Does this explain the Market Agent.s findings\?\]': '<Correlation_explanation>',
    r'\[Any broader sector trends that affect multiple stocks\]': '<Sector_trends>',
    r'\[RBI policy, budget announcements, global events affecting India\]': '<Market_context>',
    r'\[Possible reasons - insider activity, sector rotation, technical breakout\]': '<Possible_reasons>',
    r'\[What.s interesting but incomplete\]': '<Whats_interesting>',
    r'\[Specific trigger - next earnings, news confirmation, price level\]': '<Specific_trigger>',
    r'\[Conditional action\]': '<Conditional_action>',
    r'\[Distribution pattern, negative news, etc\.\]': '<Warning_sign>',
    r'\[Avoid new positions / Book profits if holding\]': '<Action>',
    r'\[Identify if multiple stocks from same sector are moving - e\.g\., "Banking sector strength"\]': '<Sector_themes>',
    r'\[Extract any RBI policy, budget, or macro events from News Agent\]': '<Macro_events>',
    r'\[Based on the balance of positive vs negative stocks\]': '<Market_sentiment>',
    r'\[Any systemic risk or opportunity mentioned in news\]': '<Systemic_risks>',
    r'\[Biggest concern from the analysis - could be data anomaly, negative sector news, or lack of news clarity\]': '<Key_risk>',
    r'\[One concrete action for the investor - e\.g\., "Accumulate banking stocks on dips; avoid IT sector until earnings clarity"\]': '<Actionable_insight>',
    r'\[Insert tool output table here\]': '<Tool_output_table>',
    r'\[your interpretation based on delivery % and volatility\]': '<your_interpretation>',
    r'\[Observation about delivery %, volatility, or sector concentration\]': '<Notable_pattern>',
    r'\[Any anomalies like >200% returns or data gaps\]': '<Risk_flags>',
    r'\[List of symbols you searched\]': '<Symbol_list>',
    r'\[e\.g\., "High delivery in banking sector", "Volatile IT stocks", "Earnings season impact"\]': '<Focus_areas>',
    r'\[Combine news catalyst \+ delivery % \+ price action in 1-2 sentences\]': '<Why_now>',
    r'\[e\.g\., "Earnings beat \+ 65% delivery \+ 12% gain = Strong institutional accumulation"\]': '<Key_signal>',
    r'\[Any caveat from data - volatility, anomaly flags, or "None if news confirmed"\]': '<Risk>',
    r'\[e\.g\., "Add on dips, Target: \[X\]% upside based on momentum"\]': '<Action>',
    r'\[Top performer observation with numbers\]': '<Top_performer_observation>',
    r'\[Delivery % pattern across top stocks\]': '<Delivery_pattern>',
    r'\[Volatility or sector concentration note\]': '<Volatility_note>',
    r'\[List symbols\]': '<List_symbols>',
    r'\[\.\.\.': '<continuation>',
}

for pattern, replacement in replacements.items():
    content = re.sub(pattern, replacement, content)

# Write back
with open('investor_agent/prompts.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Replaced all bracket placeholders with angle brackets")