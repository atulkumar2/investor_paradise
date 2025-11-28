"""Tools package for Investor Paradise agent system."""

# Import all tools from submodules
from investor_agent.tools.indices_tools import (
    get_index_constituents,
    get_market_cap_category,
    get_sector_from_index,
    get_sector_stocks,
    get_sectoral_indices,
    get_stocks_by_market_cap,
    get_stocks_by_sector_index,
    list_available_indices,
)
from investor_agent.tools.core_analysis_tools import (
    analyze_stock,
    check_data_availability,
    compare_stocks,
    detect_volume_surge,
    get_sector_top_performers,
    get_top_gainers,
    get_top_losers,
)
from investor_agent.tools.advanced_analysis_tools import (
    analyze_risk_metrics,
    detect_breakouts,
    detect_reversal_candidates,
    find_momentum_stocks,
    get_52week_high_low,
    get_delivery_momentum,
    get_volume_price_divergence,
    list_available_tools,
)
from investor_agent.tools.semantic_search_tools import (
    get_company_name,
    get_monthly_dirs_for_date_range,
    init_search_resources,
    load_collections_for_date_range,
    semantic_search,
)

__all__ = [
    # Indices and classification tools
    'get_index_constituents',
    'list_available_indices',
    'get_sectoral_indices',
    'get_sector_from_index',
    'get_stocks_by_sector_index',
    'get_stocks_by_market_cap',
    'get_market_cap_category',
    'get_sector_stocks',
    # Core analysis tools
    'check_data_availability',
    'get_top_gainers',
    'get_top_losers',
    'get_sector_top_performers',
    'analyze_stock',
    'compare_stocks',
    # Advanced analysis tools
    'detect_volume_surge',
    'get_delivery_momentum',
    'detect_breakouts',
    'list_available_tools',
    'get_52week_high_low',
    'analyze_risk_metrics',
    'find_momentum_stocks',
    'detect_reversal_candidates',
    'get_volume_price_divergence',
    # Semantic search tools
    'get_company_name',
    'get_monthly_dirs_for_date_range',
    'init_search_resources',
    'semantic_search',
    'load_collections_for_date_range',
]
